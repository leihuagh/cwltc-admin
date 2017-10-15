
from django.urls import reverse
from django.conf import settings
import gocardless_pro
from members.models import Person, Invoice, Payment
from .models import Mandate


def cardless_client():
    return gocardless_pro.Client(
        access_token=getattr(settings, 'CARDLESS_ACCESS_TOKEN'),
        environment=getattr(settings, 'CARDLESS_ENVIRONMENT')
    )


def pay_invoice(invoice):
    person=invoice.person
    mandate=person.mandate_set[0]
    gc_payment = cardless_client().payments.create(
        params={
            'amount': invoice.total,
            'currency': 'GBP',
            'links': {
                'mandate': mandate.mandate_id
            },
            'metadata': {
                'invoice_id': invoice.id
            }
        }, headers={
            'Idempotency-Key': invoice.id
        }
    )
    invoice.state = Invoice.PENDING_GC