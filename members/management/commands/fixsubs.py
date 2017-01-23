from django.core.management.base import BaseCommand, CommandError
from members.models import Subscription, Person, InvoiceItem, Membership

class Command(BaseCommand):
    help = 'Update sub in Person to be the active subscription'

    def handle(self, *args, **options):
       # import pdb; pdb.set_trace()

        # make person.sub the active sub
        # set life members as paid sub
        subs = Subscription.objects.filter(active=True, sub_year=2016).select_related()
        count = 0
        count1 = 0
        count2 = 1
        for sub in subs:
            sub.person_member.sub = sub
            if sub.membership.id == Membership.RESIGNED:
                sub.person_member.state = Person.RESIGNED
                count2 += 1
            sub.person_member.save()
            count += 1
            if sub.membership.id == Membership.LIFE or sub.membership.id == Membership.HON_LIFE:
                sub.paid = True
                sub.save()
                count1 += 1
        self.stdout.write(self.style.SUCCESS('Processed %d subs' % count))
        self.stdout.write(self.style.SUCCESS('%d life subs' % count1))
        self.stdout.write(self.style.SUCCESS('%d resigned' % count2))

        # Mark all subs with paid invoice as paid
        items = InvoiceItem.objects.filter(paid=True, subscription__isnull=False)
        count = 0
        for item in items:
            item.subscription.paid = True
            item.subscription.save()
            count += 1
        self.stdout.write(self.style.SUCCESS('Processed %d invoice items' % count))

        # Update flags in membership
        memberships = Membership.objects.all()
        count = 0 
        for mem in memberships:
            mem.is_adult = True
            if mem.id in Membership.JUNIORS_LIST:
                mem.is_adult=False
                mem.is_playing=True
                if mem.id == Membership.CADET:
                    mem.cutoff_age = 8
                elif mem.id == Membership.JUNIOR:
                    mem.cutoff_age = 18
            elif mem.id == Membership.UNDER_26:
                 mem.cutoff_age = 26
                 mem.is_playing=True
            else:
                mem.is_playing = False
                if mem.id in Membership.PLAYING_LIST:
                    mem.is_playing = True
            mem.save()
            count += 1
        self.stdout.write(self.style.SUCCESS('Processed %d memberships' % count))