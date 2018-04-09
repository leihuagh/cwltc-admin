from django.db import models
from members.models import Person


class Tickets(models.Model):

    court = models.CharField(max_length=10, blank=False, null=False)
    date = models.DateField()
    day = models.IntegerField()
    price = models.IntegerField()


class OptOut(models.Model):

    person = models.ForeignKey(Person, on_delete=models.CASCADE, blank=False, null=False)
    ticket = models.ForeignKey(Tickets, on_delete=models.CASCADE, blank=True, null=True)
    all_days = models.BooleanField(default=False)



