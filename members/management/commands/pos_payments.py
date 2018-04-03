from django.core.management.base import BaseCommand

from pos.services import fix_tea_transactions


class Command(BaseCommand):
    help = 'Change type to Teas'


    def handle(self, *args, **options):
        fix_tea_transactions()

