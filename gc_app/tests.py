from datetime import date, datetime
import pdb
import django
from django.test import SimpleTestCase
import factory
from gc_app.views import unpack_date, unpack_datetime
from members.models import Settings


class SettingsFactory(factory.DjangoModelFactory):
    class Meta:
        model = Settings
    id = 1
    membership_year = 2015

class dates(SimpleTestCase):
    
    @classmethod
    def setUpTestData(cls):
        pdb.set_trace()
        settings = SettingsFactory.create()
    
    def testSettings(self):
        year = Settings.current()
        self.assertEqual(year, 2015)

    def testDate1(self):
        s = '2016-01-31'
        d = unpack_date(s)
        self.assertEqual(date(2016, 1, 31), d)

    def testDate2(self):
        s = '31/01/2016'
        d = unpack_date(s)
        self.assertEqual(date(2016, 1, 31), d)

    def testDate3(self):
        s = '31/1/2016 10:12:14'
        d = unpack_datetime(s)
        self.assertEqual(datetime(2016, 1, 31, 10, 12, 14), d)

    def testDate4(self):
        s = '2016-01-31 10:12:14'
        d = unpack_datetime(s)
        self.assertEqual(datetime(2016, 1, 31, 10, 12, 14), d)
