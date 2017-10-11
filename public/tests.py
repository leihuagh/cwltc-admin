import django
from django.test import TestCase
from members.models import Settings

# TODO: Configure your database in settings.py and sync before running tests.

class SimpleTest(TestCase):
    """Tests for the application views."""

    # Django requires an explicit setup() when running tests in PTVS
    @classmethod
    def setUpClass(cls):
        super(SimpleTest, cls).setUpClass()


    def test_basic_addition(self):
        """
        Tests that 1 + 1 always equals 2.
        """
        self.assertEqual(1 + 1, 2)
