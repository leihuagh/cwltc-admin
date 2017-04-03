from django.core.management.base import BaseCommand, CommandError
from members.models import Subscription, Person, InvoiceItem, Membership

class Command(BaseCommand):
    help = 'Update sub in Person to be the active subscription'

    def handle(self, *args, **options):
       # import pdb; pdb.set_trace()

        # make person.sub the active sub
        # set life members as paid sub
    
        subs = Subscription.objects.filter(membership_id = Membership.RESIGNED, resigned=False).update(resigned=True)
        self.stdout.write(self.style.SUCCESS('Processed %d resigned subs' % subs))

        people = Person.objects.filter(sub__membership_id = Membership.RESIGNED)
        self.stdout.write(self.style.SUCCESS('Processed %d resigned subs' % len(people)))