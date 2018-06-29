from django.core.management.base import BaseCommand
from django.db.models import Sum
from pos.models import PosPayment, Transaction


class Command(BaseCommand):
    help = 'Check and possibly fix errors in Pos payments'

    def add_arguments(self, parser):
        parser.add_argument('--fix', help='Update payment from transaction')

    def handle(self, *args, **options):
        payments = PosPayment.objects.filter(transaction__billed=False,
                                             transaction__split=False).select_related('transaction')
        self.stdout.write('Checking non-split transactions')
        for pay in payments:
            if pay.amount != pay.transaction.total:
                self.stdout.write(self.style.ERROR(f'Payment Id: {pay.id} Amount: {pay.amount} '
                                                   f'Transaction id: {pay.transaction.id} {pay.transaction.total}'))
                if options['fix']:
                    pay.amount = pay.transaction.total
                    pay.save()
        self.stdout.write('Checking split transactions')
        splits = Transaction.objects.filter(billed=False, split=True)
        for split in splits:
            sum = PosPayment.objects.filter(transaction__id=split.id).aggregate(sum=Sum('amount'))['sum']
            if sum != split.total:
                self.stdout.write(self.style.ERROR(f'Payments total: {sum} '
                                                   f'Transaction id: {split.id} {split.total}'))
                if options['fix']:
                    diff = sum - split.total
                    pay1 = PosPayment.objects.filter(transaction__id=split.id)[0]
                    pay1.amount = pay1.amount - diff
                    pay1.save()


