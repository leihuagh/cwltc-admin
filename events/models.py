from django.db import models
from taggit.managers import TaggableManager
from members.models import ItemType, Person, ModelEnum


class Tournament(models.Model):
    """ A tournament is a collection of events """
    name = models.CharField(max_length=50, blank=True)
    description = models.CharField(max_length=1000, blank=True)
    draw_date = models.DateField(blank=False, null=False)
    finals_date = models.DateField(blank=False, null=False)
    event_cost = models.DecimalField(max_digits=5, decimal_places=2, null=False)
    active = models.BooleanField(default=True)

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
        Event.objects.create(name="Men's Plate", event_type=EventType.MENS_DOUBLES, cost=self.event_cost,
                             item_type_id=ItemType.TOURNAMENT, tournament=self, active=False, online_entry=False)
        Event.objects.create(name="Ladies' Plate", event_type=EventType.LADIES_DOUBLES, cost=self.event_cost,
                             item_type_id=ItemType.TOURNAMENT, tournament=self, active=False, online_entry=False)
        Event.objects.create(name="Mixed Plate", event_type=EventType.MIXED_DOUBLES, cost=self.event_cost,
                             item_type_id=ItemType.TOURNAMENT, tournament=self, active=False, online_entry=False)

      
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
    event_type = models.SmallIntegerField(choices=EventType.choices(), default=0)
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    cost = models.DecimalField(max_digits=5, decimal_places=2, null=False)
    item_type = models.ForeignKey(ItemType, on_delete=models.CASCADE, null=True, blank=True)
    active = models.BooleanField(default=True)
    online_entry = models.BooleanField(default=True)
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return self.name

    def add_person(self, person, person2=None, text=""):
        Participant.objects.create(event=self, person=person, person2=person2, text=text)

    def with_partner(self):
        """ True if event must have a partner """
        return self.event_type in (EventType.MENS_DOUBLES,
                                   EventType.LADIES_DOUBLES,
                                   EventType.MIXED_DOUBLES,
                                   EventType.OPEN_DOUBLES)
    
    def validate_entrants(self, person, partner):
        """
        Check that gender of person and partner(if any) is correct
        Return None if OK else return an error message
        """
        err_male = 'Entrant must be male'
        err_female = 'Entrant must be female'
        err_partner_male = 'Your partner must be male'
        err_partner_female = 'Your partner must be female'
        err_no_partner = 'You must specify a partner'

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

    def is_male_only(self):
        return self.event_type in [EventType.MENS_SINGLES.value, EventType.MENS_DOUBLES.value]

    def is_female_only(self):
        return self.event_type in [EventType.LADIES_SINGLES.value, EventType.LADIES_DOUBLES.value]

    def is_mixed(self):
        return self.event_type == EventType.MIXED_DOUBLES.value

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

class Participant(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, blank=False, null=False)
    person = models.ForeignKey(Person, on_delete=models.CASCADE, blank=False, null=False)
    partner = models.ForeignKey(Person, on_delete=models.CASCADE, blank=True, null=True, related_name='partner')
    text = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return f'{self.event.name}: {self.person.fullname}'

    
