import os
import unittest
from django.conf import settings
from django.test import TestCase
from .views import redirect_flow
import gocardless_pro


class Cardless(unittest.TestCase):


    @classmethod
    def setUpTestData(cls):
        pass


    def get_client(self):
        self.client = gocardless_pro.Client(
            access_token=getattr(settings, 'CARDLESS_ACCESS_TOKEN'),
            environment=getattr(settings, 'CARDLESS_ENVIRONMENT')
        )
        return self.client


    def test_customers(self):
        client = self.get_client()
        self.assertNotEqual(client, None)
        customers = client.customers.list().records
        self.assertEqual(customers, [])


    def test_redirect_flow(self):
        client = self.get_client()
        flow = redirect_flow()
        self.assertNotEqual(flow.id, None)
        self.assertNotEqual(flow.redirect_url, None)
