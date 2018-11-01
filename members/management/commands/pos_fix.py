from django.core.management.base import BaseCommand
from pos.models import PosPayment, Transaction


class Command(BaseCommand):
    help = 'Add payment record for manually entered transactions that did not have them'

    def add_arguments(self, parser):
        parser.add_argument('--fix', help='Update payment from transaction')

    def handle(self, *args, **options):
        ids = PosPayment.objects.all().values_list('transaction_id', flat=True)
        bad_trans = Transaction.objects.filter(attended=True, billed=0).exclude(id__in=ids)
        for trans in bad_trans:
            self.stdout.write(f'{trans.id}, {trans.creation_date}')
        good = Transaction.objects.filter(id__in=ids).count()
        self.stdout.write(f'Found {len(bad_trans)} transactions without PosPayment and {good} with PosPayment')
        if options['fix']:
            for trans in bad_trans:
                pos_payment = PosPayment(
                    transaction=trans,
                    person=trans.person,
                    billed=False,
                    total=trans.total
                )
                pos_payment.save()
