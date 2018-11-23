from datetime import datetime, date
from decimal import Decimal

from django.contrib.auth.models import User
from django.db import models
from django.db.models import Sum
from django.utils import timezone

from events.models import Event
from members.models import Person, ItemType, ModelEnum, Settings, Subscription
from members.services import BillingData

TWO_PLACES = Decimal(10) ** -2


class Colour(models.Model):
    name = models.CharField(max_length=20, blank=False)
    fore_colour = models.CharField(max_length=7, default="#ffffff")
    back_colour = models.CharField(max_length=7, default="#008800")

    def __str__(self):
        return self.name


class Item(models.Model):
    description = models.CharField(max_length=50)
    button_text = models.CharField(max_length=25)
    sale_price = models.DecimalField(max_digits=5, decimal_places=2, null=False)
    cost_price = models.DecimalField(max_digits=5, decimal_places=2, null=False)
    item_type = models.ForeignKey(ItemType, on_delete=models.CASCADE, default=ItemType.BAR, null=False)
    colour = models.ForeignKey(Colour, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return self.button_text

    def margin(self):
        if self.sale_price != 0:
            return Decimal((self.sale_price - self.cost_price) / self.sale_price * 100)
        return Decimal(0)

    def margin_formatted(self):
        return str(self.margin().quantize(TWO_PLACES)) + '%'

    def to_dict(self):
        """
        Create a dictionary item used while transaction is being created
        Decimal fields are converted to integers so they can be saved in json format
        """
        return {'id': self.id,
                'description': self.description,
                'sale_price': int(100 * self.sale_price),
                'cost_price': int(100 * self.cost_price),
                'quantity': 1,
                'total': chr(163) + " " + str(self.sale_price)}


class Layout(models.Model):
    name = models.CharField(max_length=25, blank=True)
    item_type = models.ForeignKey(ItemType, on_delete=models.CASCADE, default=ItemType.BAR, null=False)
    title = models.CharField(max_length=80)

    def __str__(self):
        return self.name


class Location(models.Model):
    ROW_MAX = 6
    COL_MAX = 6
    row = models.IntegerField()
    col = models.IntegerField()
    visible = models.BooleanField()
    item = models.ForeignKey(Item, on_delete=models.CASCADE, blank=True, null=True)
    layout = models.ForeignKey(Layout, on_delete=models.CASCADE, blank=True, null=True)
    description = models.CharField(max_length=50, blank=True)  # holds the row description when col=0

    def __str__(self):
        name = "Layout: {}, Row: {}, Col: {}, ".format(str(self.layout.name),
                                                       str(self.row), str(self.col))
        if self.item:
            name += self.item.description
        return name


class Transaction(models.Model):
    class BilledState(ModelEnum):
        UNBILLED = 0
        PART_BILLED = 1
        BILLED = 2

    creation_date = models.DateTimeField()
    creator = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    person = models.ForeignKey(Person, on_delete=models.SET_NULL, blank=True, null=True)
    total = models.DecimalField(max_digits=5, decimal_places=2, null=False)
    complimentary = models.BooleanField(default=False)
    cash = models.BooleanField(default=False)
    billed = models.SmallIntegerField(choices=BilledState.choices(), default=0)
    split = models.BooleanField(default=False)
    terminal = models.IntegerField(default=1)
    item_type = models.ForeignKey(ItemType, on_delete=models.CASCADE, default=ItemType.BAR, null=False)
    attended = models.BooleanField(default=False)

    def __str__(self):
        name = self.person.fullname if self.person else "Cash"
        return "{} {} {}".format(str(self.id),
                                 name,
                                 str(self.total))

    def save(self, *args, **kwargs):
        """ simulate auto now for backwards compatibility but normally date comes from the pos """
        if self.creation_date is None:
            self.creation_date = timezone.now()
        super().save(*args, **kwargs)

    def update_billed(self):
        billed_count = 0
        payments = self.pospayment_set.all()
        for payment in payments:
            if payment.billed:
                billed_count += 1
        if billed_count == 0:
            self.billed = self.BilledState.UNBILLED.value
        elif billed_count == len(payments):
            self.billed = self.BilledState.BILLED.value
        else:
            self.billed = self.BilledState.PART_BILLED.value
        self.save()


class LineItem(models.Model):
    item = models.ForeignKey(Item, on_delete=models.SET_NULL, null=True)
    sale_price = models.DecimalField(max_digits=5, decimal_places=2, null=False)
    cost_price = models.DecimalField(max_digits=5, decimal_places=2, null=False)
    quantity = models.IntegerField()
    transaction = models.ForeignKey(Transaction, on_delete=models.CASCADE, blank=True, null=True)

    def __str__(self):
        return "{} {}".format(self.item.description, self.transaction_id)


class PosPaymentBillingManager(models.Manager):

    def __init__(self):
        super().__init__()
        self.person = None
        self.item_type_id = None

    def _set_dates(self, from_date, to_date):
        self.from_date = from_date if from_date else date(Settings.current_year() - 1,
                                                          Subscription.START_MONTH, 1)
        self.to_date = to_date if to_date else datetime.now().date()

    def get_queryset(self):
        qs = PosPayment.objects.filter(
            transaction__creation_date__date__range=[self.from_date, self.to_date],
            transaction__item_type=self.item_type_id,
            billed=False).order_by('person_id')
        if self.person:
            qs = qs.filter(person=self.person)
        return qs

    def unbilled_total(self, person=None, item_type_id=ItemType.BAR, from_date=None, to_date=None):
        """
        Returns total of all unbilled PosPayments of specified type for a person.
        If person os None return total for all people
        """
        self.person = person
        self._set_dates(from_date, to_date)
        self.item_type_id = item_type_id
        dict = self.get_queryset().aggregate(Sum('total'))
        total = dict['total__sum']
        return 0 if total is None else total

    def billing_data(self, person=None, item_type_id=None, from_date=None, to_date=None):
        """
        Return a BillingData object with consolidated data for specified item_type_id.
        The original POS trancastions remaim untouched.
        Person is optional and if None it means all people.
        """
        self.person = person
        self.item_type_id = item_type_id
        self._set_dates(from_date, to_date)
        records = self.get_queryset()
        transaction_ids = []
        last_id = 0
        dict = {}
        if len(records):
            for record in records:
                transaction_ids.append(record.transaction_id)
                if record.person_id:  # skip complimentary
                    if record.person_id != last_id:
                        last_id = record.person_id
                        dict[record.person_id] = Decimal(record.total)
                    else:
                        dict[record.person_id] += record.total
            transactions = Transaction.objects.filter(id__in=transaction_ids)
            return BillingData(item_type_id, dict, records, transactions)
        return None

    def process(self, person=None, item_type_id=None, from_date=None, to_date=None):
        """
        Generate invoice items from POS data
        if person is None, do it for all people
        If item_type_id is None, do it for all POS item types
        Return count of invoice items generated
        """
        count = 0
        value = Decimal(0)
        if item_type_id is None:
            item_types = ItemType.objects.filter(pos=True).values_list('id', flat=True)
        else:
            item_types = [item_type_id]
        for i_type in item_types:
            billing_data = self.billing_data(person, i_type, from_date, to_date)
            if billing_data:
                count1, value1 = billing_data.process()
                count += count1
                value += value1
        return count, value


class PosPayment(models.Model):
    transaction = models.ForeignKey(Transaction, on_delete=models.CASCADE, blank=True, null=True)
    person = models.ForeignKey(Person, on_delete=models.SET_NULL, blank=True, null=True)
    billed = models.BooleanField()
    total = models.DecimalField(max_digits=5, decimal_places=2, null=False)

    objects = models.Manager()
    billing = PosPaymentBillingManager()

    def __str__(self):
        return "{} {} {} {}".format(str(self.id),
                                    str(self.person.fullname),
                                    str(self.total),
                                    str(self.billed))


class PosApp(models.Model):
    name = models.CharField(max_length=25, blank=False)
    description = models.CharField(max_length=80)
    layout = models.ForeignKey(Layout, on_delete=models.CASCADE, blank=True, null=True)
    bar_system = models.BooleanField(default=False)
    main_system = models.BooleanField(default=True)
    allow_juniors = models.BooleanField(default=False)
    index = models.SmallIntegerField()
    enabled = models.BooleanField(default=True)
    view_name = models.CharField(max_length=25, blank=False)
    attended = models.BooleanField(default=False)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, blank=True, null=True)

    def __str__(self):
        return self.name

    def is_bar_app(self):
        if self.layout:
            return self.layout.item_type.id == ItemType.BAR
        return False

    def is_visitors_app(self):
        if self.layout:
            return self.layout.item_type.id == ItemType.VISITORS
        return False

    def is_teas_app(self):
        if self.layout:
            return self.layout.item_type.id == ItemType.TEAS
        return False


class PosPing(models.Model):
    terminal = models.SmallIntegerField()
    time = models.DateTimeField()

    # url = models.CharField(max_length=30)

    def __str__(self):
        return f'Terminal: {self.terminal} time: {self.time}'


class Visitor(models.Model):
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    email = models.EmailField(max_length=75, blank=True)
    junior = models.BooleanField(default=False)

    def __str__(self):
        return self.fullname

    @property
    def fullname(self):
        return f'{self.first_name} {self.last_name}'


class VisitorBookBillingManager(models.Manager):

    def _set_dates(self, from_date, to_date):
        self.from_date = from_date if from_date else date(Settings.current_year() - 1,
                                                          Subscription.START_MONTH, 1)
        self.to_date = to_date if to_date else datetime.now().date()

    def get_queryset(self, person):
        qs = VisitorBook.objects.filter(billed=False, date__range=[self.from_date, self.to_date])
        if person:
            qs = qs.filter(member=person)
        return qs

    def unbilled_total(self, person=None, from_date=None, to_date=None):
        self._set_dates(from_date, to_date)
        dict = self.get_queryset(person).aggregate(Sum('fee'))
        total = dict['fee__sum']
        return 0 if total is None else total

    def data(self, person=None, from_date=None, to_date=None):
        self._set_dates(from_date, to_date)
        records = self.get_queryset(person)
        last_id = 0
        dict = {}
        if len(records):
            for record in records:
                if record.member_id != last_id:
                    last_id = record.member_id
                    dict[record.member_id] = Decimal(record.fee)
                else:
                    dict[record.member_id] += record.fee
            return BillingData(ItemType.VISITORS, dict, records)
        return None

    def process(self, person=None, from_date=None, to_date=None):
        count = 0
        value = Decimal(0)
        data = self.data(person, from_date, to_date)
        if data:
            count, value = data.process()
        return count, value


class VisitorBook(models.Model):
    date = models.DateField(auto_now=True)
    member = models.ForeignKey(Person, on_delete=models.CASCADE, blank=False, null=False)
    visitor = models.ForeignKey(Visitor, on_delete=models.CASCADE, blank=False, null=False)
    fee = models.DecimalField(max_digits=5, decimal_places=2)
    billed = models.BooleanField()

    objects = models.Manager()
    billing = VisitorBookBillingManager()

    def save(self, *args, **kwargs):
        """ Override default behaviour for admin data entry case"""
        if self.date is None:
            self.date = datetime.now()
        super().save(*args, **kwargs)


class Ticker(models.Model):
    message = models.CharField(max_length=100)
    bar = models.BooleanField(default=False)
    main = models.BooleanField(default=False)

    def __str__(self):
        return self.message
