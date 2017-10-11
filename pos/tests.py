from django.test import TestCase
from pos.models import *
from members.models import Person, ItemType, Settings
from django.contrib.auth.models import User
from .services import *
import factory
import logging

logger = logging.getLogger('factory').setLevel(logging.WARNING)

class ItemFactory(factory.DjangoModelFactory):
    class Meta:
        model = Item

class LayoutFactory(factory.DjangoModelFactory):
    class Meta:
        model = Layout
    name = "Layout"


class ItemTypeFactory(factory.DjangoModelFactory):
    class Meta:
        model = ItemType
    id = 1
    description = "Item type"


#class AddressFactory(factory.DjangoModelFactory):
#    class Meta:
#        model = Address

#    address1 = '5 Field Close',
#    town = 'Molesey',
#    post_code ='KT8 2LA',
#    home_phone ='02085498658'

class PersonFactory(factory.DjangoModelFactory):
    class Meta:
        model = Person
    id = 1
    gender ='M'
    first_name = factory.Sequence(lambda n: 'ian%s' % n)
    last_name = 'Stewart'
    mobile_phone ='07985748548'
    email ='is@ktconsultants.co.uk'
    dob ='1954-07-07'
    state = Person.ACTIVE     

class UserFactory(factory.Factory):
    class Meta:
        model = User  
    first_name = "John"
    last_name = "Doe"


class ItemFactory(factory.DjangoModelFactory):
    class Meta:
        model = Item

    description = 'Bottle of beer'
    button_text = 'Beer'
    sale_price = 1.50
    cost_price = 1.00

class PosTestCase(TestCase):

    @classmethod
    def setUpTestData(cls):
        settings = Settings.objects.create(id=1, membership_year=2015)
        pass
       
              
    def test_item_to_dict(self):
        item = ItemFactory.create()
        dict = item.to_dict()
        self.assertEqual(dict['id'], item.id)
        self.assertEqual(dict['description'], item.description)
        self.assertIn(str(item.sale_price), dict['total'] )

    def test_create_transaction(self):     
        receipt = []
        for i in range(10):
            item = ItemFactory.create()
            receipt.append(item.to_dict())
        layout = LayoutFactory.create()
        person = PersonFactory.create()
        user = UserFactory.create()
        user.save()
        transaction = create_transaction_from_receipt(user.id, person.id, layout.id, receipt) 
        qs = Transaction.objects.all()
        self.assertEqual(len(qs),1)
        t1 = qs[0]
        self.assertEqual(t1.total, Decimal(15.0))
            
            
