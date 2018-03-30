from django.core.management.base import BaseCommand, CommandError
from members.models import Person
from pos.models import Transaction, PosPayment


class Command(BaseCommand):
    help = 'Create a payment record for old POS transactions'

    def handle(self, *args, **options):


        trans = Transaction.objects.filter(billed=False).exclude(person__isnull=True)
        count_before = PosPayment.objects.count()
        count_created = 0
        count_paid = 0
        count_after = 0
        for tran in trans:
            payment = PosPayment.objects.filter(transaction_id=tran.id)
            if payment:
                count_paid += 1
            else:
                count_created += 1
            # if tran.pospayment_set.count() == 0:
            #     count1 += 1
                p = PosPayment(transaction=tran, person_id=tran.person_id, amount=tran.total, billed=False)
                #p.save()
        countAfter = PosPayment.objects.count()
        self.stdout.write(self.style.SUCCESS(f'''
        Pos payments: Before: {count_before}, Paid, {count_paid}, Created: {count_created}, After: {count_after}'''))

