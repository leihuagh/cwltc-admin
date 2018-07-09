from decimal import Decimal
from django.db import models
from django.contrib.auth.models import User
from members.models import Person, ItemType

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
            return Decimal((self.sale_price - self.cost_price)/self.sale_price * 100)
        return Decimal(0)

    def margin_formatted(self):
        return str(self.margin().quantize(TWO_PLACES))+'%'

    def to_dict(self):
        '''
        Create a dictionary item used while transaction is being created
        Decimal fields are converted to integers so they can be saved in json format
        '''
        item_dict = {}
        item_dict['id'] = self.id
        item_dict['description'] = self.description
        item_dict['sale_price'] = int(100 * self.sale_price)
        item_dict['cost_price'] = int(100 * self.cost_price)
        item_dict['quantity'] = 1
        item_dict['total'] = chr(163) + " " + str(self.sale_price)
        return item_dict 


class Layout(models.Model):
    name = models.CharField(max_length=25, blank=True)
    item_type = models.ForeignKey(ItemType, on_delete=models.CASCADE, default=ItemType.BAR, null=False)
    title = models.CharField(max_length=80)
    sub_title = models.CharField(max_length=256, blank=True)
    line_2 = models.CharField(max_length=256, blank=True)
    line_3 = models.CharField(max_length=256, blank=True)
    button_text = models.CharField(max_length=30, null=False, blank=False)

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
    description = models.CharField(max_length=50, blank=True) # holds the row description when col=0

    def __str__(self):
        name = "Layout: {}, Row: {}, Col: {}, ".format(str(self.layout.name),
                                                       str(self.row), str(self.col))
        if self.item:
            name += self.item.description
        return name


class Transaction(models.Model):
    creation_date = models.DateTimeField(auto_now_add=True)
    creator = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    person = models.ForeignKey(Person, on_delete=models.SET_NULL, blank=True, null=True)
    total = models.DecimalField(max_digits=5, decimal_places=2, null=False)
    complimentary = models.BooleanField(default=False)
    cash = models.BooleanField(default=False)
    billed = models.BooleanField()
    split = models.BooleanField(default=False)
    terminal = models.IntegerField(default=1)
    item_type = models.ForeignKey(ItemType, on_delete=models.CASCADE, default=ItemType.BAR, null=False)
    attended = models.BooleanField(default=False)

    def __str__(self):
        name = self.person.fullname if self.person else "Cash"
        return "{} {} {}".format(str(self.id),
                                 name,
                                 str(self.total))


class LineItem(models.Model):
    item = models.ForeignKey(Item, on_delete=models.SET_NULL, null=True)
    sale_price = models.DecimalField(max_digits=5, decimal_places=2, null=False)
    cost_price = models.DecimalField(max_digits=5, decimal_places=2, null=False)
    quantity = models.IntegerField()
    transaction = models.ForeignKey(Transaction, on_delete=models.CASCADE, blank=True, null=True)
    
    def __str__(self):
        return "{} {}".format(self.item.description, self.transaction_id)


class PosPayment(models.Model):
    transaction = models.ForeignKey(Transaction, on_delete=models.CASCADE, blank=True, null=True)
    person = models.ForeignKey(Person, on_delete=models.SET_NULL, blank=True, null=True)
    billed = models.BooleanField()
    amount = models.DecimalField(max_digits=5, decimal_places=2, null=False)

    def __str__(self):
        return "{} {} {} {}".format(str(self.id),
                                    str(self.person.fullname),
                                    str(self.amount),
                                    str(self.billed))


class PosPing(models.Model):
    terminal = models.SmallIntegerField()
    time = models.DateTimeField()

    def __str__(self):
        return f'Terminal: {terminal} time: {time}'


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


class VisitorBook(models.Model):
    date = models.DateField(auto_now=True)
    member = models.ForeignKey(Person, on_delete=models.CASCADE, blank=False, null=False)
    visitor = models.ForeignKey(Visitor, on_delete=models.CASCADE, blank=False, null=False)
    fee = models.DecimalField(max_digits=5, decimal_places=2)
    billed = models.BooleanField()

