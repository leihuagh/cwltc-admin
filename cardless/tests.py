import os
import unittest
from django.test import TestCase, RequestFactory, Client
from django.urls import reverse
from .views import RedirectFlowView
from .services import cardless_client
import gocardless_pro


class Cardless(TestCase):


    @classmethod
    def setUpTestData(cls):
        pass

    def setUp(self):
        self.factory = RequestFactory()
        self.client = cardless_client()


    def test_client_exists(self):
        self.assertNotEqual(self.client, None)

    def test_no_customers(self):
        customers = self.client.customers.list().records
        self.assertEqual(customers, [])

    def test_bad_redirect_flow(self):
        c = Client()
        response = c.get(reverse('cardless-redirect-flow'))
        # request = self.factory.get(reverse('cardless-redirect-flow'))
        # response = RedirectFlowView.as_view()(request)
        self.assertEqual(response.status_code, 400)

