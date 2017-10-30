from django.core.management.base import BaseCommand, CommandError
from members.models import Invoice, Payment

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
                payment.state = payment.STATE.CONFIRMED
                payment.banked_date = payment.creation_date
                payment.save()
                paid += 1
            # elif invoice.state == Invoice.STATE.UNPAID:
            #     fee = invoice.total/100
            #     if fee > 2:
            #         fee = 2
            #     payment = Payment.objects.create(
            #         membership_year=invoice.membership_year,
            #         type=Payment.DIRECT_DEBIT,
            #         person=invoice.person,
            #         amount=invoice.total,
            #         credited=invoice.total,
            #         fee=fee,
            #         invoice=invoice,
            #         state=Payment.STATE.PENDING ,
            #         cardless_id=invoice.gocardless_bill_id
            #     )
            #     created += 1
            else:
                others += str(invoice.id) + " "

        print("{} payments processed, {} payments created".format(paid, created))
        if others:
            print ("Other invoices: " + others)
