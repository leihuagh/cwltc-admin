import csv
import io
import logging
from decimal import Decimal
from datetime import date, datetime, timedelta
from members.services import payment_update_state, invoice_pay_by_gocardless, payment_state, ServicesError
from members.models import Invoice
from .services import cardless_client, payments_list, unpack_date, get_payout, update_payment

logger = logging.getLogger(__name__)


def process_recent_payments(days):
    start_date = datetime.now() - timedelta(days=days)
    gc_payments = payments_list(start_date)
    return process_payments_list(gc_payments)


def process_payments_list(gc_payments):
    '''
    Process a list of payments
    Update the invoices and payments in the database
    '''
    updated_invoices = []
    invoice_not_founds = []
    payments_created = []
    for gc_payment in gc_payments:
        description = gc_payment.metadata.get('description', None)
        invoice_id = gc_payment.metadata.get('invoice_id', None)
        if description and "/" in description:
            # legacy api data
            meta = description.split(':')
            ids = meta[1].split('/')
            invoice_id = ids[1].strip()
        if invoice_id:
            try:
                invoice = Invoice.objects.get(pk=invoice_id)
                # if payment exists, update it
                for payment in invoice.payment_set.all():
                    if payment.cardless_id == gc_payment.id:
                        if update_payment(payment, gc_payment):
                            updated_invoices.append(invoice.id)
                            break
                else:
                    # This will only happen if we create a manual payment on Go Cardless
                    # when there will not be a payment record
                    # create a new payment
                    new_state, banked = payment_state(gc_payment.status)
                    payout_date = None
                    if banked:
                        try:
                            payout = get_payout(gc_payment.links['payout'])
                            payout_date = unpack_date(payout.arrival_date)
                        except Exception:
                            logger.warning("Could not get payout date creating payment for invoice {0}".format(invoice.id))
                    payment_number = invoice.payment_set.count() + 1
                    try:
                        invoice_pay_by_gocardless(invoice,
                                                  Decimal(gc_payment.amount)/100,
                                                  gc_payment.id,
                                                  payment_number,
                                                  state=new_state,
                                                  banked=banked,
                                                  banked_date=payout_date
                                                  )
                        payments_created.append(invoice.id)
                    except ServicesError as err:
                        logger.warning(err.message + 'processing invoice {}'.format(invoice.id))
            except Invoice.DoesNotExist:
                invoice_not_founds.append(invoice_id)
        else:
            logger.warning("Bad metadata {} processing payment ".format(gc_payment.id))
    return updated_invoices, invoice_not_founds, payments_created


def process_csvfile(f):
    '''
    Read a GoCardless export and update all invoices that are now paid out
    '''
    decoded_file = f.read().decode('utf-8')
    io_string = io.StringIO(decoded_file)
    reader = csv.DictReader(io_string)
    record_count = 0
    paid_count = 0
    no_meta_count = 0
    invoice_not_founds = []
    payments_created = []
    errors = ""
    result = ""
    try:
        for row in reader:
            gc_payment_id = row['id']
            status= row['status']
            amount = Decimal(row['amount'])
            fee = Decimal(row['transaction_fee'])
            payout_date = unpack_date(row['payout_date'])
            record_count += 1
            if len(row['metadata.description']) > 0:
                if "/" in row['metadata.description']:
                    # legacy api data
                    meta = row['metadata.description'].split(':')
                    ids = meta[1].split('/')
                    invoice_id = ids[1].strip()
                else:
                    # this is the pro api
                    invoice_id = row['metadata.invoice_id']
                try:
                    invoice = Invoice.objects.get(pk=invoice_id)
                    # if payment exists, update it
                    for payment in invoice.payment_set.all():
                        if payment.cardless_id == gc_payment_id:
                            updated = payment_update_state(payment, status)
                            if updated:
                                paid_count += 1
                            break
                    else:
                        # create a new payment to match the cardless payment
                        state, banked = payment_state(status)
                        if not banked:
                            payout_date = None
                        payment_number = invoice.payment_set.count() + 1
                        invoice_pay_by_gocardless(invoice,
                                                  amount,
                                                  gc_payment_id,
                                                  payment_number,
                                                  state=state,
                                                  banked=banked,
                                                  banked_date=payout_date
                                                  )
                        payments_created.append(invoice.id)
                except Invoice.DoesNotExist:
                    invoice_not_founds.append(invoice_id)
            else:
                no_meta_count += 1
        result = "{} records processed and {} invoices changed to paid state. {} with no meta data. ".format(
            record_count, paid_count, no_meta_count)
        if len(invoice_not_founds) > 0:
            errors = "Not found invoice ids: " + ",".join(map(str, invoice_not_founds))
        if len(payments_created) > 0:
            errors += " Payments created for invoices: " + ",".join(map(str, payments_created))
    except KeyError:
        errors = "Invalid file format"
    return [result, errors]


