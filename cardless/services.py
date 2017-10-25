from decimal import Decimal
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
    Return the first valid mandate linked to the person
    """
    for mandate in person.mandates.all():
        try:
            gc_mandate = cardless_client().mandates.get(mandate.mandate_id)
        except Exception:
            continue
        if gc_mandate.status in ['pending_customer_approval', 'active', 'submitted', 'pending_submission']:
            return mandate
    return None


def calculate_fee(amount):
    fee = amount / 100
    if fee > 2:
        fee = 2
    return fee


def create_cardless_payment(invoice: Invoice, mandate: Mandate):
    """
    Create a cardless payment and an associated Payment object linked to the invoice
    """
    unpaid = invoice.unpaid_amount
    fee = calculate_fee(unpaid)
    amount = str(int(unpaid * 100))
    if invoice.state == Invoice.STATE.PAID.value:
        return
    gc_payment = cardless_client().payments.create(
        params={
            'amount': str(amount),
            'currency': 'GBP',
            'links': {
                'mandate': mandate.mandate_id
            },
            'metadata': {
                'invoice_id': str(invoice.id)
            }
        }, headers={
            'Idempotency-Key': str(invoice.id)
        }
    )
    # Check that we have not already got this payment attached to the invoice
    # It should not happen if all is working properly
    for payment in invoice_payments_list(invoice):
        if payment.cardless_id == gc_payment.id:
            return False
    payment = Payment(type=Payment.DIRECT_DEBIT,
                      person=invoice.person,
                      amount=unpaid,
                      fee=fee,
                      membership_year=invoice.membership_year,
                      cardless_id=gc_payment.id
                      )
    invoice.add_payment(payment)
    return True


def process_payment_event(event):
    """
    https://developer.gocardless.com/api-reference/#events-payment-actions
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

    payment.banked = False
    action = event['action']
    if action in ('created', 'customer_approval_granted', 'submitted', 'resubmission_requested'):
        payment.state = Payment.STATE.PENDING.value
    elif action == 'confirmed':
        payment.state = Payment.STATE.PAID.value
    elif action in ('cancelled', 'failed', 'customer_approval_denied',
                    'charged_back', 'late_failure_settled', 'chargeback_settled'):
        payment.state = Payment.STATE.FAILED.value
    elif action in ('paid_out', 'chargeback_cancelled'):
        payment.state = Payment.STATE.PAID.value
        payment.banked = True
    else:
        return False
    payment.invoice.update_state()
    return True


def payment_update_state(payment, gc_status):
    """ Update the payment state from the corresponding go cardless status """
    payment.banked = False
    if gc_status in ('pending_approval_granted', 'pending_submission', 'submitted'):
        payment.state = Payment.STATE.PENDING.value
    elif gc_status == 'confirmed':
        payment.state = Payment.STATE.PAID.value
    elif gc_status in ('cancelled', 'failed', 'customer_approval_denied', 'charged_back'):
        payment.state = Payment.STATE.FAILED.value
    elif gc_status == 'paid_out':
        payment.state = Payment.STATE.PAID.value
        payment.banked = True
    else:
        return False
    payment.save()
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


def invoice_payments_list(invoice: Invoice, pending=False, paid=False):
    """
    Return an updated list of payments attached to an invoice
    optionally select only pending go cardless invoices
    """
    result = []
    payments = invoice.payment_set.all().order_by('creation_date')
    for payment in payments:
        include = False
        if payment.cardless_id:
            gc_payment = cardless_client().payments.get(payment.cardless_id)
            payment.charge_date = gc_payment.charge_date
            payment.status = gc_payment.status
            # payment.state should be correct due to web hooks, but update it to be sure
            payment_update_state(payment, gc_payment.status)
        include = include or (paid and payment.state == Payment.STATE.PAID.value)
        include = include or (pending and payment.state == Payment.STATE.PENDING)
        include = include or (not paid and not pending)
        if include:
            result.append(payment)
    return result


def payment_status_is_pending(status):
    return status in ['pending_customer_approval', 'pending_submission', 'submitted']


def detokenise(token, model_class):
    """ Decode an invoice or person token """
    pk = Signer().unsign(token)
    try:
        return model_class.objects.get(pk=pk)
    except model_class.DoesNotExist:
        return None
