from django.db import models
from members.models import Person
# Go Cardless model

class Cardless(models.Model):
    mandate_id = models.CharField(max_length=50)
    customer_id = models.CharField(max_length=50)

# class WebHook(models.Model):
#     creation_date = models.DateTimeField(auto_now_add=True)
#     resource_type = models.CharField(max_length=30)
#     action = models.CharField(max_length=20)
#     message = models.CharField(max_length=1000)
#     processed = models.BooleanField(default=False)
#     error = models.CharField(max_length=80)
#     invoice = models.ForeignKey(Invoice, null=True)
#     subscription = models.ForeignKey(Subscription, null=True)
