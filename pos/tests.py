from django.test import TestCase
from pos.models import *
from members.models import Person, ItemType, Settings
from django.contrib.auth.models import User
from .services import *
import factory
import logging

logger = logging.getLogger('factory').setLevel(logging.WARNING)


class LayoutFactory(factory.DjangoModelFactory):
    class Meta:
        model = Layout
    name = "Layout"


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
    gender = 'M'
    first_name = factory.Sequence(lambda n: 'ian%s' % n)
    last_name = 'Stewart'
    mobile_phone = '07985748548'
    email = 'is@ktconsultants.co.uk'
    dob = '1954-07-07'
    state = Person.ACTIVE     


class UserFactory(factory.Factory):
    class Meta:
        model = User  
    first_name = "John"
    last_name = "Doe"


class ItemTypeFactory(factory.DjangoModelFactory):
    class Meta:
        model = ItemType
    id = 4
    description = 'Bar'


class ItemFactory(factory.DjangoModelFactory):
    class Meta:
        model = Item

    description = 'Bottle of beer'
    button_text = 'Beer'
    sale_price = 1.50
    cost_price = 1.00


class PosTestCase(TestCase):

    def init(self):
        layout = LayoutFactory.create()
        item_type = ItemTypeFactory.create()
        item_type.save()
        layout.item_type = item_type
        layout.save()
        user = UserFactory.create()
        user.save()
        item = ItemFactory.create()
        receipt = []
        for i in range(10):
            receipt.append(item.to_dict())
        return layout, user, receipt

    def test_create_transaction(self):
        layout, user, receipt = self.init()
        person = PersonFactory.create()
        person_list = [{'id': person.id, 'name': person.fullname, 'amount': 1500}]
        result = create_transaction_from_receipt(user.id, 1, layout.id, receipt, 15, person_list, False)
        transactions = Transaction.objects.all()
        self.assertEqual(len(transactions), 1)
        t0 = transactions[0]
        self.assertEqual(t0.total, Decimal(15.0))
        self.assertFalse(t0.complimentary)
        self.assertFalse(t0.cash)
        items = LineItem.objects.all()
        self.assertEqual(len(items), 10)
        payments = PosPayment.objects.all()
        self.assertEqual(payments[0].amount, Decimal(15.0))

    def test_create_split_transaction(self):
        layout, user, receipt = self.init()
        person = PersonFactory.create()
        person2 = PersonFactory.create()
        person_list = [{'id': person.id, 'name': person.fullname, 'amount': 1000},
                       {'id': person2.id, 'name': person2.fullname, 'amount': 500}]
        result = create_transaction_from_receipt(user.id, 1, layout.id, receipt, 15, person_list, False)
        transactions = Transaction.objects.all()
        payments = PosPayment.objects.all()
        self.assertEqual(len(payments), 2)
        p1 = payments[0]
        p2 = payments[1]
        self.assertEqual(p1.amount, Decimal(10.0))
        self.assertEqual(p1.person_id, person.id)
        self.assertEqual(p2.amount, Decimal(5.0))
        self.assertEqual(p2.person_id, person2.id)

    def test_create_complimentary_transaction(self):
        layout, user, receipt = self.init()
        person_list = [{'id': -1, 'name': 'complimentary', 'amount': 1500}]
        result = create_transaction_from_receipt(user.id, 1, layout.id, receipt, 15, person_list, False)
        t0 = Transaction.objects.all()[0]
        self.assertTrue(t0.complimentary)
        self.assertFalse(t0.cash)

    def test_create_cash_transaction(self):
        layout, user, receipt = self.init()
        person_list = []
        result= create_transaction_from_receipt(user.id, 1, layout.id, receipt, 15, person_list, False)
        t0 = Transaction.objects.all()[0]
        self.assertFalse(t0.complimentary)
        self.assertTrue(t0.cash)


    def test_create_invoice_items(self):
        layout, user, receipt = self.init()
        person = PersonFactory.create()
        person_list = [{'id': person.id, 'name': person.fullname, 'amount': 1500}]
        result = create_transaction_from_receipt(user.id, 1, layout.id, receipt, 15, person_list, False)
        result = create_transaction_from_receipt(user.id, 1, layout.id, receipt, 15, person_list, False)
        person2 = PersonFactory.create()
        person_list = [{'id': person2.id, 'name': person2.fullname, 'amount': 1500}]
        result = create_transaction_from_receipt(user.id, 1, layout.id, receipt, 15, person_list, False)
        result = create_transaction_from_receipt(user.id, 1, layout.id, receipt, 15, person_list, False)
        create_invoiceitems_from_payments(item_type_id=4)
        items = InvoiceItem.objects.all()
        self.assertEqual(items.count(), 2)
        self.assertEqual(items[0].amount, 30)
        self.assertEqual(items[0].person_id, person.id)
        self.assertEqual(items[1].amount, 30)
        self.assertEqual(items[1].person_id, person2.id)