import csv
import io
from decimal import Decimal
from datetime import date, datetime
from members.services import payment_update_state, invoice_pay_by_gocardless, payment_state
from members.models import Invoice

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
                            if payment_update_state(payment, status):
                                paid_count += 1
                            break
                    else:
                        # create a new payment
                        state, banked = payment_state(status)
                        if not banked:
                            payout_date = None
                        payment_number = 1
                        invoice_pay_by_gocardless(invoice,
                                                  amount,
                                                  gc_payment_id,
                                                  payment_number,
                                                  banked,
                                                  payout_date
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


def unpack_date_helper(date_string):
    '''
    Unpack a date string separated by - or / into parts
    original gocardless file uses yyyy-mm-dd
    If its been through Excel it will be dd/mm/yyyy
    always return list [yyyy, mm, dd]
    '''
    date_parts = date_string.split('-')
    if len(date_parts) == 3:
        return date_parts
    date_parts = date_string.split('/')
    if len(date_parts) == 3:
        return [date_parts[2], date_parts[1], date_parts[0]]
    raise ValueError("Cannot parse date", date_string)


def unpack_date(date_string):
    '''
    Unpack a date string separated by - or / to a date
    '''
    date_parts = unpack_date_helper(date_string)
    return  date(int(date_parts[0]), int(date_parts[1]), int(date_parts[2]))


def unpack_datetime(datetime_string):
    '''
    Unpack a datetime string separated by - or / to a datetime
    '''
    parts = datetime_string.split(' ')
    if len(parts) == 2:
        date_parts = unpack_date_helper(parts[0])
        time_parts = parts[1].split(':')
        if len(time_parts) == 3:
            return datetime(int(date_parts[0]), int(date_parts[1]), int(date_parts[2]),
                            int(time_parts[0]), int(time_parts[1]), int(time_parts[2]))
    raise ValueError("Cannot parse time from ", datetime_string)