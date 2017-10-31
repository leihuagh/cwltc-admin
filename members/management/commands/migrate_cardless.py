from django.core.management.base import BaseCommand
from members.models import Invoice
from cardless.services import get_payment, update_payment


class Command(BaseCommand):
    help = 'Migrate cardless id from invoice into payment'

    def handle(self, *args, **options):

        invoices = Invoice.objects.filter(gocardless_bill_id__startswith = "PM" )
        print("Found {} invoices to process".format(invoices.count()))
        paid = 0
        created = 0
        others = ""
        for invoice in invoices:
            if invoice.state == Invoice.STATE.PAID:
                payment = invoice.payment_set.all()[0]
                payment.state = payment.STATE.CONFIRMED
                payment.cardless_id = invoice.gocardless_bill_id
                payment.save()
                # gc_payment = get_payment(payment.cardless_id)
                # update_payment(payment, gc_payment)
                paid += 1
            else:
                others += str(invoice.id) + " "

        print("{} payments processed, {} payments created".format(paid, created))
        if others:
            print("Other invoices: " + others)
