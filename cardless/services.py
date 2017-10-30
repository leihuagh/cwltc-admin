import datetime
import logging
from django.core.signing import Signer
from django.conf import settings
import gocardless_pro
from members.models import Person, Invoice, Payment
from members.services import invoice_pay_by_gocardless, payment_update_state, invoice_update_state
from .models import Mandate, Payment_Event

logger = logging.getLogger(__name__)


def cardless_client():
    return gocardless_pro.Client(
        access_token=getattr(settings, 'CARDLESS_ACCESS_TOKEN'),
        environment=getattr(settings, 'CARDLESS_ENVIRONMENT')
    )


def webhook_secret():
    return getattr(settings, 'CARDLESS_WEBHOOK_SECRET')


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


def create_cardless_payment(invoice: Invoice, mandate: Mandate):
    """
    Create a cardless payment and an associated Payment object linked to the invoice
    """
    logger.debug('creating payment')
    existing_payments = invoice_payments_list(invoice)
    payment_number = len(existing_payments) + 1
    unpaid = invoice.unpaid_amount
    amount = str(int(unpaid * 100))
    if invoice.state == Invoice.STATE.PAID.value:
        return False, "Already paid in full"

    try:
        gc_payment = cardless_client().payments.create(
            params={
                'amount': str(amount),
                'currency': 'GBP',
                'links': {
                    'mandate': mandate.mandate_id
                },
                'metadata': {
                    'invoice_id': str(invoice.id),
                    'description': Payment.SINGLE_PAYMENT  # identifies not from legacy api
                }
            }, headers={
                'Idempotency-Key': str(invoice.id) + "/" + str(payment_number)
            }
        )
    except Exception as e:
        return False, "Exception from GoCardless {0}".format(e)

    # Check that we have not already got this payment id attached to the invoice
    # It should not happen if all is working properly
    for payment in existing_payments:
        if payment.cardless_id == gc_payment.id:
            return False, "Payment already processed"

    invoice_pay_by_gocardless(invoice, amount, gc_payment.id, payment_number)
    return True, ""


def process_payment_event(event):
    """
    https://developer.gocardless.com/api-reference/#events-payment-actions
    """
    try:
        payment = Payment.objects.get(cardless_id=event['links']['payment'])
    except Payment.DoesNotExist:
        return False

    # if event exists we have already processed this
    old_event = payment.events.filter(event_id=event['id'])
    if old_event:
        return False
    Payment_Event.objects.create(
        event_id=event['id'],
        action=event['action'],
        created_at=event['created_at'],
        payment=payment
    )
    payment.banked = False
    action = event['action']
    if action in ('created', 'customer_approval_granted', 'submitted', 'resubmission_requested'):
        payment.state = Payment.STATE.PENDING.value
    elif action == 'confirmed':
        payment.state = Payment.STATE.CONFIRMED.value
    elif action in ('cancelled', 'failed', 'customer_approval_denied',
                    'charged_back', 'late_failure_settled', 'chargeback_settled'):
        payment.state = Payment.STATE.FAILED.value
    elif action in ('paid_out', 'chargeback_cancelled'):
        payment.state = Payment.STATE.CONFIRMED.value
        payment.banked = True
        if not payment.banked_date:
            payment.banked_date = datetime.datetime.now()
    else:
        return False
    payment.save()
    invoice_update_state(payment.invoice)
    return True


def process_mandate_event(event):
    """
    https://developer.gocardless.com/api-reference/#events-mandate-actions
    """
    try:
        mandate = Mandate.objects.get(mandate_id=event['links']['mandate'])
    except Mandate.DoesNotExist:
        logger.warning('Webhook for mandate that does not exist: {}'.format(event))
        return False

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
            try:
                gc_payment = cardless_client().payments.get(payment.cardless_id)
                payment.charge_date = gc_payment.charge_date
                payment.status = gc_payment.status
                # payment.state should be correct due to web hooks, but update it to be sure
                payment_update_state(payment, gc_payment.status)
            except Exception:
                logger.warning("Payment {} for invoice {} not found in GoCardless".format(
                    payment.cardless_id, payment.invoice.id)
                )
        include = include or (paid and payment.state == Payment.STATE.CONFIRMED)
        include = include or (pending and payment.state == Payment.STATE.PENDING)
        include = include or (not paid and not pending)
        if include:
            result.append(payment)
    return result


def detokenise(token, model_class):
    """ Decode an invoice or person token """
    pk = Signer().unsign(token)
    try:
        return model_class.objects.get(pk=pk)
    except model_class.DoesNotExist:
        return None


