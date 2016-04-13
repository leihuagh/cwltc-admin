from datetime import date,datetime
import pdb
import django
import pdb
from django.test import TestCase
from members.models import (Person, Address, Membership, Subscription, Fees, Invoice, Payment,
                            InvoiceItem, ItemType, CreditNote, Group)
from members.models import bill_month, sub_start_date, sub_end_date
from members.services import *
class MembersTestCase(TestCase):
    
    @classmethod
    def setUpTestData(cls):
        settings = Settings.objects.create(id=1, membership_year=2015)
        # Define membership records
        full = Membership.objects.create(id=Membership.FULL, description="Full")
        junior = Membership.objects.create(id=Membership.JUNIOR, description="Junior")
        cadet = Membership.objects.create(id=Membership.CADET, description="Cadet")
        UNDER_26 = Membership.objects.create(id=Membership.UNDER_26, description="UNDER_26")
        
        fee1 = Fees.objects.create(
            membership = full,
            sub_year = 2015,
            annual_sub = 240.00,
            monthly_sub = 21.00,
            joining_fee = 100.00
        )
        fee2 = Fees.objects.create(
            membership = junior,
            sub_year = 2015,
            annual_sub = 75.00,
            monthly_sub = 7.00,
            joining_fee = 0
        )
        fee3 = Fees.objects.create(
            membership = cadet,
            sub_year = 2015,
            annual_sub = 35.00,
            monthly_sub = 3.00,
            joining_fee = 0
        )
        fee4 = Fees.objects.create(
            membership = UNDER_26,
            sub_year = 2015,
            annual_sub = 95.00,
            monthly_sub = 7.00,
            joining_fee = 0
        )

        # Define invoice item type
        item_sub = ItemType.objects.create(
            id = ItemType.SUBSCRIPTION,
            description = 'subscription',
            credit = False
        )
        item_joining = ItemType.objects.create(
            id = ItemType.JOINING,
            description = 'Joining fee',
            credit = False
        )
        item_bar = ItemType.objects.create(
            id = ItemType.BAR,
            description = 'Bar',
            credit = False
        )
        item_disc = ItemType.objects.create(
            id = ItemType.FAMILY_DISCOUNT,
            description = 'Discount',
            credit = True
        )

        address = Address.objects.create(
            address1 = 'Address1',
            address2 = 'Address2',
            town = 'Kingston',
            post_code = 'KT2 7QX',
            home_phone = '02085498658'
        )
        # Create an adult
        adult = Person.objects.create(
            gender = 'M',
            first_name = 'First',
            last_name = 'Adult',
            mobile_phone = '07985748548',
            email = 'is@ktconsultants.co.uk',
            dob = '1954-07-07',
            british_tennis = '123456',
            notes = 'Notes',
            membership_id = Membership.FULL,
            linked = None,
            address=address,
            state = Person.ACTIVE
        )

        # Create a linked adult
        wife = Person.objects.create(
            gender = 'F',
            first_name = 'Wife of',
            last_name = 'Adult',
            mobile_phone = '07985748548',
            email = 'is@ktconsultants.co.uk',
            dob = '1954-07-07',
            british_tennis = '123456',
            notes = 'Notes',
            membership_id = Membership.FULL,
            linked = adult,
            state = Person.ACTIVE,
            address=address,
            pays_own_bill = False
        )

        # Create a child - junior
        child = Person.objects.create(
            gender = 'F',
            first_name = 'First',
            last_name = 'Child',
            mobile_phone = '07985748548',
            email = 'is@ktconsultants.co.uk',
            dob = '2000-01-01',
            british_tennis = '987654',
            notes = 'Notes',
            membership = junior,
            linked = adult,
            address=address,
            state = Person.ACTIVE
        )

        # Create a second child - cadet
        child2 = Person.objects.create(
            gender = 'F',
            first_name = 'Second',
            last_name = 'Child',
            mobile_phone = '07985748548',
            email = 'is@ktconsultants.co.uk',
            dob = '2010-01-01',
            british_tennis = '987654',
            notes = 'Notes',
            membership=cadet,
            linked = adult,
            address=address,
            state = Person.ACTIVE
        )

    def test_sub_start_and_end(self):
        m_start = bill_month(5)
        m_end = bill_month(4)
        start = sub_start_date(m_start, 2015)
        end = sub_end_date(m_end,2015)
        self.assertEqual(start, datetime(2015,5,1))
        self.assertEqual(end, datetime(2016,4,30))
        m_start = bill_month(12)
        m_end = bill_month(3)
        start = sub_start_date(m_start, 2015)
        end = sub_end_date(m_end,2015)
        self.assertEqual(start, datetime(2015,12,1))
        self.assertEqual(end, datetime(2016,3,31))

    def test_mem_count(self):
        self.assertEqual(Membership.objects.all().count(), 4, "Actual %d" % Membership.objects.all().count())

    def test_Fee_count(self):
        self.assertEqual(Fees.objects.all().count(), 4, "Actual %d" % Fees.objects.all().count())
    
    def test_annual_sub_12(self):
        mem = Membership.objects.get(description="Full")
        fee = Fees.objects.all().filter(membership=mem, sub_year=2015)[0]
        self.assertEqual(fee.calculate(1,12, Subscription.ANNUAL), 240.00)
    
    def test_monthly_sub(self):
        mem = Membership.objects.get(description="Full")
        fee = Fees.objects.all().filter(membership=mem, sub_year=2015)[0]
        self.assertEqual(fee.calculate(1, 6, Subscription.MONTHLY), 6 * 21)

    def test_quarterly_sub(self):
        mem = Membership.objects.get(description="Full")
        fee = Fees.objects.all().filter(membership=mem, sub_year=2015)[0]
        self.assertEqual(fee.calculate(1, 3, Subscription.QUARTERLY), 3 * 21)
 
    def test_adult_subscription_renewal(self):
        adult = Person.objects.all().filter(first_name = "First", last_name = "Adult")[0]
        sub = subscription_create(
            person=adult,
            sub_year=2014,
            membership_id=Membership.FULL
            )
        self.assertEqual(adult.subscription_set.count(), 1, 'actual is: %d' % adult.subscription_set.count())
        sub = adult.subscription_set.all()[0]
        self.assertEqual(sub.membership.description, 'Full', 'Sub wrong: %s' % sub.membership.description)

        subscription_activate(sub)
        subscription_renew(sub, 2015, 5)
        self.assertEqual(Subscription.objects.all().count(), 2, 'actual is: %d' % Subscription.objects.all().count())
        self.assertEqual(adult.subscription_set.count(), 2, 'actual is: %d' % adult.subscription_set.count())
        sub_new = adult.subscription_set.all().filter(sub_year=2015)[0]
        self.assertEqual(sub_new.membership.description, 'Full', 'Sub wrong: %s' % sub.membership.description)

    def test_child_age_calculation(self):
        child = Person.objects.all().filter(last_name = "Child")[0]
        child.dob = date(2000, 5, 1)
        age = child.age(date(2008, 5, 1))
        self.assertEqual(age, 8, 'Age wrong: %d' % age)
        child.dob = date(2000, 4, 30)
        age = child.age(date(2008, 5, 1))
        self.assertEqual(age, 8, 'Age wrong: %d' % age)
        child.dob = date(2000, 5, 2)
        age = child.age(date(2008, 5, 1))
        self.assertEqual(age, 7, 'Age wrong: %d' % age)

    def test_child_subscription_renewal(self):
        child = Person.objects.all().filter(last_name = "Child")[0]
        child.dob = date(2007,5,2)
        #import pdb; pdb.set_trace()
        sub_15 = subscription_create(
            person=child,
            sub_year=2015,
            membership_id=Membership.AUTO
            )
        self.assertEqual(child.subscription_set.count(), 1, 'actual is: %d' % child.subscription_set.count())
        category = child.subscription_set.all()[0].membership.description
        self.assertEqual(category, "Cadet", 'Actual is: %s' % category)
        subscription_activate(sub_15)
       
        subscription_renew(child.active_sub(), 2016, 5)
        sub_16 = child.subscription_set.all().filter(sub_year=2016)[0]
        self.assertEqual(sub_16.membership.description, 'Junior', 'Sub wrong: %s' % sub_16.membership.description)
        subscription_activate(sub_16)
        
        subscription_renew(child.active_sub(), 2025, 5)
        sub_25= child.subscription_set.all().filter(sub_year=2025)[0]
        self.assertEqual(sub_25.membership.description, 'Junior', 'Sub wrong: %s' % sub_25.membership.description)
        subscription_activate(sub_25)

        subscription_renew(child.active_sub(), 2026, 5)
        sub_26 = child.subscription_set.all().filter(sub_year=2026)[0]
        self.assertEqual(sub_26.membership.description, 'UNDER_26', 'Sub wrong: %s' % sub_26.membership.description)
        subscription_activate(sub_26)


        subscription_renew(child.active_sub(), 2033, 5)
        sub_33 = child.subscription_set.all().filter(sub_year=2033)[0]
        self.assertEqual(sub_33.membership.description, 'UNDER_26', 'Sub wrong: %s' % sub_33.membership.description)
        subscription_activate(sub_33)

        subscription_renew(child.active_sub(), 2034, 5)
        sub_34 = child.subscription_set.all().filter(sub_year=2034)[0]
        self.assertEqual(sub_34.membership.description, 'Full', 'Sub wrong: %s' % sub_34.membership.description)
        subscription_activate(sub_34)

    def test_sub_UNDER_26_age25(self):
        child = Person.objects.all().filter(last_name = "Child")[0]
        child.dob = date(1989,5,2)
        sub = subscription_create(
            person=child,
            sub_year=2015,
            membership_id=-1
        )
        self.assertEqual(child.subscription_set.count(), 1, 'actual is: %d' % child.subscription_set.count())
        category = child.subscription_set.all()[0].membership.description
        self.assertEqual(category, "UNDER_26", 'Actual is: %s' % category)

    def test_sub_UNDER_26_age26(self):
        child = Person.objects.all().filter(last_name = "Child")[0]
        child.dob = date(1989,5,1)
        sub = subscription_create(
            person=child,
            sub_year=2015,
            membership_id=-1
        )
        self.assertEqual(child.subscription_set.count(), 1, 'actual is: %d' % child.subscription_set.count())
        category = child.subscription_set.all()[0].membership.description
        self.assertEqual(category, "Full", 'Actual is: %s' % category)

    def test_activate_sub_and_current_sub(self):
        adult = Person.objects.all().filter(first_name = "First", last_name = "Adult")[0]
        sub1 = subscription_create(
            person=adult,
            sub_year=2014,
            membership_id=Membership.FULL
        )
        self.assertIsNone(adult.active_sub())
        subscription_activate(sub1)
        self.assertEqual(adult.active_sub(), sub1, "Sub 1 not activated")
        
        sub2 = subscription_create(
            person=adult,
            sub_year=2015,
            membership_id=Membership.FULL
        )
        subs = adult.subscription_set.order_by('sub_year')
        self.assertEqual(subs.count(), 2, 'actual is: %d' % subs.count())
        self.assertEqual(adult.active_sub().sub_year, 2014, "Sub 1 not activated")
        subscription_activate(sub2)
        self.assertEqual(adult.active_sub().sub_year, 2015, "Sub 2 not activated")
        self.assertFalse(subs[0].active, "Sub 1 not deactivated")      
       
    def test_generate_adult_annual_invoice_items(self):
        self.assertEqual(InvoiceItem.objects.all().count(), 0, 'actual is: %d' % InvoiceItem.objects.all().count())
        adult = Person.objects.all().filter(first_name = "First", last_name = "Adult")[0]
        sub = subscription_create(
            person=adult,
            sub_year=2015,
            membership_id=Membership.FULL
        )
        subscription_activate(sub)
        subscription_create_invoiceitems(sub, month=5)
        self.assertEqual(InvoiceItem.objects.all().count(), 1)
        item = InvoiceItem.objects.all()[0]
        self.assertTrue(item.description.find('Full membership') > -1, 'Wrong membership')
        self.assertTrue(item.description.find('1/5/2015 to 30/4/2016') > -1, 'Wrong sub')
        self.assertEqual(item.amount, 240, 'Wrong amount: {}'.format(item.amount))
        inv = invoice_create_from_items(adult)
        self.assertEqual(Invoice.objects.all().count(), 1, 'actual is: %d' % Invoice.objects.all().count())
        inv = Invoice.objects.all()[0]
        self.assertEqual(inv.total, 240, 'Wrong total: {}'.format(inv.total))
        self.assertEqual(inv.invoiceitem_set.count(), 1)
        # test cancellation whole invoice
        inv.cancel()
        inv = Invoice.objects.all()[0]
        self.assertEqual(inv.invoiceitem_set.count(), 0)
        cnote = CreditNote.objects.all()[0]
        self.assertEqual(cnote.amount, 240)
        item = InvoiceItem.objects.all()[0]
        self.assertEqual(item.invoice, None)

    def test_generate_adult_annual_invoice_items_6months(self):
        ''' new member for 6 months only, processed late '''
        adult = Person.objects.all().filter(first_name = "First", last_name = "Adult")[0]
        sub = subscription_create(
            person=adult,
            sub_year=2015,
            start_month= 8,
            end_month=1,
            membership_id=Membership.FULL,
            new_member=True
        )
        subscription_activate(sub)
        subscription_create_invoiceitems(sub,10)
        self.assertEqual(InvoiceItem.objects.all().count(), 2)
        item = InvoiceItem.objects.all()[0]
        self.assertTrue(item.description.find('Joining fee') > -1, 'Wrong : {}'.format(item.description))
        self.assertEqual(item.amount, 100 , 'Wrong amount: {}'.format(item.amount))
        item = InvoiceItem.objects.all()[1]
        self.assertTrue(item.description.find('Full membership') > -1, 'Wrong membership')
        self.assertTrue(item.description.find('1/8/2015 to 31/1/2016') > -1, 'Wrong sub')
        self.assertEqual(item.amount, 6 * 21 , 'Wrong amount: {}'.format(item.amount))
        inv = invoice_create_from_items(adult)
        self.assertEqual(Invoice.objects.all().count(), 1, 'actual is: %d' % Invoice.objects.all().count())
        inv = Invoice.objects.all()[0]
        self.assertEqual(inv.total, 6 * 21 + 100, 'Wrong total: {}'.format(inv.total))

    def test_generate_adult_monthly_invoices_item(self):
        self.assertEqual(InvoiceItem.objects.all().count(), 0, 'actual is: %d' % InvoiceItem.objects.all().count())
        adult = Person.objects.all().filter(first_name = "First", last_name = "Adult")[0]
        sub = subscription_create(
            person=adult,
            sub_year=2015,
            membership_id=Membership.FULL,
            period=Subscription.MONTHLY
        )
        subscription_activate(sub)
        subscription_create_invoiceitems(sub, 5)
        self.assertEqual(InvoiceItem.objects.all().count(), 1)
        item = InvoiceItem.objects.all()[0]
        self.assertTrue(item.description.find('Full membership') > -1, 'Wrong membership')
        self.assertEqual(item.amount, 21, 'Wrong amount: {}'.format(item.amount))
        # don't generate second item for same date
        subscription_create_invoiceitems(sub, 5)
        self.assertEqual(InvoiceItem.objects.all().count(), 1)
        # generate a second month
        subscription_create_invoiceitems(sub, 6)
        self.assertEqual(InvoiceItem.objects.all().count(), 2)
        # miss a month so bill should be 2 months
        subscription_create_invoiceitems(sub, 8)
        self.assertEqual(InvoiceItem.objects.all().count(), 3)
        item = InvoiceItem.objects.all()[2]
        self.assertTrue(item.description.find('1/7/2015 to 31/8/2015') > -1, 'Actual is: {}'.format(item.description))
        self.assertEqual(item.amount, 42, 'Wrong amount: {}'.format(item.amount))
        # now bill remaining 8 months
        subscription_create_invoiceitems(sub, 4)
        self.assertEqual(InvoiceItem.objects.all().count(), 4)
        item = InvoiceItem.objects.all()[3]
        self.assertTrue(item.description.find('1/9/2015 to 30/4/2016') > -1, 'Actual is: {}'.format(item.description))
        self.assertEqual(item.amount, 8 * 21, 'Wrong amount: {}'.format(item.amount))

    def test_generate_adult_quarterly_invoices_item(self):
        self.assertEqual(InvoiceItem.objects.all().count(), 0, 'actual is: %d' % InvoiceItem.objects.all().count())
        adult = Person.objects.all().filter(first_name = "First", last_name = "Adult")[0]
        sub = subscription_create(
            person=adult,
            sub_year=2015,
            membership_id=Membership.FULL,
            period=Subscription.QUARTERLY
        )
        subscription_activate(sub)
        subscription_create_invoiceitems(sub, 5)
        self.assertEqual(InvoiceItem.objects.all().count(), 1)
        item = InvoiceItem.objects.all()[0]
        self.assertTrue(item.description.find('Full membership') > -1, 'Wrong membership')
        self.assertTrue(item.description.find('1/5/2015 to 31/7/2015') > -1, 'Wrong sub')
        self.assertEqual(item.amount, 3 * 21, 'Wrong amount: {}'.format(item.amount))
        # don't generate anything for months 6 and 7
        subscription_create_invoiceitems(sub, 6)
        subscription_create_invoiceitems(sub, 7)
        self.assertEqual(InvoiceItem.objects.all().count(), 1)
        # miss a month so bill should be 2 months
        subscription_create_invoiceitems(sub, 8)
        self.assertEqual(InvoiceItem.objects.all().count(), 2)
        item = InvoiceItem.objects.all()[1]
        self.assertTrue(item.description.find('1/8/2015 to 31/10/2015') > -1, 'Actual is: {}'.format(item.description))
        self.assertEqual(item.amount, 3 * 21, 'Wrong amount: {}'.format(item.amount))
        # now bill remaining 8 months
        subscription_create_invoiceitems(sub, 11)
        subscription_create_invoiceitems(sub, 2)
        self.assertEqual(InvoiceItem.objects.all().count(), 4)
        item = InvoiceItem.objects.all()[3]
        self.assertTrue(item.description.find('1/2/2016 to 30/4/2016') > -1, 'Actual is: {}'.format(item.description))
        self.assertEqual(item.amount, 3 * 21, 'Wrong amount: {}'.format(item.amount))

    def test_invoice_paid_full(self):
        ''' Create family invoice. pay it and check invoice and payment are correct '''
        adult = Person.objects.all().filter(first_name = "First", last_name = "Adult")[0]
        wife = Person.objects.all().filter(first_name = "Wife of", last_name = "Adult")[0]
        junior = Person.objects.all().filter(first_name = "First", last_name = "Child")[0]
        cadet = Person.objects.all().filter(first_name = "Second", last_name = "Child")[0]      
        sub = subscription_create(
            person=adult,
            sub_year=2014,
            active=True,
            membership_id=Membership.FULL
            )
        sub = subscription_create(
            person=wife,
            sub_year=2014,
            active=True,
            membership_id=Membership.FULL
            )
        sub = subscription_create(
            person=junior,
            sub_year=2014,
            active=True,
            membership_id=Membership.JUNIOR
            )
        sub = subscription_create(
            person=cadet,
            sub_year=2014,
            active=True,
            membership_id=Membership.CADET
            )
        subscription_renew_batch(2015,5)
        self.assertEqual(Subscription.objects.all().count() ,8)
        bar = ItemType.objects.all().filter(id=ItemType.BAR)[0]
        item1 = InvoiceItem.objects.create(
            person=adult,
            item_type=bar,
            description='Test BAR',
            amount=100)
        invoice_create_from_items(junior)
        self.assertEqual(Invoice.objects.all().count(), 1)
        inv = Invoice.objects.all()[0]
        self.assertEqual(inv.person,adult)
        self.assertEqual(inv.state, Invoice.UNPAID)
        self.assertEqual(inv.invoiceitem_set.count(), 6)
        substotal = 240 + 240 + 75 + 35
        discount = substotal/10
        total = substotal - discount + 100
        self.assertEqual(inv.total, total)
        items = inv.invoiceitem_set.filter(paid=True).count()
        self.assertEqual(items, 0)
        # create a payment
        payment = Payment.objects.create(type=Payment.CHEQUE,
                                         person=adult,
                                         reference='test',
                                         amount=total,
                                         credited=0)
        self.assertEqual(payment.state, Payment.NOT_MATCHED)
        # pay the invoice
        invoice_pay(inv, payment)
        payment = Payment.objects.all()[0]
        self.assertEqual(payment.state, Payment.FULLY_MATCHED)    
        # check the invoice and items are paid
        inv = Invoice.objects.all()[0]
        self.assertEqual(inv.state, Invoice.PAID_IN_FULL)  
        items = inv.invoiceitem_set.filter(paid=True).count()
        self.assertEqual(items, 6)
      
    def test_group_create(self):
        # Group creation is unique
        group = group_get_or_create('test')
        count = Group.objects.all().count()
        self.assertEqual(count, 1)
        group2 = group_get_or_create('test')
        count = Group.objects.all().count()
        self.assertEqual(count , 1)
        # Add 1 person
        adult = Person.objects.all().filter(first_name = "First", last_name = "Adult")[0]
        adult.groups.add(group)
        self.assertEqual(group.person_set.all().count(), 1)
        # adding a second time does not increase group size
        adult.groups.add(group)
        self.assertEqual(group.person_set.all().count(), 1)
        # check person has a group
        self.assertEqual(adult.groups.count(), 1)
        # check person is in the group
        self.assertTrue(adult.groups.filter(slug='test').exists())
        # Add another person
        wife = Person.objects.all().filter(first_name = "Wife of", last_name = "Adult")[0]
        wife.groups.add(group)
        self.assertEqual(group.person_set.all().count(), 2)
        # remove the first person
        adult.groups.remove(group)
        self.assertFalse(adult.groups.filter(slug='test').exists())


        
    #def test_generate_adult_invoice_item_joining(self):
    #    self.assertEqual(InvoiceItem.objects.all().count(), 0, 'actual is: %d' % InvoiceItem.objects.all().count())
    #    adult = Person.objects.all().filter(last_name = "Adult")[0]
    #    sub = subscription_create(
    #        person=adult,
    #        sub_year=2015,
    #        membership_id=Membership.FULL
    #    )
    #    sub.new_member = True
    #    sub.generate_invoice_items()
    #    self.assertEqual(InvoiceItem.objects.all().count(), 2)
    #    item = InvoiceItem.objects.filter(item_type = ItemType.SUBSCRIPTION)[0]
    #    self.assertTrue(item.description.find('Full membership') > -1 'Wrong membership')
    #    self.assertTrue(item.description.find('Annual subscription 1/5/2015 to 30/4/2016') > -1, 'Wrong sub')
    #    self.assertEqual(item.amount, 240, 'Wrong amount')
    #    item = InvoiceItem.objects.filter(item_type = ItemType.JOINING)[0]
    #    self.assertEqual(item.description, 'Joining fee', 'Wrong joining record')
    #    self.assertEqual(item.amount, 100, 'Wrong joining amount')

    #def test_generate_junior_sub(self):
    #    junior = Person.objects.get(id=2)
    #    sub = junior.subscription_set.all()[0]
    #    sub.generate_invoice_items()
    #    item = InvoiceItem.objects.all()[0]
    #    self.assertTrue(item.description.find('Junior membership') > -1 'Wrong membership')
    #    self.assertTrue(item.description.find('Annual subscription 1/5/2015 to 30/4/2016') > -1, 'Wrong sub')
    #    self.assertEqual(item.amount, 75, 'Wrong amount')

    #def test_generate_partial_sub1(self):
    #    adult = Person.objects.get(id=1)
    #    sub = adult.subscription_set.all()[0]
    #    sub.start_date = datetime.date(2015, 11, 17)
    #    sub.save()
    #    sub.generate_invoice_items()
    #    self.assertEqual(InvoiceItem.objects.all().count(), 1)
    #    item = InvoiceItem.objects.all()[0]
    #    self.assertTrue(item.description.find('Annual subscription 17/11/2015 to 30/4/2016') > -1, 'Wrong sub')
    #    self.assertEqual(item.amount, 105, 'Wrong partial amount: {}'.format(item.amount))

    #def test_generate_partial_sub2(self):
    #    adult = Person.objects.get(id=1)
    #    sub = adult.subscription_set.all()[0]
    #    sub.start_date = datetime.date(2016, 01, 01)
    #    sub.end_date = datetime.date(2016, 03, 10)
    #    sub.save()
    #    sub.generate_invoice_items()
    #    self.assertEqual(InvoiceItem.objects.all().count(), 1)
    #    item = InvoiceItem.objects.all()[0]
    #    self.assertTrue(item.description.find('Annual subscription 1/1/2016 to 10/3/2016') > -1
    #                    'Wrong sub: {}'.format(item.description))
    #    self.assertEqual(item.amount, 3 * 21, 'Wrong partial amount: {}'.format(item.amount))

#class ViewTest(TestCase):
#    """Tests for the application views."""

#    if django.VERSION[:2] >= (1, 7):
#        # Django 1.7 requires an explicit setup() when running tests in PTVS
#        @classmethod
#        def setUpClass(cls):
#            django.setup()

#    def test_home(self):
#        """Tests the home page."""
#        response = self.client.get('/')
#        self.assertContains(response, 'Home Page')
#        self.assertContains(response, 'Home Page', 1, 200)

#    def test_contact(self):
#        """Tests the contact page."""
#        response = self.client.get('/contact')
#        self.assertContains(response, 'Contact', 3, 200)

#    def test_about(self):
#        """Tests the about page."""
#        response = self.client.get('/about')
#        self.assertContains(response, 'About', 3, 200)
