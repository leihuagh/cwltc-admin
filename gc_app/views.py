# Go cardless views
import gocardless
from django.views.generic import View, RedirectView, TemplateView
from django import http
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.conf import settings
import json

# Read settings from setting.py and initialise go cardless api
GO_CARDLESS=getattr(settings, 'GO_CARDLESS')

gocardless.set_details(app_id=GO_CARDLESS['APP_ID'],
        app_secret=GO_CARDLESS['APP_SECRET'],
        access_token=GO_CARDLESS['ACCESS_TOKEN'],
        merchant_id=GO_CARDLESS['MERCHANT_ID'])

gocardless.environment = GO_CARDLESS['ENVIRONMENT']

class SubmitGC(RedirectView):
    """
    Redirect customer to GoCardless payment pages
    """
    def get_redirect_url(self, **kwargs):
        url = gocardless.client.new_subscription_url(
            amount=10,
            interval_length=1,
            interval_unit="month",
            name="Premium Subscription",
            description="A premium subscription for my site",
            user={'email': self.request.POST['email']})
        return url

    """
    Use get logic for post requests (Django 1.3 support)
    """
    def post(self, request, *args, **kwargs):
        return self.get(request, *args, **kwargs)

class ConfirmGC(TemplateView):
    """
    Confirms payment creation
    """
    def dispatch(self, request, *args, **kwargs):
    # Patch the Django dispatch method to confirm successful receipt of the
    # payment details before doing anything else
        gocardless.client.confirm_resource(request.GET)
        return super(ConfirmGC, self).dispatch(request, *args, **kwargs)

class GCWebhook(View):
    """
    Validate webhooks from GoCardless and process them
    """
    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super(GCWebhook, self).dispatch(*args, **kwargs)

    def post(self, request, *args, **kwargs):
        json_data = json.loads(request.body)
        if gocardless.client.validate_webhook(json_data['payload']):
            data = json_data['payload']
            if data['resource_type'] == 'subscription' and data['action'] == 'cancelled':
                for subscription in data['subscriptions']:
                    # Lookup the subscription using subscription['resource_id']
                    # Perform logic to cancel the subscription
                    # Any time-consuming jobs should be performed asynchronously
                    print("Subscription {0} cancelled".format(subscription['id']))
            return http.HttpResponse(status=200)
        return http.HttpResponse(status=403)
@csrf_exempt
def webhook(request):
    json_data = json.loads(request.body)
    return http.HttpResponse(status=200)