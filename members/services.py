from datetime import date, datetime, timedelta
from operator import attrgetter
from members.models import *
import pdb

class Error(Exception):
    """ Base class for exceptions in this module """
    pass

class ServicesError(Error):
    """ Error while processing payment """
    def __init__(self, message):
        self.message = message

def invoice_pay_by_gocardless(invoice, amount, fee):
    ''' Create a gocardless payment record and pay an invoice '''
    year = Settings.current().membership_year
    payment = Payment(type=Payment.DIRECT_DEBIT,
                        person=invoice.person,
                        amount=amount,
                        fee=fee,
                        membership_year=year,
                        banked=True,
                        banked_date=datetime.now(),
                        )
    payment.save()
    invoice_pay(invoice, payment)

def invoice_pay(invoice, payment):
    ''' Pay invoice with payment '''
    if invoice.state == Invoice.PAID_IN_FULL:
        raise ServicesError("Already paid in full")
        return

    if invoice.total == payment.amount:
        items = invoice.invoiceitem_set.all()
        for item in items:
            invoice_item_pay(item, payment)
        invoice.state = Invoice.PAID_IN_FULL
        payment.state = Payment.FULLY_MATCHED
        payment.invoice = invoice
        payment.credited = payment.amount       
    else:
        payment.invoice = invoice
        invoice.state = Invoice.PART_PAID
        payment.state = Payment.PARTLY_MATCHED  
    payment.save()
    invoice.save()

def invoice_item_pay(invoice_item, payment):
    ''' Mark invoice item as paid by payment.
        If it is for a subscription, mark the sub as paid
    '''

    invoice_item.payment = payment
    invoice_item.paid = True
    invoice_item.save()
    if invoice_item.subscription:
        invoice_item.subscription.paid = True
        invoice_item.subscription.save()

def invoice_create_batch(exclude_slug='', size=10000):
    ''' Generate a batch of invoices of specified size
        Returns the number of people still remaining with uninvoiced items
        Note: because of family invoices the count returned may not seem correct
        if size = 0 just return the number of people with uninvoiced items
    '''
    # get a list of all people ids from uninvoiced items
    people_ids = InvoiceItem.objects.filter(invoice=None).values_list('person_id', flat=True)
    people = Person.objects.filter(id__in=people_ids)
    total = people.count()
    done = 0
    if size > 0 :
        for person in people:
            if exclude_slug <> '':
                include = not person.groups.filter(slug=exclude_slug).exists()
            else:
                include = True
            if include:
                invoice_create_from_items(person)
                done += 1
                if done == size:
                    break
    return (total, done)

def invoice_create_from_items(person):
    ''' if there are open invoice items link them to a new invoice
        process all family members who don't pay own bill
        Return invoice or False if there are no items '''
        
    if person.linked and not person.pays_own_bill:
        return invoice_create_from_items(person.linked)
    else:
        invoice = Invoice.objects.create(
            person = person,
            state = Invoice.UNPAID,
            date = datetime.now(),
            membership_year = Settings.current().membership_year
            )
        # include all own items
        subs_total = 0
        has_adult = False
        has_junior = False
        is_family = False
        items = person.invoiceitem_set.filter(
            invoice=None
            ).filter(
            item_type=ItemType.SUBSCRIPTION)
        if items.count()>0:
            item=items[0]
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
                item.invoice = invoice
                invoice.total += item.amount
                subs_total += item.amount
                item.save()

            for item in fam_member.invoiceitem_set.filter(invoice=None):
                is_fam_member = True
                item.invoice = invoice
                invoice.total += item.amount
                item.save()
            
        # test for family discount
        if is_family and has_adult and has_junior:
            disc_item = InvoiceItem.objects.create(
                person=person,
                invoice=invoice,
                item_type_id = ItemType.FAMILY_DISCOUNT,
                item_date = datetime.today(),
                description = 'Family discount 10%',
                amount= -subs_total / 10
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
        if invoice.invoiceitem_set.count() > 0:
            invoice.save()
            return invoice
        else:
            invoice.delete()
            return None

def invoice_cancel(invoice, with_credit_note=True, superuser=False):
    ''' 
    Disconnect all items from an invoice
    Delete Family discount items, the others remain
    If with credit_note, mark invoice as cancelled and create a credit note
    Else delete the invoice but not any attached credit note
    '''
    # no item can be paid
    if not superuser:
        if invoice.paid_items_count():
            return False

    amount = 0
    description = u''
    for item in invoice.invoiceitem_set.all():
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
        invoice.state = Invoice.CANCELLED
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

    #def pay_invoice_part(self, inv):
    #    ''' THIS CODE NOT FINISHED '''
    #    new_paid = 0
    #    old_paid = 0
    #    pay_amount = self.amount - self.credited
    #    items = inv.invoiceitem_set.order_('-amount')
    #    discount = 0
    #    for item in items:
    #        if item.amount < 0:
    #            discount += item.amount
    #    discount = - discount
    #    for item in items:
    #        if item.amount >= 0:
    #            if not item.paid:
    #                due = item.amount
    #                if due >= discount:
    #                    due -= discount
    #                    discount = 0
    #                else:
    #                    discount -= due
    #                    due = 0
                      
    #                if pay_amount >= due:
    #                    item.pay(self)
    #                    new_paid += due
    #                    pay_amount -= due
    #            else:
    #                old_paid += item.amount
        
    #                total = old_paid + new_paid
    #    # Update invoice state
    #    if total == inv.total:
    #        inv.state = Invoice.PAID_IN_FULL
    #    elif total > inv.total:
    #        inv.state = Invoice.ERROR
    #    elif total > 0:
    #        inv.state = Invoice.PART_PAID
    #    inv.save()
    #    # Update our state
    #    self.credited = self.credited + new_paid
    #    if self.amount > 0:
    #        if self.credited == 0:
    #            self.state = Payment.NOT_MATCHED
    #        elif self.amount == self.credited:
    #            self.state = Payment.FULLY_MATCHED
    #        elif self.amount > self.credited:
    #            self.state = Payment.PARTLY_MATCHED
    #        else:
    #            self.state = Payment.ERROR
    #    else:
    #        self.state = Payment.FULLY_MATCHED
    #    self.save()

def subscriptions_change_year(year):
    
    for person in Person.objects.all():      
        subs = person.subscription_set.filter(sub_year=year, active=True)
        if subs.count() == 1:
            person.sub=subs[0]
            person.save()


def create_age_list():
    ''' return a list of (age, membership_id) pairs '''
    return list(Membership.objects.exclude(
        cutoff_age=0
        ).order_by(
            'cutoff_age'
            ).values_list(
                'cutoff_age', 'id'))

def subscription_create(person,
                        sub_year,
                        start_month=Subscription.START_MONTH,
                        end_month=Subscription.END_MONTH,
                        membership_id=Membership.AUTO,
                        period=Subscription.ANNUAL,
                        new_member=False,
                        age_list=None):
        ''' Create a new subscription and link it to a person but do not activate it. '''
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
            age = person.age(datetime(sub_year, Subscription.START_MONTH, 1))       
            sub.membership_id = Membership.FULL
            if age:
                if not age_list:
                    age_list = create_age_list()
                for entry in age_list:
                    if age < entry[0]:
                        sub.membership_id = entry[1]
                        break               
        else:
            sub.membership_id = membership_id
        sub.new_member = new_member
        sub.invoiced_month = 0
        sub.save()
        return sub

def subscription_activate(sub, make_live=True):
    ''' Activate this subscription and clear all others that have the same year
        Update person.sub only if its for the same year
    '''
    for subold in sub.person_member.subscription_set.filter(sub_year=sub.sub_year):
        if subold.active:
            subold.active = False
            subold.save()
    sub.active = True
    sub.save()
    if make_live:
        sub.person_member.membership_id = sub.membership_id
        sub.person_member.sub = sub
        sub.person_member.save()
  
def subscription_renew(sub, sub_year, sub_month, generate_item=False, make_live=True, age_list=None):
    ''' Generate a new sub if current sub active and expired '''
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
            subscription_activate(new_sub, make_live)
            if generate_item:
                subscription_create_invoiceitems(new_sub, sub_month)
            return new_sub

def subscription_renew_batch(sub_year, sub_month, size = 100000):
    '''
    Renew a batch of subscriptions.
    Size determines how many to renew.
    Invoice items are automatically generated for each subscription
    But person.sub is not changed
    If size = 0 just return the count
    Else return the number remaining
    '''
    expiry_date = datetime(sub_year, sub_month, 1)
    expired_subs = Subscription.objects.filter(
        active=True
    ).filter(
        no_renewal=False
    ).filter(
        end_date__lt=expiry_date)
    remaining = expired_subs.count()
    count = 0
    if size > 0 :
        for sub in expired_subs:
            new_sub = subscription_renew(sub,
                                         sub_year,
                                         sub_month,
                                         generate_item=True,
                                         make_live=False,
                                         age_list=create_age_list())
            count += 1
            if count == size:
                break
    return remaining - count

def subscription_create_invoiceitems(sub, month):
    ''' Generate invoice item for the active subscription record
        For new members also generate a joining fee record if appropriate '''
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
                                        u"Joining fee",
                                        fee.joining_fee)  
                
                if sub.period == Subscription.ANNUAL:
                    subscription_create_invoiceitem(sub, start, end, fee)
                    sub.invoiced_month = end

                elif sub.period == Subscription.QUARTERLY:
                    bill_months = [1, 4, 7, 10, 12]
                    if current in bill_months or sub.invoiced_month == 0: 
                        if sub.invoiced_month  > start:
                            start = sub.invoiced_month + 1
                        end = (current + 2) // 3 * 3             
                        subscription_create_invoiceitem(sub, start, end, fee)
                        sub.invoiced_month  = end

                elif sub.period == Subscription.MONTHLY:
                    if sub.invoiced_month  > start:
                        start = sub.invoiced_month +1
                    end = current                              
                    subscription_create_invoiceitem(sub, start, end, fee)
                    sub.invoiced_month = end

                elif sub.period == Subscription.NON_RECURRING:
                    pass
            else:
                # If no fee, consider it paid (honorary life)
                pdb.set_trace()
                sub.paid = True
            sub.save()

def subscription_delete_invoiceitems(sub):
    ''' Delete invoice items attached to sub
    If item is linked to an unpaid invoice, 
    cancel the invoice and delete the item '''
    for item in sub.invoiceitem_set.all():
        if item.invoice:
            if item.invoice.state == Invoice.UNPAID:
                invoice_cancel(item.invoice)
                item.delete()
        else:
            item.delete()

def subscription_create_invoiceitem(sub, start_absmonth, end_absmonth, fee):
    ''' create a subscription invoice item 
        link it to the subscription '''
    item = InvoiceItem.objects.create(
        person=sub.person_member,
        item_type_id=ItemType.SUBSCRIPTION,
        item_date=datetime.today(),
        description=u'{mem} membership from {start} to {end}'.format(
            mem=str(sub.membership),
            start=formatted_date(sub_start_date(start_absmonth, sub.sub_year)),
            end=formatted_date(sub_end_date(end_absmonth, sub.sub_year))
            ),   
        amount=fee.calculate(start_absmonth, end_absmonth, sub.period),
        subscription=sub
        )
    item.save()


def person_resign(person):
    ''' Resign a person
        If there is an unpaid sub, cancel the invoice and delete the sub
        If there is a paid sub, make it inactive
    '''
    if person.sub:
        if not person.sub.paid:
            items = person.sub.invoiceitem_set.all()
            if items.count() == 1:
                inv_item = items[0]
                invoice_cancel(inv_item.invoice, with_credit_note=True)
                inv_item.delete()
        person.sub.end_date = date.today()
        person.sub.resigned = True
        person.sub.no_renewal = True 
        person.sub.save()       
        person.state = Person.RESIGNED
        person.save()
                    
def person_link_to_parent(child, parent):
    ''' link child to parent
        If parent = None, just unlink
        Delete any unknown parents without children '''
    old_parent = child.linked
    old_address = child.address
    child.linked = parent
    child.save()
    if (
        old_parent and
        old_parent.membership == Membership.NON_MEMBER and
        old_parent.person_set.count() == 0 and
        old_parent.first_name == 'Unknown'):
            old_parent.delete()
    if old_address.person_set.count() == 0:
        address.delete()

def person_delete(person):
    ''' 
    Delete a person if they have no family
    Also deletes the address if no one else linked to it
    '''
    if person.person_set.count() > 0:
        return "Person has {0} children".format(person.person_set.count())             
    for inv in person.invoice_set.all():
        if not inv.delete():
            return "Invoice {0} cannot be deleted".format(inv.id)
    if person.address.person_set.count() == 1:
        person.address.delete()
    person.delete()
    return ""  

def person_get_book_entries(person, year):
    '''
    Returns a sorted list of invoice, payments and credit notes
    for a person for the specified year
    '''
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
    return sorted(entries, key=attrgetter('creation_date'))


def group_get_or_create(slug):
    '''
    Returns the group with given slug if it exists
    Otherwise it creates it
    '''
    qset = Group.objects.filter(slug=slug)
    if qset.count() == 0:
        group = Group(slug=slug)
        group.save()
    elif qset.count() == 1:
        group = qset[0]
    else:
        raise ServicesError("{} groups matches slug {}".format(qset.count(), slug))
    return group
 
def group_add_list(group, id_list):
    '''
    Adds a list of ids to a group
    '''
    group_ids = Group.objects.all
    #for person_id in id_list:
    #    person = Person.objects.get(id=person_id)
    #    person.groups.add(group)
    #    person.save() 
    plist = Person.objects.filter(pk__in=id_list)
    for person in plist:
        person.groups.add(group)
        person.save() 

     

def consolidate(year):
    slug = '2015UnpaidInvoices'
    group = group_get_or_create(slug)
 
    # get a set of all people ids from year's invoices
    people_ids = set(Invoice.objects.filter(membership_year=year).values_list('person_id', flat=True))
    people = Person.objects.filter(id__in=people_ids)
    unpaid_count = 0
    credit_count = 0
    for person in people:
        entries = person_get_book_entries(person, year)
        balance = 0
        for entry in entries:
            classname = entry.__class__.__name__
            if classname == "Invoice":
                balance += entry.total          
            elif classname == "Payment":
                balance -= entry.amount
            elif classname == "CreditNote":
                balance -= entry.amount
        if balance <> 0:
            if balance > 0:
                desc = 'Unpaid amount carried forward from ' + str(year)
                type = ItemType.UNPAID
                unpaid_count += 1
                person.groups.add(group)
            else:
                desc = 'Credit amount carried forward from ' + str(year)
                type = ItemType.OTHER_CREDIT
                credit_count  += 1
            item = InvoiceItem(item_date=date(year + 1, 4, 1),
                               amount=balance,
                               description=desc,
                               item_type_id=type,
                               person_id=person.id)
            item.save()
    return people.count(), unpaid_count, credit_count 