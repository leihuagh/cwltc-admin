from datetime import date, datetime, timedelta
#import datetime
import os
from django.db import models
from django.db.models import Q
from django.conf import settings
from django.core.urlresolvers import reverse
from django.dispatch import receiver 
from sets import Set
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

class ParentsManager(models.Manager):
    def get_queryset(self):
        kids = Person.objects.filter(
            Q(membership_id = Membership.CADET) |
            Q(membership_id = Membership.JUNIOR)
            )
        parent_set = Set([])
        for kid in kids:
            if kid.linked:
                if not kid.linked_id in parent_set:
                    parent_set.add(kid.linked_id)
        parents = Person.objects.filter(id__in=parent_set)
        return parents

class Group(models.Model):
    slug =  models.SlugField(max_length=20)
    description = models.CharField(max_length=80)
    #generated = models.BooleanField(default = False)
    
    def __unicode__(self):
        return self.slug 

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
    state = models.SmallIntegerField(choices=STATES, default=ACTIVE)
    date_joined = models.DateField(null=True, blank=True)  
    #
    membership = models.ForeignKey('Membership', blank=True, null=True)
    linked = models.ForeignKey('self', blank=True, null=True)
    address = models.ForeignKey('address', blank=True, null=True)
    groups = models.ManyToManyField(Group)
    # -- Navigation --
    # person_set
    # invoice_set
    # invoiceitem_set
    # subscription_set
    # payment_set
    # creditnote_set
    objects = models.Manager()
    parent_objects = ParentsManager()

    def __unicode__(self):
        return self.fullname()

    def get_absolute_url(self):
        return reverse("person-detail", kwargs={"pk": self.pk})   
    
    def as_array(self):
        return [
            self.first_name,
            self.last_name,
            self.membership.description,
            self.age_today,
            self.email,
            self.id,
            ] 
 
   
    def age(self, date):
        ''' return the age in years on given date
        '''
        if self.dob:
            return date.year - self.dob.year - ((date.month, date.day) < (self.dob.month, self.dob.day))
    
    def age_today(self):
        return self.age(date.today())

    def fullname(self):
        return self.first_name + " " + self.last_name    
    
    def active_sub(self):
        ''' Return the active subscription if one exists. ''' 
        if self.subscription_set.count():
            for sub in self.subscription_set.all():
                if sub.active:
                    return sub
        return None

                                       

class Membership(models.Model):
    AUTO = -1
    FULL = 1
    JUNIOR = 2
    CADET = 3
    UNDER_26 = 4
    BRIDGE = 5
    COUNTRY = 6
    COACH = 7
    HON_LIFE = 8
    LIFE = 9
    MIDWEEK = 10
    NON_PLAYING = 11
    RESIGNED = 12
    NON_MEMBER = 13
    PARENT = 14
    OFF_PEAK = 15
    # Groups
    PLAYING = 100
    JUNIORS = 101
    FAMILIES = 102
    ALL_NONPLAYING = 103
    PLAYING_LIST = [FULL, UNDER_26, COUNTRY, HON_LIFE, LIFE, MIDWEEK, OFF_PEAK, PARENT, COACH]
    JUNIORS_LIST = [JUNIOR, CADET]   
    ALL_NONPLAYING_LIST = [BRIDGE, NON_PLAYING]

    FILTER_CHOICES = [
        (0,'All'),
        (PLAYING, 'Playing members'),
        (JUNIORS, 'Juniors & cadets'),
        (FAMILIES, 'Families'),
        (ALL_NONPLAYING, 'All non-playing')
        ]

    
    NO_BAR_ACCOUNT  = [JUNIOR, CADET, RESIGNED, NON_MEMBER, PARENT]
    ADULT_CHOICES = [
        (FULL, "Full"),
        (OFF_PEAK, "Off peak"),
        (PARENT, "Parent"),
        (COUNTRY, "Country"),
        (BRIDGE, "Bridge"),
        (NON_PLAYING, "Non playing"),
        (COACH, "Coach"),
        (UNDER_26, "Under 26"),
        (HON_LIFE, "Honorary life"),
        ]


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
    membership_year = models.SmallIntegerField(default=0)
    reference = models.CharField(max_length=80)
    state = models.SmallIntegerField(choices = STATES, default = UNPAID)
    gocardless_action = models.CharField(max_length=10, blank=True)
    gocardless_bill_id = models.CharField(max_length=255, blank=True)
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

    def as_dict(self):
        return {
            "id": self.id,
            "state": self.STATES[self.state][1],
            "creation_date": self.creation_date.strftime(settings.DATE_INPUT_FORMATS[0]),
            "update_date": self.update_date.strftime(settings.DATE_INPUT_FORMATS[0]),
            "person": self.person.fullname(),
            "items": self.invoiceitem_set.count(),
            "email_count": self.email_count,
            "total": '{0:.2f}'.format(self.total)
            }
    def as_array(self):
        return [
            self.id,
            self.STATES[self.state][1],
            self.creation_date.strftime(settings.DATE_INPUT_FORMATS[0]),
            self.update_date.strftime(settings.DATE_INPUT_FORMATS[0]),
            self.person.first_name,
            self.person.last_name,
            self.invoiceitem_set.count(),
            self.email_count,
            '{0:.2f}'.format(self.total)
            ]
   
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

    def delete_invoice(self):
        ''' Delete the invoice and all invoice items if no invoice item has been paid '''
        for item in self.invoiceitem_set.all():
            if item.paid:
                return False
        for item in self.invoiceitem_set.all(): 
            item.delete()
        self.delete()

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
        context['reference'] = self.number
        context['items'] = self.invoiceitem_set.all().order_by('creation_date')
        context['hooks'] = self.webhook_set.all().order_by('-creation_date')
        context['state_list'] = Invoice.STATES
        context['types'] = Payment.TYPES
        context['payment_states'] = Payment.STATES
        context['full_payment_button'] = self.state == Invoice.UNPAID
        context['can_delete'] = self.email_count == 0 and self.postal_count == 0 and self.state == Invoice.UNPAID
        c_note = None
        if self.creditnote_set.count() > 0:
            c_note = self.creditnote_set.all()[0]
        context['credit_note'] = c_note
        addressee = self.person.fullname()
        if self.person.first_name == 'Unknown':
            if self.person.person_set.count() > 0:
                addressee = 'Parent or guardian of '
                for person in self.person.person_set.all():
                    addressee += person.first_name +' ' + person.last_name + ', '
                addressee = addressee[:-2]
            context['unknown'] = "Please supply your full name"  
        context['addressee'] = addressee

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
    membership_year = models.SmallIntegerField(default=0)
    type = models.SmallIntegerField(choices=TYPES, default=BACS)
    person = models.ForeignKey(Person)
    reference = models.CharField(max_length=80, blank=True, null=True)
    amount = models.DecimalField(max_digits=7, decimal_places=2, null=False)
    credited = models.DecimalField(max_digits=7, decimal_places=2, null=False, default=0)
    state = models.SmallIntegerField(choices=STATES, default=NOT_MATCHED)
    banked = models.BooleanField(default=False)
    banked_date = models.DateField(null=True)
    fee = models.DecimalField(max_digits=7, decimal_places=2, null=False, default=0)
    invoice = models.ForeignKey(Invoice,blank=True, null=True)
    def __unicode__(self):
        return "Payment:{} amount:{} credited:{} state:{}".format(
            Payment.TYPES[self.type][1],
            self.amount,
            self.credited,
            Payment.STATES[self.state][1]
            )

class CreditNote(models.Model):
    creation_date = models.DateTimeField(auto_now_add=True)
    update_date = models.DateTimeField(auto_now=True)
    membership_year = models.SmallIntegerField(default=0)
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
    def create(cls, person, type_id, description, amount):
        item = InvoiceItem.objects.create(
            person = person,
            item_type_id = type_id,
            item_date = datetime.today(),
            description = description, 
            amount = amount  
            )
        item.save()

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
    UNDER_26_AGE = 26

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

    def has_items(self):
        return self.invoiceitem_set.all().count() > 0

    def has_unpaid_invoice(self):
        for item in self.invoiceitem_set.all():
            if item.invoice and item.invoice.state == Invoice.UNPAID:
                return True
        return False

    def has_paid_invoice(self):
        for item in self.invoiceitem_set.all():
            if item.invoice and item.invoice.state == Invoice.PAID_IN_FULL:
                return True
        return False
    
    def is_invoiced(self):
        return self.invoice_item is not None

class Settings(models.Model):
    membership_year = models.SmallIntegerField(default=0)

    @classmethod
    def current(cls):
        return Settings.objects.get(pk=1)

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

    @classmethod
    def add_email_context(self, context):
        params = TextBlock.objects.filter(name='_email_params')[0].text
        blocks = params.split('|')
        context['text_intro'] = TextBlock.objects.filter(name=blocks[0])[0]
        context['text_notes'] = TextBlock.objects.filter(name=blocks[1])[0]
        context['text_closing'] = TextBlock.objects.filter(name=blocks[2])[0]
    
    @classmethod
    def exists(cls, name):
        if len(TextBlock.objects.filter(name=name)) == 1:
            return True
        return False

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