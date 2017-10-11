import os
from django.conf import settings
from django.test import TestCase
import gocardless_pro


class Cardless(TestCase):

    @classmethod
    def setUpTestData(cls):
        pass

    def get_client(self):
        self.client = gocardless_pro.Client(
            access_token=getattr(settings, 'CARDLESS_ACCESS_TOKEN'),
            environment=getattr(settings, 'CARDLESS_ENVIRONMENT')
        )
        return self.client


    def test_client_not_none(self):
        self.get_client()
        self.assertNotEqual(self.client, None)








