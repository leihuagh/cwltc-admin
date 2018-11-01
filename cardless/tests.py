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
