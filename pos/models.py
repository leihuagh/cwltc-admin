from __future__ import unicode_literals

from django.db import models
from django.contrib.auth.models import User
from members.models import Person

class Item(models.Model):
    description = models.CharField(max_length=50)
    button_text = models.CharField(max_length=25)
    sale_price = models.DecimalField(max_digits=5, decimal_places=2, null=False)
    cost_price = models.DecimalField(max_digits=5, decimal_places=2, null=False)
     
    def __unicode__(self):
        return self.description 
    
    def to_dict(self):
        '''
        Create a dictionary item used while transaction is being cretaed
        Decimla fields are converted to integers do theay can be saved in json format
        '''
        item_dict = {}
        item_dict['id'] = self.id
        item_dict['description'] = self.description
        item_dict['sale_price'] = int(100 * self.sale_price)
        item_dict['cost_price'] = int(100 * self.cost_price)
        item_dict['quantity'] = 1
        item_dict['total'] = unichr(163) + " " + str(self.sale_price)
        return item_dict 

class Layout(models.Model):
    name = models.CharField(max_length=25)

    def __unicode__(self):
        return self.name

class Location(models.Model):
    row = models.IntegerField()
    col = models.IntegerField()
    visible = models.BooleanField()
    item = models.ForeignKey(Item, blank=True, null=True)
    layout = models.ForeignKey(Layout, blank=True, null=True)

    def __unicode__(self):
        name = "Row {} Col {} ".format(str(self.row), str(self.col))
        if self.item:
            name += self.item.description
        return name

class Transaction(models.Model):
    creation_date = models.DateTimeField(auto_now_add=True)
    creator = models.ForeignKey(User)
    person = models.ForeignKey(Person)
    total = models.DecimalField(max_digits=5, decimal_places=2, null=False)
    
    def __unicode__(self):
        return str(self.id)



class LineItem(models.Model):
    item = models.ForeignKey(Item)
    sale_price = models.DecimalField(max_digits=5, decimal_places=2, null=False)
    cost_price = models.DecimalField(max_digits=5, decimal_places=2, null=False)
    quantity = models.IntegerField()
    transaction = models.ForeignKey(Transaction, blank=True, null=True)
    
    def __unicode__(self):
        return self.item.description
