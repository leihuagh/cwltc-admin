from django.db import models
from django.core.signing import Signer
from django.conf import settings
import gocardless_pro
from members.models import Person, Invoice, Payment
from members.services import invoice_pay, invoice_unpay
from .models import Mandate, Payment_Event


def cardless_client():
    return gocardless_pro.Client(
        access_token=getattr(settings, 'CARDLESS_ACCESS_TOKEN'),
        environment=getattr(settings, 'CARDLESS_ENVIRONMENT')
    )

def active_mandate(person: Person):
    """
    Return the gc id of first active mandate linked to the person
    """
    mandates = person.Mandates.filter(active=True)
    if mandates:
        mandate = mandates[0]
        gc_mandate = cardless_client().mandates.get(mandate.mandate_id)
        if gc_mandate.status in ['active', 'submitted', 'pending_submission']:
            return gc_mandate
        else:
            mandate.active = False
            mandate.save()
            return None
    else:
        return None

def pay_invoice(invoice: Invoice, mandate_id: str):
    if invoice.state == Invoice.PAID_IN_FULL:
        raise ServicesError("Already paid in full")

    gc_payment = cardless_client().payments.create(
        params={
            'amount': invoice.total,
            'currency': 'GBP',
            'links': {
                'mandate': mandate_id
            },
            'metadata': {
                'invoice_id': invoice.id
            }
        }, headers={
            'Idempotency-Key': invoice.id
        }
    )
    payment = Payment(type=Payment.DIRECT_DEBIT,
                      person=invoice.person,
                      amount=invoice.total,
                      fee=fee,
                      membership_year=invoice.membership_year,
                      banked=True,
                      banked_date=date
                      )
    payment.save()
    invoice_pay(invoice, payment)


    invoice.state = Invoice.PENDING_GC


def process_payment_event(event):
    """
    https://developer.gocardless.com/api-reference/#events-payment-actions
    :return
    """
    payment = Payment.objects.filter(payment_id=event['links']['payment'])
    if not payment:
        return False

    # if event exists we have already processed this
    old_event = payment.events_set.filter(event_id=event['id'])
    if old_event:
        return False

    Payment_Event.objects.create(
        event_id=event['id'],
        action=event['action'],
        date=event['created_at'],
        payment=payment
    )

    # clear pending and banked flags, but not paid flag because we need to test if its been paid already
    payment.pending = False
    payment.banked = False

    action = event['action']
    if action == 'created' or action == 'customer_approval_granted' or action == 'submitted':
        payment.pending = True
        payment.paid = False

    elif action == 'customer_approval_denied':
        payment.paid = False

    elif action == 'confirmed':
        payment.pending = True
        if not payment.paid:
            payment.paid = True
            invoice_pay(payment.invoice, payment)

    elif action == 'cancelled':
        payment.delete()

    elif action == 'failed':
        payment.paid = False

    elif action == 'chargeback_cancelled':
        payment.pending = False
        if not payment.paid:
            payment.paid = True
            invoice_pay(payment.invoice, payment)
        payment.banked = True

    elif action == 'paid_out':
        payment.pending = False
        if not payment.paid:
            payment.paid = True
            invoice_pay(payment.invoice, payment)
        payment.banked = True

    elif action == 'charged_back' or action == 'late_failure_settled' or action == 'chargeback_settled':
        invoice_unpay(payment.invoice)
        payment.pending = False
        payment.paid = False
        payment.banked = False

    elif action == 'resubmission_requested':
        payment.pending = False
        payment.paid = False

    else:
        return False
    return True


def process_mandate_event(event):
    """
    https://developer.gocardless.com/api-reference/#events-mandate-actions
    """
    mandate = Mandate.objects.filter(mandate_id=event['links']['mandate'])
    action = event['action']

    if action == 'active' or action == 'reinstated':
        mandate.active = True
        mandate.save()

    elif action == 'failed' or action == 'expired':
        mandate.active = False
        mandate.save()

    elif action == 'cancelled' or action == 'transferred' or action == ' replaced':
        mandate.delete()


def detokenise(token, model_class):
    """ Decode an invoice or person token """
    id = Signer().unsign(token)
    try:
        return model_class.objects.get(pk=id)
    except model_class.DoesNotExist:
        return None


