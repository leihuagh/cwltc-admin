from django.db import models
from django.contrib.auth.models import User
from members.models import Person, ItemType


class Item(models.Model):
    description = models.CharField(max_length=50)
    button_text = models.CharField(max_length=25)
    sale_price = models.DecimalField(max_digits=5, decimal_places=2, null=False)
    cost_price = models.DecimalField(max_digits=5, decimal_places=2, null=False)
    item_type = models.ForeignKey(ItemType, default=4, null=False)

    def __str__(self):
        return self.button_text
    
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


    def __str__(self):
        return self.name


class Location(models.Model):

    ROW_MAX = 6
    COL_MAX = 6
    row = models.IntegerField()
    col = models.IntegerField()
    visible = models.BooleanField()
    item = models.ForeignKey(Item, blank=True, null=True)
    layout = models.ForeignKey(Layout, blank=True, null=True)

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
        return "{} {} {} {}".format(str(self.id),
                                    str(self.person.first_name),
                                    str(self.person.last_name),
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