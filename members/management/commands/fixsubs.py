from django.core.management.base import BaseCommand
from members.models import Subscription, Person, Settings


class Command(BaseCommand):
    help = 'Update person.sub to be the 2018 active subscription'

    def handle(self, *args, **options):

        # make person.sub the latest active sub
        # set life members as paid sub
        year = Settings.current_year()
        subs = Subscription.objects.filter(sub_year=year, active=True)
        count = 0
        for sub in subs:

            person = Person.objects.filter(pk=sub.person_member_id).select_related('sub')[0]
            subs1 = Subscription.objects.filter(person_member_id=person.id, sub_year=year, active=True)
            if len(subs1) != 1:
                self.stdout.write(f'Subs count {len(subs1)} for Person: {person.id}')
                if person.id == 21277:
                    self.stdout.write(f'Fixing {person.id}')
                    person.sub = None
                    person.save()
                    for s in subs1:
                        if s.active:
                            s.delete()
                        else:
                            s.active = True
                            s.save()
                            person.sub = s
                            person.save()
                else:
                    self.stdout.write(f'Problem with {person.id}')
            else:
                if person.sub != sub:
                    count += 1
                    person.sub_id = sub.id
                    person.save()

        self.stdout.write(self.style.SUCCESS(f'Update {count} records from {len(subs)}'))
