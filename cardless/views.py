import os
import json
import hmac
import hashlib
import os
import secrets
import gocardless_pro
from django.conf import settings
from django.urls import reverse
from django.views.generic import View, RedirectView, TemplateView, ListView, DetailView, FormView
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.http import HttpResponse
from members.models import Person


def client():
    return gocardless_pro.Client(
        access_token=getattr(settings, 'CARDLESS_ACCESS_TOKEN'),
        environment=getattr(settings, 'CARDLESS_ENVIRONMENT')
    )


def redirect_flow():
    return client().redirect_flows.create(
        params={
            "description": "Ale Casks",  # This will be shown on the payment pages
            "session_token": "dummy_session_token",  # Not the access token
            "success_redirect_url": "https://developer.gocardless.com/example-redirect-uri",
            "prefilled_customer": {  # Optionally, prefill customer details on the payment page
                "given_name": "Tim",
                "family_name": "Rogers",
                "email": "tim@gocardless.com",
                "address_line1": "338-346 Goswell Road",
                "city": "London",
                "postal_code": "EC1V 7LQ"
            }
        }
    )



def create_mandate(person, description, session):
    token = secrets.token_urlsafe(20)
    url = reverse('cardless-redirect-flow')
    flow = client().redirect_flows.create(
        params={
            "description": description,
            "session_token": token,
            "success_redirect_url": url,
            "prefilled_customer": {
                "given_name": person.first_name,
                "family_name": person.last_name,
                "email": person.email,
                "address_line1": person.adddress1,
                "address_line2": person.adddress2,
                "city": person.address.town,
                "postal_code": person.address.post_code
            }
        }
    )
    session['flow'] = flow
    session['token'] = token
    session['person_id'] = person.id


class RedirectFlowView(View):
    def get(self, request, *args, **kwargs):
        flow = request.session['flow']
        token = request.session['token']
        person_id = request.session['person_id']
        new_flow = client().redirect_flows.complete(
            identity=flow,
            params={
                "session_token": token
            })
        person = Person.objects.get(id=person_id)
        person.mandate = new_flow.links.mandate
        person.customer = new_flow.links.customer


class Webhook(View):

    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super(Webhook, self).dispatch(*args, **kwargs)

    def is_valid_signature(self, request):
        secret = bytes(os.environ['GC_WEBHOOK_SECRET'], 'utf-8')
        computed_signature = hmac.new(
            secret, request.body, hashlib.sha256).hexdigest()
        provided_signature = request.META["HTTP_WEBHOOK_SIGNATURE"]
        # In flask, access the webhook signature header with
        # request.headers.get('Webhook-Signature')
        return hmac.compare_digest(provided_signature, computed_signature)

    def post(self, request, *args, **kwargs):
        if self.is_valid_signature(request):
            response = HttpResponse()
            payload = json.loads(request.body.decode('utf-8'))
            # Each webhook may contain multiple events to handle, batched together.
            for event in payload['events']:
                self.process(event, response)
            return response
        else:
            return HttpResponse(498)

    def process(self, event, response):
        response.write("Processing event {}\n".format(event['id']))
        if event['resource_type'] == 'mandates':
            return self.process_mandates(event, response)
        # ... Handle other resource types
        else:
            response.write("Don't know how to process an event with \
                resource_type {}\n".format(event['resource_type']))
            return response

    def process_mandates(self, event, response):
        if event['action'] == 'cancelled':
            response.write("Mandate {} has been \
                cancelled\n".format(event['links']['mandate']))
        # ... Handle other mandate actions
        else:
            response.write("Don't know how to process an event with \
                resource_type {}\n".format(event['resource_type']))
        return response
