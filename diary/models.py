from django.db import models
from members.models import Person

class Booking(models.Model):
    date = models.DateField()
    time = models.TimeField()
    court = models.PositiveSmallIntegerField()
    person = models.ForeignKey(Person, on_delete=models.SET_NULL, null=True, blank=True)
    note = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return f'{date} {time} {court}'
