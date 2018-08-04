from operator import itemgetter
from django.db import models
from django.db.models import Q
from taggit.managers import TaggableManager
from members.models import ItemType, Person, ModelEnum, Membership, Settings
from members.services import BillingData


class Tournament(models.Model):
    """ A tournament is a collection of events """
    name = models.CharField(max_length=50, blank=True)
    description = models.CharField(max_length=1000, blank=True)
    draw_date = models.DateField(blank=False, null=False)
    finals_date = models.DateField(blank=False, null=False)
    event_cost = models.DecimalField(max_digits=5, decimal_places=2, null=False)

    @property
    def billed(self):
        """ True if no associated unbilled events"""
        return self.event_set.filter(billed=False).count() == 0

    def event_count(self, active=True):
        """ True if any linked event is active"""
        return self.event_set.filter(active=active).count()


    def make_active(self, state=True):
        """ Make tournament inactive - makes all linked events inactive too """
        for event in self.event_set.all():
            if state:
                event.active = not event.billed
            else:
                event.active = False
            event.save()

    def generate_bills(self):
        count = 0
        if not self.active:
            for event in self.event_set.filter(billed=False):
                data = event.billing_data()
                if data:
                    count += data.process()
        return count

    def add_standard_events(self):
        Event.objects.create(name="Men's Singles", event_type=EventType.MENS_SINGLES, cost=self.event_cost,
                             item_type_id=ItemType.TOURNAMENT, tournament=self)
        Event.objects.create(name="Ladies' Singles", event_type=EventType.LADIES_SINGLES, cost=self.event_cost,
                             item_type_id=ItemType.TOURNAMENT, tournament=self)
        Event.objects.create(name="Men's Doubles", event_type=EventType.MENS_DOUBLES, cost=self.event_cost,
                             item_type_id=ItemType.TOURNAMENT, tournament=self)
        Event.objects.create(name="Ladies' Doubles", event_type=EventType.LADIES_DOUBLES, cost=self.event_cost,
                             item_type_id=ItemType.TOURNAMENT, tournament=self)
        Event.objects.create(name="Mixed Doubles", event_type=EventType.MIXED_DOUBLES, cost=self.event_cost,
                             item_type_id=ItemType.TOURNAMENT, tournament=self)
        Event.objects.create(name="Men's Plate", event_type=EventType.MENS_DOUBLES, cost=0,
                             item_type_id=ItemType.TOURNAMENT, tournament=self, active=False, online_entry=False)
        Event.objects.create(name="Ladies' Plate", event_type=EventType.LADIES_DOUBLES, cost=0,
                             item_type_id=ItemType.TOURNAMENT, tournament=self, active=False, online_entry=False)
        Event.objects.create(name="Mixed Plate", event_type=EventType.MIXED_DOUBLES, cost=0,
                             item_type_id=ItemType.TOURNAMENT, tournament=self, active=False, online_entry=False)

    def players_list(self, for_choice_field=False):
        """ Returns a list of tuples containing player's fullname and id """
        parts = Participant.objects.filter(event__tournament_id=self.id).select_related('person', 'partner', 'person__address', 'partner__address')
        people_set = set()
        for record in parts:
            if for_choice_field:
                people_set.add((record.person.id, record.person.fullname,))
            else:
                people_set.add((record.person.id, record.person.fullname, record.person.mobile_phone, record.person.email, record.person.address.home_phone))
            if record.partner:
                if for_choice_field:
                    people_set.add((record.partner.id, record.partner.fullname,))
                else:
                    people_set.add((record.partner.id, record.partner.fullname, record.partner.mobile_phone, record.partner.email, record.partner.address.home_phone))
        people_list = list(people_set)
        people_list.sort(key=itemgetter(1))
        if for_choice_field:
            people_list.insert(0, (None, "-----"))
        return people_list


class EventType(ModelEnum):
    MENS_SINGLES = 0
    LADIES_SINGLES = 1
    MENS_DOUBLES = 2
    LADIES_DOUBLES = 3
    MIXED_DOUBLES = 4
    OPEN_SINGLES = 5
    OPEN_DOUBLES = 6


class Event(models.Model):
    """ Events can be social or other events. A tournament event is a special case """
       
    name = models.CharField(max_length=50, blank=False)
    description = models.CharField(max_length=1000, blank=True)
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    cost = models.DecimalField(max_digits=5, decimal_places=2, null=False)
    item_type = models.ForeignKey(ItemType, on_delete=models.CASCADE, null=True, blank=True)
    active = models.BooleanField(default=True)
    online_entry = models.BooleanField(default=True)
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE, null=True, blank=True)
    event_type = models.SmallIntegerField(choices=EventType.choices(), default=0)
    billed = models.BooleanField(default=False)

    def __str__(self):
        return self.name

    def add_person(self, person, partner=None, text=""):
        Participant.objects.create(event=self, person=person, partner=partner, text=text)

    def with_partner(self):
        """ True if event must have a partner """
        return self.event_type in (EventType.MENS_DOUBLES,
                                   EventType.LADIES_DOUBLES,
                                   EventType.MIXED_DOUBLES,
                                   EventType.OPEN_DOUBLES)
    
    def validate_entrants(self, person, partner, skip_eligibility=False):
        """
        Check that gender of person and partner(if any) is correct
        Return None if OK else return an error message
        Note some of the checks are redundant because gender checks are now handled when setting up the context
        """
        err_male = 'Entrant must be male'
        err_female = 'Entrant must be female'
        err_partner_male = 'Your partner must be male'
        err_partner_female = 'Your partner must be female'
        err_no_partner = 'You must specify a partner'
        err_same = 'You cannot partner yourself!'
        err_invalid = 'You are not eligible to enter'
        err_young = f'You must be {Membership.REGISTRATION_AGE} or over'
        err_invalid_partner = 'Selected partner is not eligible'
        err_young_partner = f'Partner must be {Membership.REGISTRATION_AGE} or over'

        if not skip_eligibility:
            if not Event.eligible(person):
                return err_invalid
            if partner:
                if not Event.eligible(partner):
                    return err_invalid_partner
                if person == partner:
                    return err_same

        if self.event_type == EventType.MENS_SINGLES.value:
            if person.gender != 'M':
                return err_male
        elif self.event_type == EventType.LADIES_SINGLES:
            if person.gender != 'F':
                return err_female
        elif self.event_type == EventType.MENS_DOUBLES.value:
            if person.gender != 'M':
                return err_male
            if partner:
                if partner.gender != 'M':
                    return err_partner_male
            else:
                return err_no_partner
        elif self.event_type == EventType.LADIES_DOUBLES.value:
            if person.gender != 'F':
                return err_female
            if partner:
                if partner.gender != 'F':
                    return err_female
            else:
                return err_no_partner
        elif self.event_type == EventType.MIXED_DOUBLES.value:
            if partner:
                if person.gender == 'F':
                    if partner.gender != 'M':
                        return err_partner_male
                else:
                    if partner.gender != 'F':
                        return err_partner_female
            else:
                return err_no_partner
        elif self.event_type == EventType.OPEN_SINGLES.value:
            pass
        elif self.event_type == EventType.OPEN_DOUBLES.value:
            if not partner:
                return err_no_partner
        return None

    @classmethod
    def eligible(cls, person):
        """ Must be active with a paid, playing subscription for this or previous year and 14 or over """
        year = Settings.current_year()
        if not person.state == Person.ACTIVE:
            return False
        if not person.sub:
            return False
        if not person.sub.paid:
            return False
        if person.sub.sub_year < year - 1:
            return False
        if not person.membership.is_playing:
            return False
        age = person.age_for_membership()
        if age and age < Membership.REGISTRATION_AGE:
            return False
        return True

    def is_male_only(self):
        return self.tournament and self.event_type in [EventType.MENS_SINGLES.value, EventType.MENS_DOUBLES.value]

    def is_female_only(self):
        return self.tournament and self.event_type in [EventType.LADIES_SINGLES.value, EventType.LADIES_DOUBLES.value]

    def is_mixed(self):
        return self.tournament and self.event_type == EventType.MIXED_DOUBLES.value

    def participant_from_person(self, person):
        """ return the Participant object for a person if there is one """
        part = Participant.objects.filter(event=self, person=person)
        if part:
            return part[0]
        else:
            part = Participant.objects.filter(event=self, partner=person)
            if part:
                return part[0]
        return None

    def billing_data(self):
        """
        Return a single BillingData object for this event
        NB you cannot generate this for a single person - it is always for everyone in the event
        """
        dict = {}
        if not self.billed and not self.active:
            for p in self.participant_set.all():
                if p.person_id in dict:
                    dict[p.person_id] += self.cost
                else:
                    dict[p.person_id] = self.cost
                if p.partner_id:
                    if p.partner_id in dict:
                        dict[p.partner_id] += self.cost
                    else:
                        dict[p.partner_id] = self.cost
            records = Event.objects.filter(id=self.id) # need a queryset of records to be updated
            return BillingData(self.item_type, dict, records, self.description, self.end_date)


class Participant(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, blank=False, null=False)
    person = models.ForeignKey(Person, on_delete=models.CASCADE, blank=False, null=False)
    partner = models.ForeignKey(Person, on_delete=models.CASCADE, blank=True, null=True, related_name='partner')
    text = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return f'{self.event.name}: {self.person.fullname}'

    
