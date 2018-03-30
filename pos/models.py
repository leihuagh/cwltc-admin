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
    name = models.CharField(max_length=25)
    item_type = models.ForeignKey(ItemType, on_delete=models.CASCADE, default=ItemType.BAR, null=False)

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
    creator = models.ForeignKey(User)
    person = models.ForeignKey(Person, blank=True, null=True)
    total = models.DecimalField(max_digits=5, decimal_places=2, null=False)
    complementary = models.BooleanField(default=False)
    cash = models.BooleanField(default=False)
    billed = models.BooleanField()
    layout = models.ForeignKey(Layout, blank=True, null=True)
    split = models.BooleanField(default=False)
    
    def __str__(self):
        name = self.person.fullname if self.person else "Cash"
        return "{} {} {}".format(str(self.id),
                                 name,
                                 str(self.total))


class LineItem(models.Model):
    item = models.ForeignKey(Item)
    sale_price = models.DecimalField(max_digits=5, decimal_places=2, null=False)
    cost_price = models.DecimalField(max_digits=5, decimal_places=2, null=False)
    quantity = models.IntegerField()
    transaction = models.ForeignKey(Transaction, blank=True, null=True)
    
    def __str__(self):
        return "{} {}".format(self.item.description, self.transaction_id)


class PosPayment(models.Model):
    transaction = models.ForeignKey(Transaction, blank=True, null=True)
    person = models.ForeignKey(Person)
    billed = models.BooleanField()
    amount = models.DecimalField(max_digits=5, decimal_places=2, null=False)

    def __str__(self):
        return "{} {} {} {}".format(str(self.id),
                                    str(self.person.fullname),
                                    str(self.amount),
                                    str(self.billed))

class PosAdmin(models.Model):
    attended_mode = models.BooleanField(default=False)
    default_layout = models.ForeignKey(Layout, blank=True, null=True)


    def __str__(self):
        return f'Admin: {self.admin_mode}, Layout: {self.default_layout.name}'\

    @classmethod
    def record(cls):
        records = PosAdmin.objects.all()
        if records:
            return records[0]
        else:
            return PosAdmin.objects.create(attended_mode=False, default_layout=None)

