from django.db import models
from taggit.managers import TaggableManager
from members.models import ItemType, Person, ModelEnum




class Event(models.Model):
    
    class EventType(ModelEnum):
        MENS_SINGLES = 0
        LADIES_SINGLES = 1
        MENS_DOUBLES = 2
        LADIES_DOUBLES = 3
        MIXED_DOUBLES = 4
        OPEN_SINGLES = 5
        OPEN_DOUBLES = 6
    
    name = models.CharField(max_length=50, blank=False)
    description = models.CharField(max_length=1000, blank=True)
    event_type = models.SmallIntegerField(choices=EventType.choices(), default=0)
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    cost = models.DecimalField(max_digits=5, decimal_places=2, null=False)
    item_type = models.ForeignKey(ItemType, on_delete=models.CASCADE, null=True, blank=True)
    tags = TaggableManager()

    def __str__(self):
        return self.name

    def add_person(self, person, person2=None, text=""):
        Participant.objects.create(event=self, person=person, person2=person2, text=text)

    def with_partner(self):
        """ True if event must have a partner """
        return self.event_type in (Event.EventType.MENS_DOUBLES,
                                   Event.EventType.LADIES_DOUBLES,
                                   Event.EventType.MIXED_DOUBLES,
                                   Event.EventType.OPEN_DOUBLES)
    
    def validate_entrants(self, person, partner):
        """
        Check that gender of person and partner(if any) is correct
        Return None if OK else return an error message
        """
        err_male = 'Person must be male'
        err_female = 'Person must be female'
        err_partner_male = 'Your partner must be male'
        err_partner_female = 'Your partner must be female'
        err_no_partner = 'You must specify a partner'

        if self.event_type == Event.EventType.MENS_SINGLES:
            if person.gender != 'M':
                return err_male
        elif self.event_type == Event.EventType.LADIES_SINGLES:
            if person.gender != 'F':
                return err_female
        elif self.event_type == Event.EventType.MENS_DOUBLES:
            if person.gender != 'M':
                return err_male
            if partner:
                if partner.gender != 'M':
                    return err_partner_male
            else:
                return err_no_partner
        elif self.event_type == Event.EventType.LADIES_DOUBLES:
            if person.gender != 'F':
                return err_female
            if partner:
                if partner.gender != 'F':
                    return err_female
            else:
                return err_no_partner

        elif self.event_type == Event.EventType.MIXED_DOUBLES:
            if partner:
                if person.gender == 'F':
                    if partner.gender != 'M':
                        return err_partner_male
                else:
                    if partner.gender != 'F':
                        return err_partner_female
            else:
                return err_no_partner
        elif self.event_type == Event.EventType.OPEN_SINGLES:
            pass
        elif self.event_type == Event.EventType.OPEN_DOUBLES:
            if not partner:
                return err_no_partner
        return None


class Participant(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, blank=False, null=False)
    person = models.ForeignKey(Person, on_delete=models.CASCADE, blank=False, null=False)
    partner = models.ForeignKey(Person, on_delete=models.CASCADE, blank=True, null=True, related_name='partner')
    text = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return f'{self.event.name}: {self.person.fullname}'