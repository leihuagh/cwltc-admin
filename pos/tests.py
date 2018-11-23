from django.test import TestCase
from factory.django import DjangoModelFactory
from pos.models import *
from members.models import Person, ItemType, Settings
from django.contrib.auth.models import User
from .services import *
import logging

logger = logging.getLogger('factory').setLevel(logging.WARNING)

TEAS_ITEM_TYPE = 3
BAR_ITEM_TYPE = 4
VISITOR_ITEM_TYPE = 5


class LayoutFactory(DjangoModelFactory):
    class Meta:
        model = Layout
    name = "Layout"


class PersonFactory(DjangoModelFactory):
    class Meta:
        model = Person


class UserFactory(DjangoModelFactory):
    class Meta:
        model = User  
    # first_name = "John"
    # last_name = "Doe"


class ItemTypeFactory(DjangoModelFactory):
    class Meta:
        model = ItemType


class BarItemTypeFactory(ItemTypeFactory):
    id = BAR_ITEM_TYPE
    description = 'Bar'
    pos = True


class TeasItemTypeFactory(ItemTypeFactory):
    id = TEAS_ITEM_TYPE
    description = 'Teas'
    pos = True


class ItemFactory(DjangoModelFactory):
    class Meta:
        model = Item

    description = 'Bottle of beer'
    button_text = 'Beer'
    sale_price = 1.50
    cost_price = 1.00

# Useful constants
UNBILLED = Transaction.BilledState.UNBILLED.value
PART_BILLED = Transaction.BilledState.PART_BILLED.value
BILLED = Transaction.BilledState.BILLED.value

class PosTestCase(TestCase):

    def create_bar_layout(self):
        layout = LayoutFactory.create()
        layout.item_type = BarItemTypeFactory.create()
        layout.save()
        return layout

    def create_teas_layout(self):
        layout = LayoutFactory.create()
        layout.item_type = TeasItemTypeFactory.create()
        layout.save()
        return layout

    def init_receipt(self, count):
        receipt = []
        item = ItemFactory.create()
        for i in range(count):
            receipt.append(item.to_dict())
        return receipt


    def test_create_transaction(self):
        user = UserFactory.create()
        layout = self.create_bar_layout()
        person = PersonFactory.create()
        receipt = self.init_receipt(10)
        person_list = [{'id': person.id, 'name': person.fullname, 'amount': 1500}]
        create_transaction_from_receipt(user.id, 1, layout.id, receipt, 1500, person_list, attended=False)
        transactions = Transaction.objects.all()
        self.assertEqual(len(transactions), 1)
        t0 = transactions[0]
        self.assertEqual(t0.total, Decimal(15.0))
        self.assertFalse(t0.complimentary)
        self.assertFalse(t0.cash)
        items = LineItem.objects.all()
        self.assertEqual(len(items), 10)
        payments = PosPayment.objects.all()
        self.assertEqual(len(payments), 1)
        self.assertEqual(payments[0].total, Decimal(15.0))
        unbilled = PosPayment.billing.unbilled_total(person, ItemType.BAR)
        self.assertEqual(unbilled, Decimal(15.0))

    def test_create_split_transaction(self):
        user = UserFactory.create()
        layout = self.create_bar_layout()
        receipt = self.init_receipt(10)
        person1 = PersonFactory.create()
        person2 = PersonFactory.create()
        person_list = [{'id': person1.id, 'name': person1.fullname, 'amount': 1000},
                       {'id': person2.id, 'name': person2.fullname, 'amount': 500}]
        create_transaction_from_receipt(user.id, 1, layout.id, receipt, 1500, person_list, attended=False)
        # There should be single transaction
        self.assertEqual (Transaction.objects.all().count(), 1)
        # with 2 payments
        payments = Transaction.objects.all()[0].pospayment_set.all()
        self.assertEqual(len(payments), 2)
        p1 = payments[0]
        p2 = payments[1]
        # person 1 pays 10
        self.assertEqual(p1.total, Decimal(10.0))
        self.assertEqual(p1.person_id, person1.id)
        # person 2 pays 5
        self.assertEqual(p2.total, Decimal(5.0))
        self.assertEqual(p2.person_id, person2.id)

        # test billling split transaction
        # Transaction starts in unbilled state
        self.assertEqual(Transaction.objects.filter(billed=UNBILLED).count(), 1)
        # Unbilled total for person 1 is 10
        self.assertEqual(PosPayment.billing.unbilled_total(person1, ItemType.BAR), 10)
        # Unbillled total for person 2 is 5
        self.assertEqual(PosPayment.billing.unbilled_total(person2, ItemType.BAR), 5)
        PosPayment.billing.process(person1)
        # person 1 has been processed so unbilled payments = 0
        self.assertEqual(PosPayment.billing.unbilled_total(person1, ItemType.BAR), 0)
        # person 2 still has unbilled payment
        self.assertEqual(PosPayment.billing.unbilled_total(person2, ItemType.BAR), 5)
        # Should be 1 transaction with billed state = part paid
        self.assertEqual(Transaction.objects.filter(billed=PART_BILLED).count(), 1)
        # Now process person 2
        PosPayment.billing.process(person2)
        # no unbilled payments for person 2
        self.assertEqual(PosPayment.billing.unbilled_total(person2, ItemType.BAR), 0)
        # Transaction should be fully billed
        self.assertEqual(Transaction.objects.count(), 1)
        self.assertEqual(Transaction.objects.filter(billed=BILLED).count(), 1)


    def test_create_complimentary_transaction(self):
        user = UserFactory.create()
        layout = self.create_bar_layout()
        receipt = self.init_receipt(10)
        person_list = [{'id': -1, 'name': 'complimentary', 'amount': 1500}]
        create_transaction_from_receipt(user.id, 1, layout.id, receipt, 1500, person_list, False)
        t0 = Transaction.objects.all()[0]
        self.assertTrue(t0.complimentary)
        self.assertFalse(t0.cash)

    def test_create_cash_transaction(self):
        user = UserFactory.create()
        layout = self.create_bar_layout()
        receipt = self.init_receipt(1)
        person_list = []
        create_transaction_from_receipt(user.id, 1, layout.id, receipt, 1500, person_list, False)
        t0 = Transaction.objects.all()[0]
        self.assertFalse(t0.complimentary)
        self.assertTrue(t0.cash)


    def test_create_invoice_items(self):
        user = UserFactory.create()
        layout_bar = self.create_bar_layout()
        layout_teas = self.create_teas_layout()
        # Create a visitors item type that should be ignored
        VisitorsItemTypeFactory.create()
        person1 = PersonFactory.create()
        person2 = PersonFactory.create()
        person1_list = [{'id': person1.id, 'name': person1.fullname, 'amount': 1500}]
        person2_list = [{'id': person2.id, 'name': person2.fullname, 'amount': 500}]
        receipt1 = self.init_receipt(10) # £15
        receipt2 = self.init_receipt(5)

        # person 1 £30 in bar, £15 in teas
        create_transaction_from_receipt(user.id, 1, layout_bar.id, receipt1, 1500, person1_list, False)
        create_transaction_from_receipt(user.id, 1, layout_bar.id, receipt1, 1500, person1_list, False)
        create_transaction_from_receipt(user.id, 1, layout_teas.id, receipt1, 1500, person1_list, False)
        # Unbilled amounts should be £30 in bar, £15 in teas
        self.assertEqual(PosPayment.billing.unbilled_total(person1, ItemType.BAR), Decimal(30.0))
        self.assertEqual(PosPayment.billing.unbilled_total(person1, ItemType.TEAS), Decimal(15.0))

        # person 2 £5 in bar, £10 in teas
        create_transaction_from_receipt(user.id, 1, layout_teas.id, receipt2, 500, person2_list, False)
        create_transaction_from_receipt(user.id, 1, layout_teas.id, receipt2, 500, person2_list, False)
        create_transaction_from_receipt(user.id, 1, layout_bar.id, receipt2, 500, person2_list, False)
        # Unbilled amounts should be £5 in bar, £10 in teas
        self.assertEqual(PosPayment.billing.unbilled_total(person2, ItemType.BAR), Decimal(5.0))
        self.assertEqual(PosPayment.billing.unbilled_total(person2, ItemType.TEAS), Decimal(10.0))



        # start with no unbilled transactions
        self.assertEqual(Transaction.objects.filter(billed=UNBILLED).count(), 6)
        # generate data for 1 person only but do not process it
        bill_data_list = PosPayment.billing.billing_data(person1)
        self.assertEqual(len(bill_data_list), 2)
        # validate generated data list for BAR
        bill = bill_data_list[0]
        self.assertEqual(bill.item_type.id, BAR_ITEM_TYPE)
        self.assertEqual(len(bill.transactions), 2)
        self.assertEqual(len(bill.records), 2)
        self.assertEqual(len(bill.dict), 1)
        # validate generated data list for TEAS
        bill = bill_data_list[1]
        self.assertEqual(bill.item_type.id, TEAS_ITEM_TYPE)
        self.assertEqual(len(bill.transactions), 1)
        self.assertEqual(len(bill.records), 1)
        self.assertEqual(len(bill.dict), 1)
        # process all the Pos billing data
        self.assertEqual(PosPayment.billing.process(), 4)
        items = InvoiceItem.objects.all()
        # Should be 4 invoice items created
        self.assertEqual(items.count(), 4)
        # person 1 total should be 30 for bar
        bar1 = items.filter(person=person1, item_type_id = BAR_ITEM_TYPE)
        self.assertEqual(len(bar1), 1)
        self.assertEqual(bar1[0].amount, 30)
        # person 1 total should be 15 for teas
        teas1 = items.filter(person=person1, item_type_id = TEAS_ITEM_TYPE)
        self.assertEqual(len(teas1), 1)
        self.assertEqual(teas1[0].amount, 15)
        # person 2 total should be 5 for bar
        bar2 = items.filter(person=person2, item_type_id = BAR_ITEM_TYPE)
        self.assertEqual(len(bar2), 1)
        self.assertEqual(bar2[0].amount, 5)
        # person 2 total should be 10 for teas
        teas2 = items.filter(person=person2, item_type_id = TEAS_ITEM_TYPE)
        self.assertEqual(len(teas2), 1)
        self.assertEqual(teas2[0].amount, 10)
        # Should be 6 billed transactions
        self.assertEqual(Transaction.objects.filter(billed=BILLED).count(), 6)
        # Should be 6 billed payments
        self.assertEqual(PosPayment.objects.filter(billed=True).count(), 6)
        # Unbilled amounts should now be 0
        self.assertEqual(PosPayment.billing.unbilled_total(person1, ItemType.BAR), 0)
        self.assertEqual(PosPayment.billing.unbilled_total(person1, ItemType.TEAS), 0)
        self.assertEqual(PosPayment.billing.unbilled_total(person2, ItemType.BAR), 0)
        self.assertEqual(PosPayment.billing.unbilled_total(person2, ItemType.TEAS), 0)


class VisitorsItemTypeFactory(ItemTypeFactory):
    id = VISITOR_ITEM_TYPE
    description = 'Visitors'
    pos = False


class VisitorBookFactory(DjangoModelFactory):
    class Meta:
        model = VisitorBook
    billed = False

class VisitorFactory(DjangoModelFactory):
    class Meta:
        model = Visitor


class JuniorVisitorFactory(VisitorFactory):
    junior=True
    

class VistorBookTestCase(TestCase):

    def test_visitor_billing_all_members(self):
        VisitorsItemTypeFactory.create()
        person1 = PersonFactory.create()
        person2 = PersonFactory.create()
        visitor1 = VisitorFactory.create()
        visitor2 = VisitorFactory.create()
        visitor3 = VisitorFactory.create()
        visitor4 = JuniorVisitorFactory.create()
        VisitorBookFactory.create(member=person1, visitor=visitor1, fee=6)
        VisitorBookFactory.create(member=person1, visitor=visitor2, fee=6)
        VisitorBookFactory.create(member=person2, visitor=visitor3, fee=6)
        VisitorBookFactory.create(member=person2, visitor=visitor4, fee=3)
        count = VisitorBook.billing.process()
        self.assertEqual(count, 2)
        items = InvoiceItem.objects.all()
        self.assertEqual(items.count(), 2)

        invs = items.filter(person=person1, item_type_id = VISITOR_ITEM_TYPE)
        self.assertEqual(len(invs), 1)
        self.assertEqual(invs[0].amount, 12)

        invs = items.filter(person=person2, item_type_id = VISITOR_ITEM_TYPE)
        self.assertEqual(len(invs), 1)
        self.assertEqual(invs[0].amount, 9)

        self.assertEqual(VisitorBook.objects.filter(billed=False).count(), 0)
        self.assertEqual(VisitorBook.objects.filter(billed=True).count(), 4)

    def test_visitor_billing_one_member(self):
        VisitorsItemTypeFactory.create()
        person1 = PersonFactory.create()
        person2 = PersonFactory.create()
        visitor1 = VisitorFactory.create()
        visitor2 = VisitorFactory.create()
        VisitorBookFactory.create(member=person1, visitor=visitor1, fee=6)
        VisitorBookFactory.create(member=person2, visitor=visitor2, fee=6)
        count = VisitorBook.billing.process(person1)
        self.assertEqual(count, 1)
        items = InvoiceItem.objects.all()
        self.assertEqual(items.count(), 1)
        self.assertEqual(items[0].amount, 6)
        self.assertEqual(items[0].person, person1)
        unbilled = VisitorBook.objects.filter(billed=False)[0]
        self.assertEqual(unbilled.member, person2)
        billed = VisitorBook.objects.filter(billed=True)[0]
        self.assertEqual(billed.member, person1)
