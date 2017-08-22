from datetime import date, datetime, timedelta
import os
from django.db import models
from django.db.models import Q
from django.conf import settings
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.dispatch import receiver 
from markdownx.models import MarkdownxField

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
        kids =  Person.objects.filter(sub__membership__is_adult=False).values_list('linked_id')
        parents = Person.objects.filter(id__in=kids)
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
    dob = models.DateField(null=True, blank=True, verbose_name='Date of birth')
    british_tennis = models.IntegerField(null=True, blank=True)
    notes = models.TextField(blank=True)  
    pays_own_bill = models.BooleanField(default = False)
    state = models.SmallIntegerField(choices=STATES, default=ACTIVE)
    date_joined = models.DateField(null=True, blank=True)
    hex_key = models.CharField(max_length=50, null=True, blank=True)
    allow_phone = models.BooleanField(default=True)
    allow_email = models.BooleanField(default=True)
    #
    membership = models.ForeignKey('Membership', blank=True, null=True)
    linked = models.ForeignKey('self', blank=True, null=True)
    address = models.ForeignKey('address', blank=True, null=True)
    groups = models.ManyToManyField(Group)
    unsubscribed = models.ManyToManyField('MailType')
    sub = models.ForeignKey('Subscription', blank=True, null=True)
    auth = models.OneToOneField(User, related_name='person', blank=False, null=True, on_delete=models.SET_NULL)
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
        return self.fullname

    def get_absolute_url(self):
        return reverse("person-detail", kwargs={"pk": self.pk})   
      
    def age(self, date):
        ''' return the age in years on given date
        '''
        if self.dob:
            return date.year - self.dob.year - ((date.month, date.day) < (self.dob.month, self.dob.day))
    
    def age_today(self):
        return self.age(date.today())
    
    @property
    def fullname(self):
        return self.first_name + " " + self.last_name    
    
    def active_sub(self, year):
        ''' Return the active subscription for a year if one exists. '''       
        subs = self.subscription_set.filter(sub_year=year, active=True)
        if subs.count() == 1:
            return subs[0]
        return None

    def current_sub(self):
        year = Settings.current().membership_year
        return active_sub(year)
    
    def invoices(self, state):
        return self.invoice_set.filter(state=state).order_by('update_date')                           


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

    JUNIOR_CHOICES = [
        (JUNIORS, 'Juniors & cadets'),
        (JUNIOR, 'Juniors'),
        (CADET, 'Cadets')
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
        (COACH, "Coach")
        ]

    JOIN_CHOICES =  [
        (NON_MEMBER, 'No membership (parent)'),
        (FULL, 'Full membership'),
        (OFF_PEAK, "Off peak (Mon - Fri to 6pm)"),
        (PARENT, 'Parent - to play with children'),
        (UNDER_26, 'Under 26'),
        ]

    description = models.CharField(max_length=20, verbose_name='Membership')
    long_description = models.CharField(max_length=300, verbose_name='Description', blank=True )
    is_adult = models.BooleanField(default=True)
    is_playing = models.BooleanField(default=True)
    apply_online = models.BooleanField(default=True)
    cutoff_age = models.IntegerField(default=0)
    
    def __unicode__(self):
        return self.description

    @classmethod
    def create(cls, id, description):
        mem = cls(id = id, description = description)
        mem.save()
        return mem

    @classmethod
    def adult_choices(cls, membership_id=0, description=False):
        '''
        Return a list of adult membership choices for membership field
        If description is set return descriptions else return list for choice widget
        '''
        if membership_id:
            qs = Membership.objects.filter(pk=membership_id)
        else:
            qs = Membership.objects.filter(
            is_adult=True, cutoff_age=0, apply_online=True
            ).order_by('id')
        if description:
            year = Settings.current().membership_year
            result = []
            for record in qs:
                fee=Fees.objects.filter(membership_id=record.id, sub_year=year)[0]
                result.append([record.description, fee.annual_sub, fee.joining_fee, record.long_description])
            return result
        else:
            return list(qs.values_list('id', 'description'))
    
class AdultApplication(models.Model):
    '''
    Additional data captured during application
    '''
    BEGINNER = 0
    IMPROVER = 1
    RUSTY = 2
    INTERMEDIATE = 3
    ADVANCED = 4

    ABILITIES = [
        (BEGINNER, 'Beginner'),
        (IMPROVER, 'Improver'),
        (RUSTY, 'Rusty - Returning to tennis'),
        (INTERMEDIATE, 'Intermediate - average club player'),
        (ADVANCED, 'Advanced  - club team player'),
        ]

    MEMBER = 0
    SCHOOL = 1
    WEB = 2
    LTA = 3
    FLYER = 4
    AD = 5
    OTHER = 6

    SOURCES = [
        (MEMBER, 'Friend, relative or member'),
        (SCHOOL, 'School'),
        (WEB, 'Web search'),
        (LTA, 'LTA search or promotion'),
        (FLYER, 'Leaflet'),
        (AD, 'Advertisement'),
        (OTHER, 'Other'),
        ]
    membership_id = models.SmallIntegerField('Membership type',
                                          choices = Membership.ADULT_CHOICES,
                                          default = Membership.FULL)
    ability = models.SmallIntegerField('Judge your tennnis ability',
                                       choices = ABILITIES, default = BEGINNER)
    singles = models.BooleanField('Singles', default=False)
    doubles = models.BooleanField('Doubles', default=False)
    coaching1 = models.BooleanField('Individual coaching', default=False)
    coaching2 = models.BooleanField('Group coaching', default=False)
    daytime = models.BooleanField('Daytime tennis', default=False)
    family = models.BooleanField('Family tennis', default=False)
    social = models.BooleanField('Social tennis', default=False)
    competitions = models.BooleanField('Club competitions', default=False)
    teams = models.BooleanField('Team tennis', default=False)

    club = models.CharField('Name of previous tennis club (if any)',
                            max_length=80, blank=True)
    source = models.SmallIntegerField('How did you hear about us?',
                                      choices = SOURCES, default = WEB,)
    person = models.ForeignKey(Person, blank=True, null=True)
      
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
    PENDING_GC = 6
    # For filtering
    NOT_CANCELLED = 7

    STATES = (
        (UNPAID, "Unpaid"),
        (PART_PAID, "Part paid"),
        (PAID_IN_FULL, "Paid"),
        (CANCELLED, "Cancelled"),
        (PART_CREDIT_NOTE, "Part paid & credit note"),
        (ERROR, "Error - overpaid"),
        (PENDING_GC, "Pending GoCardless"),       
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
    # payment_set
    def __unicode__(self):
        return "Invoice {}, {} items, total = {}".format(
            Invoice.STATES[self.state][1],
            self.invoiceitem_set.count(),
            self.total
            )

    @property
    def payment_state(self):
        '''
        Pending Go Cardless payments do not update invoice state automatically
        So this property deals with that case
        '''
        if self.state == Invoice.PAID_IN_FULL:
            return Invoice.STATES[self.state][1]
        elif self.gocardless_bill_id != "":
            return Invoice.STATES[Invoice.PENDING_GC][1]
        else:
            return Invoice.STATES[self.state][1]

    def as_dict(self):
        return {
            "id": self.id,
            "state": self.STATES[self.state][1],
            "creation_date": self.creation_date.strftime(settings.DATE_INPUT_FORMATS[0]),
            "update_date": self.update_date.strftime(settings.DATE_INPUT_FORMATS[0]),
            "person": self.person.fullname,
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

    def paid_items_count(self):
        return self.invoiceitem_set.filter(paid=True).count()

    def unpaid_items_count(self):
        return self.invoiceitem_set.filter(paid=False).count()

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
        context['can_delete'] = (self.email_count == 0 and self.postal_count == 0 and self.state == Invoice.UNPAID)
         
        c_note = None
        if self.creditnote_set.count() > 0:
            c_note = self.creditnote_set.all()[0]
        context['credit_note'] = c_note
        addressee = self.person.fullname
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
        (BACS, "BACS"),
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

    PAID = 0
    UNPAID = 1
    ALL = 2
    PAYCHOICES = [
        (PAID,'Paid'),
        (UNPAID,'Unpaid'),
        (ALL,'All')]

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
    invoice = models.ForeignKey(Invoice, blank=True, null=True)

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

    @property
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
    membership = models.ForeignKey(Membership, blank=True, null=True)
    new_member = models.BooleanField(default=False)
    paid = models.BooleanField(default=False)
    active = models.BooleanField(default=False)
    resigned = models.BooleanField(default=False)
    invoiced_month = models.SmallIntegerField()
    no_renewal = models.BooleanField(default=False)       

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

    @property
    def membership_fulldescription(self):
        ''' Return a description including resigned case '''
        desc = self.membership.description
        if self.resigned:
            # post 2017 data has old membership in parenthesis"
            if desc != "Resigned":
                desc = "Resigned ({})".format(desc)
        return desc

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


class Editor(models.Model):

    text = MarkdownxField()

class TextBlock(models.Model):
    BLOCK = 0
    BEE_HTML = 1
    BEE_TEMPLATE = 2

    TYPES = (
        (BLOCK, "Text block"),
        (BEE_HTML, "HTML document"),
        (BEE_TEMPLATE, "Bee editor template"),
        )

    name = models.CharField(max_length=30, null=False, blank=False)
    type = models.SmallIntegerField(choices=TYPES, default=BLOCK)
    text = models.TextField(null=False, blank=False)

    def __unicode__(self):
        return "{0}: {1}".format(self.type, self.name)

    @classmethod
    def add_email_context(self, context):
        blocks = TextBlock.email_params()
        if blocks[0] > 0:
            context['text_intro'] = TextBlock.objects.get(pk=blocks[0])
        if blocks[1] > 0:
            context['text_notes'] = TextBlock.objects.get(pk=blocks[1])
        if blocks[2] > 0:
            context['text_closing'] = TextBlock.objects.get(pk=blocks[2])
    
    @classmethod
    def exists(cls, name):
        if len(TextBlock.objects.filter(name=name)) == 1:
            return True
        return False

    @classmethod
    def email_params(self):
        ''' return 3 integers representing the blocks for an invoice mail '''
        blocks = TextBlock.objects.filter(name='_invoice_mail')
        if len(blocks) == 1:
            try:
                ids = blocks[0].text.split("|")         
                for i in range(0,len(ids)-1):
                    ids[i]=int(ids[i])
                    if len(TextBlock.objects.filter(pk=ids[i])) == 0:
                        ids[i] = -1  
                return ids
            except ValueError:
                pass
        return [-1,-1,-1]  


class MailTemplate(models.Model):
    name = models.CharField(max_length=50, null=False, blank=False)
    json = models.TextField(null=False, blank=False)
    
    def __unicode__(self):
        return self.name


class MailCampaign(models.Model):

    class Meta:
        ordering = ['-update_date']
    
    creation_date = models.DateTimeField(auto_now_add=True)
    update_date = models.DateTimeField(auto_now=True)
    sent_date = models.DateTimeField(null=True)
    name = models.CharField(max_length=50, null=False, blank=False)
    text = models.TextField(null=True, blank=False)
    json = models.TextField(null=True, blank=True)
    mail_template = models.ForeignKey(MailTemplate, null=True)

    def __unicode__(self):
        return self.name

class MailType(models.Model):
    name = models.CharField(max_length=30, null=False, blank=False)
    description = models.CharField(max_length=300, null=False, blank=False)
    can_unsubscribe = models.BooleanField(default=True)
    sequence = models.IntegerField(default=0)
    mail_campaign = models.ForeignKey(MailCampaign, null=True, blank=True)

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