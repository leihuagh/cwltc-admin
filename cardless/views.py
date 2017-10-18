import os
import json
import hmac
import hashlib
import os
import secrets
from django.core.signing import Signer
from django.views.generic import View, RedirectView, TemplateView, ListView, DetailView, FormView
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseRedirect
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse
from members.models import Person, Invoice, Payment
from .models import Mandate
from .services import cardless_client, process_payment_event, process_mandate_event


class MandateCreateView(View):
    """
    Starts the mandate creation through a Go Cardless page
    Can be initiated with an invoice token or person token
    """
    def get(self, request, *args, **kwargs):
        invoice_token = kwargs.pop('invoice_token', None)
        person_token = kwargs.pop('person_token', None)
        signer = Signer()
        if invoice_token:
            invoice_id = signer.unsign(self.kwargs['invoice_token'])
            invoice = get_object_or_404(Invoice, pk=invoice_id)
            person = invoice.person
        elif person_token:
            person_id = signer.unsign(self.kwargs['person_token'])
            person = get_object_or_404(Person, pk=person_id)

        description = "CWLTC Mandate"
        session_token = secrets.token_urlsafe(20)
        url = request.build_absolute_uri(reverse('cardless-redirect-flow'))
        flow = cardless_client().redirect_flows.create(
            params={
                "description": description,
                "session_token": session_token,
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
        request.session['session_token'] = session_token
        request.session['person_id'] = person.id
        request.session['invoice_token'] = invoice_token
        return redirect(flow.redirect_url)


class RedirectFlowView(View):
    """
    Come here after mandate details have been entered on Go Cardless
    Confirm the mandate creation, create a mandate object linked to person and redirect to success
    """
    def get(self, request, *args, **kwargs):
        flow = request.session.get('flow', None)
        session_token = request.session.get('session_token', None)
        person_id = request.session.get('person_id', None)
        invoice_token = request.session('invoice_token', '0')
        if flow and session_token and person_id:
            new_flow = cardless_client().redirect_flows.complete(
                identity=flow.id,
                params={
                    "session_token": session_token
                })
            person = Person.objects.get(id=person_id)
            mandate = Mandate.objects.create(
                mandate_id=new_flow.links.mandate,
                customer_id=new_flow.links.customer,
                person=person,
                active=False
            )
            del request.session['flow']
            del request.session['session_token']
            del request.session['person_id']
            del request.session['invoice_token']
            return redirect('cardless_mandate_success', invoice_token=invoice_token)
        else:
            return HttpResponseBadRequest()


class MandateSuccessView(TemplateView):
    template_name = "cardless/mandate_success.html"

    def get_context_data(self, **kwargs):
        context = super(MandateSuccessView, self).get_context_data(**kwargs)
        invoice_token = kwargs['invoice_token']
        if invoice_token != '0':
            invoice_id = Signer().unsign(invoice_token)
            context['invoice'] = Invoice.objects.get(pk=invoice_id)
        return context


class PaymentCreateView(TemplateView):
    template_name = "cardless/payment_create.html"


class PaymentSuccessView(TemplateView):
    template_name = "cardless/payment_success.html"


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
            process_payment_event(event)
        if event['resource_type'] == 'mandates':
            process_mandate_event(event)
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


    def process_payouts(self, event, response):
        action = event['action']

        if action == 'paid':
            pass

        return response

    def process_refunds(selfself, event, response):
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