from django.db import models
from taggit.managers import TaggableManager
from members.models import ItemType, Person


class Event(models.Model):
    name = models.CharField(max_length=50, blank=False)
    description = models.CharField(max_length=1000, blank=True)
    url_name = models.CharField(max_length=50, blank=False)
    start_date = models.CharField(blank=True, null=True)
    end_date = models.CharField(blank=True, null=True)
    cost = models.DecimalField(max_digits=5, decimal_places=2, null=False)
    item_type = models.ForeignKey(ItemType, on_delete=models.CASCADE, null=True, blank=True)
    tags = TaggableManager()

    def __str__(self):
        return self.name

    def add_person(self, person, person2=None, text=""):
        Participant.objects.create(event=self, person=person, person2=person2, text=text)


class Participant(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, blank=False, null=False)
    person = models.ForeignKey(Person, on_delete=models.CASCADE, blank=False, null=False)
    person2 = models.ForeignKey(Person, on_delete=models.CASCADE, blank=True, null=True)
    text = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return f'{self.event.name}: {person.fullname}'