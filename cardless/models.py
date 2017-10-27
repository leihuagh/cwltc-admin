from django.db import models
from members.models import Person, Payment
# Go Cardless model

class Mandate(models.Model):
    mandate_id = models.CharField(max_length=50)
    customer_id = models.CharField(max_length=50)
    event_id = models.CharField(max_length=50)
    active = models.BooleanField(default=False)
    person = models.ForeignKey(Person, on_delete=models.CASCADE, related_name='mandates')

class Payment_Event(models.Model):
    created_at = models.CharField(max_length=30)
    event_id = models.CharField(max_length=50)
    action = models.CharField(max_length=30)
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name='events', null=True)


