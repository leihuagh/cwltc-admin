import datetime
from operator import attrgetter
from typing import Dict
from django.db import transaction
from nose.tools import nottest
from members.models import *

class Error(Exception):
    """
    Base class for exceptions in this module
    """
    pass


class ServicesError(Error):
    """
    Error while processing payment
    """
    def __init__(self, message):
        self.message = message


class BillingData:
    """
     Creation of invoice items for Bar, Teas, Visitors Book and Events.
     dict has a key = person_id and value = consolidated total fror item type.
     records is a list of records to be update as billed.
     For Bar and Teas, transactions is list of transactions to be updated as billed.
    """

    def __init__(self, item_type_id, dict, records, transactions=None, description='', date=None):
        self.item_type_id = item_type_id
        self.dict = dict
        self.description = description
        self.records = records
        self.transactions = transactions
        self.date = date if date else datetime.today()

    def process(self):
        """
        Processes the dictionary creating invoice items
        Update POS transactions if any
        Return count of items generated
        """
        count = 0
        value = Decimal(0)
        with transaction.atomic():
            for id, total in self.dict.items():
                if total != 0:
                    count += 1
                    value += total
                    inv_item = InvoiceItem(
                        item_date=self.date,
                        item_type_id=self.item_type_id,
                        description=self.description,
                        amount=total,
                        person_id=id,
                        paid=False
                    )
                    inv_item.save()
            self.records.update(billed=True)
            if self.transactions:
                for trans in self.transactions:
                    trans.update_billed()
        return count, value


def calculate_fee(amount):
    fee = amount / 100
    if fee > 2:
        fee = 2
    return fee


def invoice_pay_by_gocardless(invoice,
                              amount,
                              cardless_id,
                              payment_number=1,
                              state=Payment.STATE.PENDING,
                              banked=False,
                              banked_date=None):
    """
    Create a go cardless payment record and update invoice
    """
    if invoice.state == Invoice.STATE.PAID:
        raise ServicesError("Already paid in full")

    payment = Payment(type=Payment.DIRECT_DEBIT,
                      person=invoice.person,
                      amount=amount,
                      fee=calculate_fee(amount),
                      membership_year=invoice.membership_year,
                      state=state,
                      banked=banked,
                      banked_date=banked_date,
                      cardless_id=cardless_id,
                      payment_number=payment_number
                      )
    payment.save()
    invoice_pay(invoice, payment)


def invoice_update_state(invoice: Invoice):
    """
    Calculate the invoice state from the state of its linked payments.
    Update the linked items state and any sub that is connected.
    From 30 May 2018, if there is a pending GoCardless transaction the invoice state can be considered to be Paid.
    The pending flag will be set until all payments are confirmed.
    TODO Subscription paid state when multiple invoice items
    """
    total = Decimal(0)
    invoice.pending = False
    invoice.paid = False

    for payment in invoice.payment_set.all():
        if payment.state == Payment.STATE.PENDING:
            invoice.pending = True
            total += payment.amount
        elif payment.state == Payment.STATE.CONFIRMED:
            total += payment.amount

    if invoice.state != Invoice.STATE.CANCELLED:
        if total == invoice.total:
            invoice.state = Invoice.STATE.PAID
        elif total > 0 and total < invoice.total:
            invoice.state = Invoice.STATE.PART_PAID
        elif total > invoice.total:
            invoice.state = Invoice.STATE.OVERPAID
        else:
            invoice.state=Invoice.STATE.UNPAID
    invoice.save()
    # Update linked items and any sub that is connected
    paid = (invoice.state == Invoice.STATE.PAID) or invoice.special_case
    for invoice_item in invoice.invoice_items.all():
        invoice_item.paid = paid
        invoice_item.save()
        if invoice_item.subscription:
            invoice_item.subscription.paid = paid
            invoice_item.subscription.save()


def invoice_toggle_special_case(invoice: Invoice):
    """ Toggle special case and update state """
    invoice.special_case = not invoice.special_case
    invoice_update_state(invoice)


def payment_state(gc_status):
    """
    return the payment state corresponding to the go cardless status
    """
    new_banked = False
    if gc_status in ('pending_customer_approval', 'pending_submission', 'submitted'):
        new_state = Payment.STATE.PENDING
    elif gc_status == 'confirmed':
        new_state = Payment.STATE.CONFIRMED
    elif gc_status in ('cancelled', 'failed', 'customer_approval_denied', 'charged_back'):
        new_state = Payment.STATE.FAILED
    elif gc_status == 'paid_out':
        new_state = Payment.STATE.CONFIRMED
        new_banked = True
    else:
        raise ServicesError(f'Undefined GoCardless payment status: {gc_status}')
    return new_state, new_banked


def payment_update_state(payment, gc_status):
    """
    Update the payment state from the corresponding go cardless payment
    If the state has changed update the invoice state
    Return True if state changed or new_banked state
    """
    new_state, new_banked = payment_state(gc_status)
    if payment.state != new_state or payment.banked != new_banked:
        payment.state = new_state
        payment.banked = new_banked
        payment.save()
        invoice_update_state(payment.invoice)
        return True
    return False


def invoice_pay(invoice, payment):
    """
    Pay invoice with payment
    """
    if invoice.state == Invoice.STATE.PAID:
        raise ServicesError("Already paid in full")
    payment.invoice = invoice
    payment.save()
    invoice_update_state(invoice)


def invoice_create_batch(exclude_name='', size=10000):
    """
    Generate a batch of invoices of specified size
    Returns the number of people still remaining with uninvoiced items
    Note: because of family invoices the count returned may not seem correct
    if size = 0 just return the number of people with uninvoiced items
    """
    # get a list of all people ids from uninvoiced items
    people_ids = InvoiceItem.objects.filter(invoice=None).values_list('person_id', flat=True)
    people = Person.objects.filter(id__in=people_ids)
    total = people.count()
    year = Settings.objects.all()[0].membership_year
    done = 0
    if size > 0:
        for person in people:
            if exclude_name!= '':
                include = not person.groups.filter(name=exclude_name).exists()
            else:
                include = True
            if include:
                invoice_create_from_items(person, year)
                done += 1
                if done == size:
                    break
    return total, done


def invoices_create_from_list(id_list, year):
    """
    Generate invoices for all people in the list of ids
    And return a count of how many generated
    This may be less than number of people because of families
    """
    people = Person.objects.filter(id__in=id_list)
    count = 0
    for person in people:
        inv = invoice_create_from_items(person, year)
        if inv:
            count += 1
    return count


def invoice_create_from_items(person, year):
    """
    If there are open invoice items link them to a new invoice
    process all family members who don't pay own bill
    Return invoice or False if there are no items
    """  
    if person.linked and not person.pays_own_bill:
        return invoice_create_from_items(person.linked, year)
    else:
        invoice = Invoice.objects.create(
            person=person,
            state=Invoice.STATE.UNPAID,
            date=datetime.now(),
            membership_year=year
            )
        # include all own items
        subs_total = 0
        has_adult = False
        has_junior = False
        has_cadet = False
        is_family = False
        items = person.invoiceitem_set.filter(
            invoice=None
            ).filter(
            item_type=ItemType.SUBSCRIPTION)
        if items.count() > 0:
            item = items[0]
            item.invoice = invoice
            invoice.total += item.amount
            subs_total += item.amount
            has_adult = person.membership_id == Membership.FULL
            item.save()
            
        # include family subs
        family = person.person_set.filter(pays_own_bill=False)
        for fam_member in family:                         
            items = fam_member.invoiceitem_set.filter(
                invoice=None
                ).filter(
                item_type=ItemType.SUBSCRIPTION)
            for item in items:
                is_family = True
                has_adult = has_adult or fam_member.membership_id == Membership.FULL
                has_junior = has_junior or fam_member.membership_id == Membership.JUNIOR
                has_cadet = has_cadet or fam_member.membership_id == Membership.CADET
                item.invoice = invoice
                invoice.total += item.amount
                subs_total += item.amount
                item.save()

            for item in fam_member.invoiceitem_set.filter(invoice=None):
                item.invoice = invoice
                invoice.total += item.amount
                item.save()
            
        # test for family discount
        if is_family and has_adult and (has_junior or has_cadet):
            disc_item = InvoiceItem.objects.create(
                person=person,
                invoice=invoice,
                item_type_id=ItemType.FAMILY_DISCOUNT,
                item_date=datetime.today(),
                description='Family discount 10%',
                amount=-subs_total / 10
                )
            invoice.total += disc_item.amount

        # Now own non Subscription items
        own_items = person.invoiceitem_set.filter(
            invoice=None
            ).exclude(
            item_type=ItemType.SUBSCRIPTION)
        for item in own_items:
            item.invoice = invoice
            invoice.total += item.amount
            item.save()

        # include family non Subscription items
        for fam_member in family:
            items = fam_member.invoiceitem_set.filter(
                invoice=None
                ).exclude(
                item_type=ItemType.SUBSCRIPTION)
            for item in items:
                item.invoice = invoice
                invoice.total += item.amount
                item.save()
        if invoice.invoice_items.count() > 0:
            invoice.save()
            return invoice
        else:
            invoice.delete()
            return None


def invoice_cancel(invoice, with_credit_note=True, superuser=False):
    """
    Disconnect all items from an invoice
    Delete Family discount items, the others remain
    If with credit_note, mark invoice as cancelled and create a credit note
    Else delete the invoice but not any attached credit note
    """
    # no item can be paid
    if not superuser:
        if invoice.paid_items_count():
            return False

    amount = 0
    description = u''
    for item in invoice.invoice_items.all():
        amount += item.amount
        description = description + 'Item: {0} {1}{2}'.format(
            item.item_type.description,
            item.amount,
            '<br>')
        if item.item_type_id == ItemType.FAMILY_DISCOUNT:
            item.delete()
        else:
            item.invoice = None
            item.save()
    
    if with_credit_note:
        invoice.state = Invoice.STATE.CANCELLED
        invoice.save()
        c_note = CreditNote(invoice=invoice,
                            person=invoice.person,
                            reference='Cancelled invoice {}'.format(invoice.number()),
                            amount=amount,
                            detail=description,
                            membership_year=invoice.membership_year
                            )
        c_note.save()
        return c_note
    else:
        # disconnect any credit note else it will cascade the delete
        for cnote in invoice.creditnote_set.all():
            cnote.invoice = None
            cnote.save()
        invoice.delete()
    return True


def subscriptions_change_year(year):
    
    for person in Person.objects.all():      
        subs = person.subscription_set.filter(sub_year=year, active=True)
        if subs.count() == 1:
            person.sub = subs[0]
            person.save()


def create_age_list():
    """
    Return a list of (age, membership_id) pairs
    """
    return list(Membership.objects.exclude(
        cutoff_age=0
        ).order_by('cutoff_age')
                )         


def membership_age(dob, sub_year=0):
    """ return age as at start of sub year"""
    if sub_year == 0:
        sub_year = Settings.current_year()
    now_date = datetime(sub_year, Subscription.START_MONTH, 1)
    return now_date.year - dob.year - ((now_date.month, now_date.day) < (dob.month, dob.day))


def membership_from_dob(dob, sub_year=0, age_list=None):
    """
    Return membership id for a date of birth
    Defaults to adult full
    """
    membership = Membership.objects.get(id=1)
    if dob:
        age = membership_age(dob, sub_year)
        if not age_list:
            age_list = create_age_list()
        for entry in age_list:
            if age < entry.cutoff_age:
                membership = entry
                break
    return membership


def subscription_create(person,
                        sub_year,
                        start_month=Subscription.START_MONTH,
                        end_month=Subscription.END_MONTH,
                        membership_id=Membership.AUTO,
                        period=Subscription.ANNUAL,
                        new_member=False,
                        age_list=None):
    """
    Create a new subscription and link it to a person but do not activate it.
    """
    sub = Subscription()
    sub.person_member = person
    sub.sub_year = sub_year
    year = sub_year if start_month >= Subscription.START_MONTH else sub_year+1
    sub.start_date = datetime(year, start_month, 1)
    year = sub_year + 1 if end_month <= Subscription.START_MONTH else sub_year
    if end_month == 12:
        sub.end_date = datetime(year, 12, 31)
    else:
        sub.end_date = datetime(year, end_month + 1, 1) - timedelta(days=1)
    sub.period = period
    # Calculate membership from age if not explicitly passed
    if membership_id == Membership.AUTO:
        sub.membership_id = membership_from_dob(person.dob, sub_year, age_list).id             
    else:
        sub.membership_id = membership_id
    sub.new_member = new_member
    sub.invoiced_month = 0
    sub.save()
    return sub

# In a given year there can be multiple subs linked to a person, but only one of those will be active
# The last activated sub is set in person.sub to allow fast access

def subscription_activate(sub, activate=True):
    """
    Activate this subscription and clear active flag on all others that have the same year
    Update person.sub
    """
    for subold in sub.person_member.subscription_set.filter(sub_year=sub.sub_year):
        if subold.active:
            subold.active = False
            subold.save()
    sub.active = True
    sub.save()
    sub.person_member.membership_id = sub.membership_id
    sub.person_member.sub = sub
    sub.person_member.save()


def subscription_delete(sub):
    """
    Delete the current sub
    If there is another sub for that year, set person_sub to that one
    else person_sub will be 0
    """
    person = sub.person_member
    person.sub = None
    person.save()
    sub.delete()
    old_subs = person.subscription_set.filter(sub_year=sub.sub_year).order_by('-end_date')
    if old_subs:
        person.sub = old_subs[0]
        person.save()
        old_subs[0].active = True
        old_subs[0].save()

  
def subscription_renew(sub, sub_year, sub_month, generate_item=False, age_list=None):
    """
    Generate a new sub if current sub active and expired
    """
    if not age_list:
        age_list = create_age_list()
    new_start = datetime(sub_year, sub_month, 1).date()
    if sub.active and not sub.no_renewal:
        if sub.end_date < new_start:
            new_mem_id = sub.membership_id
            if sub.membership.cutoff_age > 0:
                new_mem_id = Membership.AUTO
            new_sub = subscription_create(
                person=sub.person_member,
                sub_year=sub_year,
                membership_id=new_mem_id,
                period=sub.period,
                age_list=age_list
                )
            subscription_activate(new_sub)
            if generate_item:
                subscription_create_invoiceitems(new_sub, sub_month)
            return new_sub


def subscription_renew_list(sub_year, sub_month, id_list):
    """
    Renew the current subscription for every person in the list of ids
    Make it active and generate an invoice item for it
    Return the number of subs generated
    """
    plist = Person.objects.filter(pk__in=id_list)
    age_list = create_age_list()
    count = 0
    for person in plist:
        sub = person.sub
        new_sub = subscription_renew(sub,
                                     sub_year,
                                     sub_month,
                                     generate_item=True,
                                     age_list=age_list)
        if new_sub:
            count += 1
    return count


def subscription_renew_batch(sub_year, sub_month):
    """
    Renew all paid subs for previous year
    Invoice items are automatically generated for each subscription
    """
    expiry_date = datetime(sub_year, sub_month, 1)
    expired_subs = Subscription.objects.filter(sub_year=sub_year - 1, active=True, paid=True,
                                               no_renewal=False, end_date__lt=expiry_date)
    count = 0
    for sub in expired_subs:
        subscription_renew(sub,
                           sub_year,
                           sub_month,
                           generate_item=True,
                           age_list=create_age_list())
        count += 1
    return count


def subscription_create_invoiceitems(sub, month):
    """
    Generate invoice item for the active subscription record
    For new members also generate a joining fee record if appropriate
    """
    if sub.active:
        current = bill_month(month)
        start = bill_month(sub.start_date.month)
        end = bill_month(sub.end_date.month)
        if current > sub.invoiced_month and current >= start:
            fee = Fees.objects.filter(membership=sub.membership, sub_year=sub.sub_year)[0]
            if fee.annual_sub > 0:
                if sub.new_member and fee.joining_fee > 0 and sub.invoiced_month == 0:
                    InvoiceItem.create(sub.person_member,
                                       ItemType.JOINING,
                                       "Joining fee",
                                       fee.joining_fee)
                
                if sub.period == Subscription.ANNUAL:
                    subscription_create_invoiceitem(sub, start, end, fee)
                    sub.invoiced_month = end

                elif sub.period == Subscription.QUARTERLY:
                    bill_months = [1, 4, 7, 10, 12]
                    if current in bill_months or sub.invoiced_month == 0: 
                        if sub.invoiced_month > start:
                            start = sub.invoiced_month + 1
                        end = (current + 2) // 3 * 3             
                        subscription_create_invoiceitem(sub, start, end, fee)
                        sub.invoiced_month = end

                elif sub.period == Subscription.MONTHLY:
                    if sub.invoiced_month > start:
                        start = sub.invoiced_month + 1
                    end = current                              
                    subscription_create_invoiceitem(sub, start, end, fee)
                    sub.invoiced_month = end

                elif sub.period == Subscription.NON_RECURRING:
                    pass
            else:
                # If no fee, consider it paid (honorary life)
                sub.paid = True
            sub.save()


def subscription_delete_invoiceitems(sub):
    """ 
    Delete invoice items attached to sub
    If item is linked to an unpaid invoice, 
    cancel the invoice and delete the item
    """
    for item in sub.invoiceitem_set.all():
        if item.invoice:
            if item.invoice.state == Invoice.STATE.UNPAID:
                invoice_cancel(item.invoice)
                item.delete()
        else:
            item.delete()


def subscription_create_invoiceitem(sub, start_absmonth, end_absmonth, fee):
    """
    Create a subscription invoice item 
    link it to the subscription
    """
    item = InvoiceItem.objects.create(
        person=sub.person_member,
        item_type_id=ItemType.SUBSCRIPTION,
        item_date=datetime.today(),
        description=u'{mem} membership from {start} to {end}'.format(
            mem=str(sub.membership.description),
            start=formatted_date(sub_start_date(start_absmonth, sub.sub_year)),
            end=formatted_date(sub_end_date(end_absmonth, sub.sub_year))
            ),   
        amount=fee.calculate(start_absmonth, end_absmonth, sub.period),
        subscription=sub
        )
    item.save()


def person_resign(person):
    """
    Resign a person
    If there is an unpaid sub, cancel the invoice and delete the sub
    If there is a paid sub, make it inactive
    Generate any invoice items from POS
    """
    if person.sub:
        if not person.sub.paid:
            items = person.sub.invoiceitem_set.all()
            if items.count() == 1:
                inv_item = items[0]
                if inv_item.invoice:
                    invoice_cancel(inv_item.invoice, with_credit_note=True)
                inv_item.delete()
        person.sub.end_date = date.today()
        person.sub.resigned = True
        person.sub.no_renewal = True 
        person.sub.save()       
    person.state = Person.RESIGNED
    person.unregister()
    # generate any pos records
    # todo bill person upon resignation
    # create_all_invoiceitems_from_payments(person)
    invoice_create_from_items(person, Settings.current_year())


@nottest
def person_testfor_delete(person):
    """
    Return [] if person can be deleted
    else return a list of reasons why not
    We don't test for subs so hon life paid subs can be deleted
    """
    messages = []
    if person.person_set.count() > 0:
        messages.append("Person has family records")
    if person.invoice_set.count() > 0:
        messages.append("Person has invoice records")
    if person.payment_set.count() > 0:
        messages.append("Person has payment records")
    if person.creditnote_set.count() > 0:
        messages.append("Person has credit notes")
    if person.invoiceitem_set.count() > 0:
        messages.append("Person has invoice items")
    return messages


def person_can_delete(person):
    """
    True if person can be deleted
    """
    return person_testfor_delete(person) == []


def person_delete(person):
    """ 
    Delete a person if they have no linked records
    Also deletes the address if no one else linked to it
    """
    messages = person_testfor_delete(person)
    if not messages:
        if person.address:
            if person.address.person_set.count() == 1:
                person.address.delete()
        person.delete()
    return messages


def person_statement(person, year):
    """
    Returns a sorted list of invoice, payments and credit notes
    for a person for the specified year
    """
    entries = []
    invoices = person.invoice_set.filter(membership_year=year)
    for i in invoices:
        entries.append(i)
    cnotes = person.creditnote_set.filter(membership_year=year)
    for c in cnotes:
        entries.append(c)
    payments = person.payment_set.filter(membership_year=year)
    for p in payments:
        entries.append(p)
    entries = sorted(entries, key=attrgetter('creation_date'))
    statement = []
    balance = 0
    for entry in entries:
        classname = entry.__class__.__name__
        if classname == "Invoice":
            balance += entry.total
        elif classname == "Payment":
            balance -= entry.amount
        elif classname == "CreditNote":
            balance -= entry.amount
        statement.append((entry, balance))
    return statement


def person_merge(person_from, person_to):
    """
    Merge two people into one
    Move all related items from person_from to person_to
    Then delete person_to and their address record
    """
    person_reassign_records(person_from, person_to)
    for sub in person_from.subscription_set.all():
        sub.person_member = person_to
        sub.save()
    for invitem in person_from.invoiceitem_set.all():
        invitem.person = person_to
        invitem.save()
    person_delete(person_from)


def person_reassign_records(person_from, person_to):
    """
    Reassign all family and finance records to a parent person
    """
    for child in person_from.person_set.all():
        child.linked = person_to
        child.address = person_to.address
        child.save()
    for invoice in person_from.invoice_set.all():
        invoice.person = person_to
        invoice.save()
    for payment in person_from.payment_set.all():
        payment.person = person_to
        payment.save()
    for cnote in person_from.creditnote_set.all():
        cnote.person = person_to
        cnote.save()


def person_link(child, parent):
    """ 
    Link child to parent
    If parent = None, just unlink
    Delete any unknown parents without children
    """
    person_reassign_records(child, parent)
    old_parent = child.linked
    old_address = child.address
    child.linked = parent
    child.save()
    if (old_parent and
            old_parent.membership == Membership.NON_MEMBER and
            old_parent.person_set.count() == 0 and
            old_parent.first_name == 'Unknown'):
                old_parent.delete()
    if old_address.person_set.count() == 0:
        old_address.delete()


def group_get_or_create(name):
    """
    Returns the group with given name if it exists
    Otherwise it creates it
    """
    qset = Group.objects.filter(name=name)
    if qset.count() == 0:
        group = Group(name=name)
        group.save()
    elif qset.count() == 1:
        group = qset[0]
    else:
        raise ServicesError("{} groups matches name {}".format(qset.count(), name))
    return group


def consolidate(year):
    name = '2015UnpaidInvoices'
    group = group_get_or_create(name)
 
    # get a set of all people ids from year's invoices
    people_ids = set(Invoice.objects.filter(membership_year=year).values_list('person_id', flat=True))
    people = Person.objects.filter(id__in=people_ids)
    unpaid_count = 0
    credit_count = 0
    for person in people:
        entries = person_statement(person, year)
        balance = 0
        for entry in entries:
            classname = entry.__class__.__name__
            if classname == "Invoice":
                balance += entry.total          
            elif classname == "Payment":
                balance -= entry.amount
            elif classname == "CreditNote":
                balance -= entry.amount
        if balance != 0:
            if balance > 0:
                desc = 'Unpaid amount carried forward from ' + str(year)
                item_type = ItemType.UNPAID
                unpaid_count += 1
                person.groups.add(group)
            else:
                desc = 'Credit amount carried forward from ' + str(year)
                item_type = ItemType.OTHER_CREDIT
                credit_count += 1
            item = InvoiceItem(item_date=date(year + 1, 4, 1),
                               amount=balance,
                               description=desc,
                               item_type_id=item_type,
                               person_id=person.id)
            item.save()
    return people.count(), unpaid_count, credit_count 