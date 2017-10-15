import os
import json
import hmac
import hashlib
import os
import secrets
import gocardless_pro
from django.views.generic import View, RedirectView, TemplateView, ListView, DetailView, FormView
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseRedirect
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse
from members.models import Person, Payment
from .models import Mandate
from .services import cardless_client

class MandateCreateView(View):

    def get(self, request, *args, **kwargs):
        person = get_object_or_404(Person, pk=self.kwargs['pk'])
        description = "CWLTC"
        token = secrets.token_urlsafe(20)
        url = request.build_absolute_uri(reverse('cardless-redirect-flow'))
        flow = cardless_client().redirect_flows.create(
            params={
                "description": description,
                "session_token": token,
                "success_redirect_url": url,
                "prefilled_customer": {
                    "given_name": person.first_name,
                    "family_name": person.last_name,
                    "email": person.email,
                    "address_line1": person.address.address1,
                    "address_line2": person.address.address2,
                    "city": person.address.town,
                    "postal_code": person.address.post_code
                }
            }
        )
        request.session['flow'] = flow
        request.session['token'] = token
        request.session['person_id'] = person.id
        return redirect(flow.redirect_url)


class RedirectFlowView(View):

    def get(self, request, *args, **kwargs):
        flow = request.session.get('flow', None)
        token = request.session.get('token', None)
        person_id = request.session.get('person_id', None)
        if flow and token and person_id:
            new_flow = cardless_client().redirect_flows.complete(
                identity=flow.id,
                params={
                    "session_token": token
                })
            person = Person.objects.get(id=person_id)
            mandate = Mandate.objects.create(
                mandate_id=new_flow.links.mandate,
                customer_id=new_flow.links.customer,
                person=person,
                active=False
            )
            del request.session['flow']
            del request.session['token']
            del request.session['person_id']
            return redirect('cardless-mandate-success')
        else:
            return HttpResponseBadRequest()

class MandateSuccessView(TemplateView):
    template_name = "cardless/mandate_success.html"


class Webhook(View):

    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super(Webhook, self).dispatch(*args, **kwargs)

    def is_valid_signature(self, request):
        secret = bytes(os.environ['GC_WEBHOOK_SECRET'], 'utf-8')
        computed_signature = hmac.new(
            secret, request.body, hashlib.sha256).hexdigest()
        provided_signature = request.META["HTTP_WEBHOOK_SIGNATURE"]
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
        if event['resource_type'] == 'payments':
            return self.process_payments(event, response)
        if event['resource_type'] == 'mandates':
            return self.process_mandates(event, response)
        if event['resource_type'] == 'payouts':
            return self.process_payouts(event, response)
        if event['resource_type'] == 'refunds':
            return self.process_refunds(event, response)
        if event['resource_type'] == 'subscriptions':
            return self.process_subscriptions(event, response)
        else:
            response.write("Don't know how to process an event with \
                resource_type {}\n".format(event['resource_type']))
            return response

    def process_payments(selfself, event, response):
        payment = Payment.objects.filter(payment_id = event['links']['payment'])
        action = event['action']
        if action == 'created':
            pass
        elif action == 'customer_approval_granted':
            pass
        elif action == 'customer_approval_denied':
            pass
        elif action == 'submitted':
            pass
        elif action == 'confirmed':
            pass
        elif action == 'cancelled':
            pass
        elif action == 'failed':
            pass
        elif action == 'charged_back':
            pass
        elif action == 'chargeback_cancelled':
            pass
        elif action == 'paid_out':
            pass
        elif action == 'late_failure_settled':
            pass
        elif action == 'chargeback_settled':
            pass
        elif action == 'resubmission_requested':
            pass
        return response

    def process_mandates(self, event, response):
        mandate = Mandate.objects.filter(mandate_id = event['links']['mandate'])
        action = event['action']

        if action == 'active' or action == 'reinstated':
            mandate.active = True
            mandate.save()

        elif action == 'failed' or action == 'expired':
            mandate.active=False
            mandate.save()

        elif action == 'cancelled' or action == 'transferred' or action ==' replaced':
            mandate.delete()

        return response

    def process_payouts(selfself, event, response):
        payment = Payment.objects.filter(payment_id = event['links']['payment'])
        action = event['action']

        if action == 'paid':
            pass

        return response

    def process_refunds(selfself, event, response):
        payment = Payment.objects.filter(payment_id = event['links']['payment'])
        action = event['action']
        # TODO refunds
        pass

        return response

    def process_subscriptions(selfself, event, response):
        # TODO subscription actions
        action = event['action']

        if action == 'created':
            pass

        elif action == 'customer_approval_granted':
            pass

        elif action == 'customer_approval_denied':
            pass

        elif action == 'payout_created':
            pass

        elif action == 'cancelled':
            pass

        elif action == 'finished':
            pass

        return response