from datetime import date, datetime, timedelta
import os
from django.db import models
from django.conf import settings
from django.core.urlresolvers import reverse
from django.dispatch import receiver 

#import pdb; pdb.set_trace()

def formatted_date(d):
    return u'{}/{}/{}'.format(d.day, d.month, d.year)

class Address(models.Model):
    address1 = models.CharField(max_length=50)
    address2 = models.CharField(max_length=50, blank=True)
    town = models.CharField(max_length=30)
    post_code = models.CharField(max_length=15)
    home_phone = models.CharField(max_length=20, blank=True)
    
    def __unicode__(self):
        return self.post_code

    def get_absolute_url(self):
        return reverse("person-detail", kwargs={"pk": self.pk})

class Person(models.Model):
    GENDERS = (
        ('M','Male'),
        ('F','Female'),
        ('U','Unknown'),
    )
    ACTIVE = 0
    APPLIED = 1  
    REJECTED = 2
    RESIGNED = 3
    STATES = (
        (ACTIVE, 'Active'),
        (APPLIED, 'Applied'),
        (REJECTED, 'Rejected'),
        (RESIGNED, 'Resigned'),
    )

    gender = models.CharField(max_length=1, choices=GENDERS, default='M')
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    mobile_phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(max_length=75)
    dob = models.DateField(null=True, blank=True)
    british_tennis = models.IntegerField(null=True, blank=True)
    notes = models.TextField(blank=True)  
    pays_own_bill = models.BooleanField(default = False)
    pays_family_bill = models.BooleanField(default = False)
    state = models.SmallIntegerField(choices=STATES, default=ACTIVE)
    date_joined = models.DateField(null=True, blank=True)  
    #
    membership = models.ForeignKey('Membership', blank=True, null=True)
    linked = models.ForeignKey('self', blank=True, null=True)
    address = models.ForeignKey('address', blank=True, null=True)
    # -- Navigation --
    # person_set
    # invoice_set
    # invoiceitem_set
    # subscription_set
    # payment_set
    # creditnote_set

    def __unicode__(self):
        return self.fullname()

    def get_absolute_url(self):
        return reverse("person-detail", kwargs={"pk": self.pk})

    def age(self, date):
        ''' return the age in years on given date
        '''
        if self.dob:
            return date.year - self.dob.year - ((date.month, date.day) < (self.dob.month, self.dob.day))
    
    def active_sub(self):
        ''' Return the active subscription if one exists. ''' 
        if self.subscription_set.count():
            for sub in self.subscription_set.all():
                if sub.active:
                    return sub
        return None

    def generate_invoice(self):
        ''' if there are open invoice items link them to a new invoice
            process all family members who don't pay own bill
            Return invoice or False if there are no items '''
        if self.linked and not self.pays_own_bill:
            return self.linked.generate_invoice()
        else:
            invoice = Invoice.objects.create(
                person = self,
                state = Invoice.UNPAID,
                date = datetime.now()
                )
            # include all own items
            subs_total = 0
            has_adult = False
            has_junior = False
            is_family = False
            items = self.invoiceitem_set.filter(
                invoice=None
                ).filter(
                item_type=ItemType.SUBSCRIPTION)
            if items.count()>0:
                item=items[0]
                item.invoice = invoice
                invoice.total += item.amount
                subs_total += item.amount
                has_adult = self.membership_id == Membership.FULL
                item.save()
            
            # include family subs
            family = self.person_set.filter(pays_own_bill=False)
            for fam_member in family:                         
                items = fam_member.invoiceitem_set.filter(
                    invoice=None
                    ).filter(
                    item_type=ItemType.SUBSCRIPTION)
                if items.count() > 0:
                    item=items[0]
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
                    person=self,
                    invoice=invoice,
                    item_type_id = ItemType.FAMILY_DISCOUNT,
                    item_date = datetime.today(),
                    description = 'Family discount 10%',
                    amount= -subs_total / 10
                    )
                invoice.total += disc_item.amount

            # Now own non Subscription items
            own_items = self.invoiceitem_set.filter(
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
            if invoice.total > 0:
                invoice.save()
                return invoice
            return None

    def fullname(self):
        return self.first_name + " " + self.last_name

    def link(self, parent):
        ''' link child to parent
            If parent = None, just unlink
            Delete any unknown parents without children '''
        old_parent = self.linked
        old_address = self.address
        self.linked = parent
        self.save()
        if (
            old_parent and
            old_parent.membership == Membership.NON_MEMBER and
            old_parent.person_set.count() == 0 and
            old_parent.first_name == 'Unknown'):
                old_parent.delete()
        if old_address.person_set.count() == 0:
            address.delete()

class Membership(models.Model):
    AUTO = -1
    FULL = 1
    JUNIOR = 2
    CADET = 3
    STUDENT = 4
    NON_MEMBER = 13

    description = models.CharField(max_length=20)
    
    def __unicode__(self):
        return self.description

    @classmethod
    def create(cls, id, description):
        mem = cls(id = id, description = description)
        mem.save()
        return mem

class Fees(models.Model):
    membership = models.ForeignKey('Membership')
    sub_year = models.SmallIntegerField()
    annual_sub = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    monthly_sub = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    joining_fee = models.DecimalField(max_digits=7, decimal_places=2, null=True)
 
    def __unicode__(self):
        return u'%s %s %s' % (self.sub_year, self.membership, self.annual_sub)

    def calc_sub(self, start_date, end_date, period):
        amount = 0
        end_month = end_date.month
        if end_date.month < Subscription.START_MONTH:
            end_month += 12
        start_month = start_date.month if start_date.day < 16 else start_date.month + 1
        if start_month > 12:
            start_month = 1
        if start_month < Subscription.START_MONTH:
            start_month += 12
        months = end_month - start_month + 1
        if months > 12:
            raise Exception('Annual subscription but months = %d' % months)
        if period == Subscription.ANNUAL:
            if months > 10:
                amount = self.annual_sub
            else:
                amount = months * self.monthly_sub          
        elif period == Subscription.QUARTERLY:
            if months == 3:
                amount = months * self.monthly_sub
            else:
                raise Exception('Quarterly sub but months = %d' % months)
        elif period == Subscription.MONTHLY:
            amount = self.monthly_sub
        elif period == Subscription.NON_RECURRING:
            amount = self.monthly_sub
        return amount

    def calculate(self, start_absmonth, end_absmonth, period):
        months = end_absmonth - start_absmonth + 1
        if months > 12:
            raise Exception("Fees > 12 months")
        if period == Subscription.ANNUAL:
            if months > 10:
                amount = self.annual_sub
            else:
                amount = months * self.monthly_sub 
        else:
               amount = months * self.monthly_sub  
        return amount

class Invoice(models.Model):
    UNPAID = 0
    PART_PAID = 1
    PAID_IN_FULL = 2
    CANCELLED = 3
    PART_CREDIT_NOTE = 4
    ERROR = 5

    STATES = (
        (UNPAID, "Unpaid"),
        (PART_PAID, "Part paid"),
        (PAID_IN_FULL, "Paid in full"),
        (CANCELLED, "Cancelled"),
        (PART_CREDIT_NOTE, "Part paid & credit note"),
        (ERROR, "Error - overpaid"),
        )

    creation_date = models.DateTimeField(auto_now_add=True)
    update_date = models.DateTimeField(auto_now=True)
    date = models.DateField()
    reference = models.CharField(max_length=80)
    state = models.SmallIntegerField(choices = STATES, default = UNPAID)
    person = models.ForeignKey(Person)
    email_count = models.SmallIntegerField(default=0)
    postal_count = models.SmallIntegerField(default=0)
    total = models.DecimalField(max_digits=7, decimal_places=2, default=0, null=False)
    # -- Navigation --
    # invoiceitem_set
    # creditnote_set

    def __unicode__(self):
        return "Invoice {}, {} items, total = {}".format(
            Invoice.STATES[self.state][1],
            self.invoiceitem_set.count(),
            self.total
            )

    def number(self):
        return '{}/{}'.format(self.person.id, self.id)

    def get_absolute_url(self):
        return reverse("invoice-detail", kwargs={"pk": self.pk})

    def pay_full(self):
        ''' Mark all items in the invoice as paid in full '''
        for item in self.invoiceitem_set.all():
            item.paid = True
            item.save()
        self.state = Invoice.PAID_IN_FULL
        self.save()

    def cancel(self):
        ''' Mark invoice as cancelled and disconnect all items from it
            Relink it to the person
            Create a credit note for total
            Return the credit note or False if invoice has paid items
        '''
        c_note = CreditNote(invoice=self,
                            person=self.person,
                           reference='Cancelled invoice {}'.format(self.number())
                           )
        amount = 0
        description = u''
        paid_items = False
        for item in self.invoiceitem_set.all():
            if not item.paid:
                amount += item.amount
                description = description + 'Item: {0} {1}{2}'.format(
                    item.item_type.description,
                    item.amount,
                    '\n')
                if item.item_type_id == ItemType.FAMILY_DISCOUNT:
                    item.delete()
                else:
                    item.invoice = None
                    item.save()
            else:
                paid_items = True
        if paid_items:
            return False
        else:
            self.state = Invoice.CANCELLED
            self.save()
            c_note.amount = amount
            c_note.detail = description
            c_note.save()
            return c_note

    def add_context(self, context):
        ''' set up the context for invoice & payment templates '''
        context['invoice'] = self
        context['person'] = self.person
        context['address'] = self.person.address
        context['reference'] = str(self.person.id) + '/' + str(self.id)
        context['items'] = self.invoiceitem_set.all().order_by('creation_date')
        context['state_list'] = Invoice.STATES
        context['types'] = Payment.TYPES
        context['payment_states'] = Payment.STATES
        context['full_payment_button'] = self.state == Invoice.UNPAID
        context['can_delete'] = self.email_count == 0 and self.postal_count == 0 and self.state == Invoice.UNPAID
        c_note = None
        if self.creditnote_set.count() > 0:
            c_note = self.creditnote_set.all()[0]
        context['credit_note'] = c_note



class Payment(models.Model):
    CHEQUE = 0
    CASH = 1
    BACS = 2
    DIRECT_DEBIT = 3
    PAYPAL = 4
    OTHER = 5
    TYPES = (
        (CHEQUE, "Cheque"),
        (CASH, "Cash"),
        (BACS, "BACS transfer"),
        (DIRECT_DEBIT, "Direct debit"),
        (PAYPAL, "Paypal"),
        (OTHER, "Other")
        )

    NOT_MATCHED = 0
    PARTLY_MATCHED = 1
    FULLY_MATCHED = 2
    ERROR = 3
    STATES = (
        (NOT_MATCHED, "Not matched"),
        (PARTLY_MATCHED, "Partly matched"),
        (FULLY_MATCHED, "Fully matched"),
        (ERROR, "Error - overpaid"),
        )

    creation_date = models.DateTimeField(auto_now_add=True)
    update_date = models.DateTimeField(auto_now=True)
    type = models.SmallIntegerField(choices=TYPES, default=BACS)
    person = models.ForeignKey(Person)
    reference = models.CharField(max_length=80, blank=True, null=True)
    amount = models.DecimalField(max_digits=7, decimal_places=2, null=False)
    credited = models.DecimalField(max_digits=7, decimal_places=2, null=False, default=0)
    state = models.SmallIntegerField(choices=STATES, default=NOT_MATCHED)
    banked = models.BooleanField(default=False)
    
    def __unicode__(self):
        return "Payment:{} amount:{} credited:{} state:{}".format(
            Payment.TYPES[self.type][1],
            self.amount,
            self.credited,
            Payment.STATES[self.state][1]
            )

    def pay_invoice(self, inv):
        if inv.total == self.amount:
            items = inv.invoiceitem_set.all()
            for item in items:
                item.pay(self)
            inv.state = Invoice.PAID_IN_FULL
            self.credited = self.amount
            self.state = Payment.FULLY_MATCHED
            self.save()
            inv.save()
        else:
            pay_invoice_part(inv)

    def pay_invoice_part(self, inv):
        ''' THIS CODE NOT FINISHED '''
        new_paid = 0
        old_paid = 0
        pay_amount = self.amount - self.credited
        items = inv.invoiceitem_set.order_('-amount')
        discount = 0
        for item in items:
            if item.amount < 0:
                discount += item.amount
        discount = - discount
        for item in items:
            if item.amount >= 0:
                if not item.paid:
                    due = item.amount
                    if due >= discount:
                        due -= discount
                        discount = 0
                    else:
                        discount -= due
                        due = 0
                      
                    if pay_amount >= due:
                        item.pay(self)
                        new_paid += due
                        pay_amount -= due
                else:
                    old_paid += item.amount
        
                    total = old_paid + new_paid
        # Update invoice state
        if total == inv.total:
            inv.state = Invoice.PAID_IN_FULL
        elif total > inv.total:
            inv.state = Invoice.ERROR
        elif total > 0:
            inv.state = Invoice.PART_PAID
        inv.save()
        # Update our state
        self.credited = self.credited + new_paid
        if self.amount > 0:
            if self.credited == 0:
                self.state = Payment.NOT_MATCHED
            elif self.amount == self.credited:
                self.state = Payment.FULLY_MATCHED
            elif self.amount > self.credited:
                self.state = Payment.PARTLY_MATCHED
            else:
                self.state = Payment.ERROR
        else:
            self.state = Payment.FULLY_MATCHED
        self.save()

class CreditNote(models.Model):
    creation_date = models.DateTimeField(auto_now_add=True)
    update_date = models.DateTimeField(auto_now=True)
    person = models.ForeignKey(Person)
    invoice = models.ForeignKey(Invoice, blank=True, null=True)
    amount = models.DecimalField(max_digits=7, decimal_places=2, null=False)
    reference = models.CharField(max_length=80, blank=True, null=True)
    detail = models.CharField(max_length=1000, blank=True, null=True)

    
class ItemType(models.Model):
    SUBSCRIPTION = 1
    JOINING = 2
    TEAS = 3
    BAR = 4
    VISITORS = 5
    COURTS = 6
    COACHING = 7
    TOURNAMENT = 8
    UNPAID = 9
    SOCIAL = 10
    OTHER_DEBIT = 11
    FAMILY_DISCOUNT = 12
    DISCOUNT = 13
    PAYMENT = 14
    WRITTEN_OFF = 15
    OTHER_CREDIT = 16

    id = models.IntegerField(primary_key=True)
    description = models.CharField(max_length=30)
    credit = models.BooleanField(default=False)

    def __unicode__(self):
        return self.description

class InvoiceItem(models.Model):
    creation_date = models.DateTimeField(auto_now_add=True)
    update_date = models.DateTimeField(auto_now=True)      
    item_date = models.DateField(null=True, blank=True)
    description = models.CharField(max_length=100, blank=True, null=True)
    amount = models.DecimalField(max_digits=7, decimal_places=2)
    paid = models.BooleanField(default=False)
    #
    item_type = models.ForeignKey(ItemType, default=ItemType.SUBSCRIPTION)
    person = models.ForeignKey(Person, blank=True, null=True)
    invoice = models.ForeignKey(Invoice, blank=True, null=True)
    payment = models.ForeignKey(Payment, blank=True, null=True)
    subscription = models.ForeignKey('Subscription', blank=True, null=True)
    
    def __unicode__(self):
        return u'%s %d' % (self.description, self.amount)

    def is_invoiced(self):
        return invoice is not None

    def pay(self, payment):
        self.payment = payment
        self.paid = True
        self.save()

    @classmethod
    def create_sub(cls, sub, start_absmonth, end_absmonth, fee):
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

    @classmethod
    def create(cls, person, type_id, description, amount):
        item = InvoiceItem.objects.create(
            person = person,
            item_type_id = type_id,
            item_date = datetime.today(),
            description = description, 
            amount = amount  
            )
        item.save()

    @classmethod
    def invoice_batch(cls, size=10000):
        ''' Generate a batch of invoices of specified size
            Returns the number of people still remaining with uninvoiced items
            Note: because of family invoices the count returned may not seem correct
            if size = 0 just return the number of people with uninvoiced items
        '''
        # get a list of all people ids from uninvoiced items
        people_ids = InvoiceItem.objects.filter(invoice=None).values_list('person_id', flat=True)
        people = Person.objects.filter(id__in=people_ids)
        remaining = people.count()
        count = 0
        if size > 0 :
            for person in people:
                person.generate_invoice()
                count += 1
                if count == size:
                    break
            return remaining - count
        else:
            return remaining


class Subscription(models.Model):
    START_MONTH = 5
    END_MONTH = 4

    ANNUAL = 0
    QUARTERLY = 1
    MONTHLY = 2
    NON_RECURRING = 3
    PERIODS = (
        (ANNUAL, "Annual"),
        (QUARTERLY, "Quarterly"),
        (MONTHLY, "Monthly"),
        (NON_RECURRING, "Non recurring"),
    )

    CADET_AGE = 8
    JUNIOR_AGE = 18
    STUDENT_AGE = 26

    person_member = models.ForeignKey(Person)
    sub_year = models.SmallIntegerField()
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    period = models.SmallIntegerField(choices=PERIODS, default=ANNUAL)
    membership = models.ForeignKey(Membership)
    new_member = models.BooleanField(default=False)
    paid = models.BooleanField(default=False)
    active = models.BooleanField(default=False)
    invoiced_month = models.SmallIntegerField()
    no_renewal = models.BooleanField(default=False)

    @classmethod
    def create(cls, person, sub_year, start_month=START_MONTH, end_month=END_MONTH,
               membership_id=Membership.AUTO,
               period=ANNUAL, new_member=False, paid=False, active=False):
        ''' Create a new subscription and link it to a person but do not activate it. '''
        sub = cls()
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
            if age <= Subscription.CADET_AGE:
                sub.membership_id = Membership.CADET
            elif age <= Subscription.JUNIOR_AGE:              
                sub.membership_id = Membership.JUNIOR
            elif age <= Subscription.STUDENT_AGE:
                sub.membership_id = Membership.STUDENT
            else:
                sub.membership_id = Membership.FULL
        else:
            sub.membership_id = membership_id
        sub.new_member = new_member
        sub.paid = paid
        sub.invoiced_month = 0
        sub.active = active
        sub.save()
        return sub

    @classmethod
    def renew_batch(cls, sub_year, sub_month, size = 100000):
        '''
        Renew a batch of subscriptions.
        Size determines how many to renew.
        Invoice items are automatically generated for each subscription
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
                new_sub = sub.renew(sub_year, sub_month, generate_item=True)
                count += 1
                if count == size:
                    break
        return remaining - count

    def renew(self, sub_year, sub_month, generate_item=False):
        ''' Generate a new sub if current sub active and expired '''
        new_start = datetime(sub_year, sub_month, 1).date()
        if self.active and not self.no_renewal:
            if self.end_date < new_start:
                new_mem_id = self.membership_id
                if (new_mem_id == Membership.CADET or 
                    new_mem_id  == Membership.JUNIOR or
                    new_mem_id  == Membership.STUDENT):
                    new_mem_id = Membership.AUTO
                new_sub = Subscription.create(
                    person=self.person_member,
                    sub_year=sub_year,
                    membership_id=new_mem_id,
                    period=self.period,
                    active=True
                    )
                self.active=False
                self.save()
                self.person_member.membership_id=new_sub.membership_id
                self.person_member.save()
                if generate_item:
                    new_sub.generate_invoice_items(sub_month)
                return new_sub

    def activate(self):
        ''' Activate this subscription and clear all others for the person.'''
        for sub in self.person_member.subscription_set.all():
            if sub.active:
                sub.active = False
                sub.save()
        self.active = True
        self.save()   
        self.person_member.membership_id = self.membership_id
        self.person_member.save()
             

    def __unicode__(self):  
        return u'Sub {} {} {} {}'.format (
            self.person_member,
            self.membership,
            Subscription.PERIODS[self.period][1],
            self.active)

    def get_absolute_url(self):
        return reverse("sub-update", kwargs={"pk": self.pk})

    def is_invoiced(self):
        return self.invoice_item is not None
   
    def generate_invoice_items(self, month):
        ''' Generate invoice item for the active subscription record
            For new members also generate a joining fee record if appropriate '''
        if self.active:
            current = bill_month(month)
            start = bill_month(self.start_date.month)
            end = bill_month(self.end_date.month)
            if current > self.invoiced_month and current >= start:
                fee = Fees.objects.all().filter(membership=self.membership, sub_year=self.sub_year)[0]
                if fee.annual_sub > 0:
                    if self.new_member and fee.joining_fee > 0 and self.invoiced_month == 0:
                        InvoiceItem.create(self.person_member,
                                           ItemType.JOINING,
                                           u"Joining fee",
                                           fee.joining_fee)  
                
                    if self.period == Subscription.ANNUAL:
                        InvoiceItem.create_sub(self, start, end, fee)
                        self.invoiced_month = end

                    elif self.period == Subscription.QUARTERLY:
                        bill_months = [1, 4, 7, 10, 12]
                        if current in bill_months or self.invoiced_month == 0: 
                            if self.invoiced_month  > start:
                                start = self.invoiced_month + 1
                            end = (current + 2) // 3 * 3             
                            InvoiceItem.create_sub(self, start, end, fee)
                            self.invoiced_month  = end

                    elif self.period == Subscription.MONTHLY:
                        if self.invoiced_month  > start:
                            start = self.invoiced_month +1
                        end = current                              
                        InvoiceItem.create_sub(self, start, end, fee)
                        self.invoiced_month = end

                    elif self.period == Subscription.NON_RECURRING:
                        pass
    
    def delete_invoice_items(self):
        ''' Delete uninvoice items attached to sub
        If item is linked to an unpaid invoice, 
        cancel the invoice and delete the item '''
        for item in self.invoiceitem_set.all():
            if item.invoice:
                if item.invoice.state == Invoice.UNPAID:
                    item.invoice.cancel()
                    item.delete()
            else:
                item.delete()

class BarTransaction(models.Model):
    id = models.IntegerField(primary_key=True)
    date = models.DateField()
    time = models.TimeField()
    member_id = models.ForeignKey('Person')
    member_split = models.IntegerField()
    product = models.CharField(max_length=20)
    description = models.CharField(max_length=20)
    price = models.DecimalField(max_digits=7, decimal_places = 2)
    total = models.DecimalField(max_digits=7, decimal_places = 2)

    def __unicode__(self):
        return self.id + " " + description + total

class TextBlock(models.Model):
    name = models.CharField(max_length=30, null=False, blank=False)
    text = models.CharField(max_length=8000, null=False, blank=False)
    
    def __unicode__(self):
        return self.name

class ExcelBook(models.Model):
    file = models.FileField(upload_to='excel')

    def save(self, *args, **kwargs):
        ''' Delete all objects then save the new one.
            The post_delete signal will ensure there is only one file in filesystem
        '''
        ExcelBook.objects.all().delete()
        super(ExcelBook, self).save(*args, **kwargs)

@receiver(models.signals.post_delete, sender=ExcelBook)
def auto_delete_file_on_delete(sender, instance, **kwargs):
    """ Deletes file from filesystem
    when corresponding `MediaFile` object is deleted.
    http://stackoverflow.com/questions/16041232/django-delete-filefield
    """
    if instance.file:
        if os.path.isfile(instance.file.path):
            os.remove(instance.file.path)        
        
      
        
              
def diff_month(end, start):
    return (end.year - start.year)*12 + end.month - start.month

def bill_month(m):
    ''' Get month in range 0 to 12 '''
    if m == 0:
        return 0
    if m < Subscription.START_MONTH:
        m += 12
    m -= (Subscription.START_MONTH - 1)
    return m

def sub_start_date(m, y):
    ''' Return the subscription start date for a sub month '''
    m += (Subscription.START_MONTH - 1)
    if m > 12:
        m -= 12
        y += 1
    return datetime(y, m, 1)

def sub_end_date(m, y):
    ''' Return the subscription end date for a sub month '''
    m += Subscription.START_MONTH
    if m > 12:
        m -= 12
        y += 1
    return datetime(y, m, 1) - timedelta(days=1)