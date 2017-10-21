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
from django.shortcuts import redirect, get_object_or_404, render
from django.urls import reverse
from members.models import Person, Invoice, Payment
from .models import Mandate
from .services import cardless_client, process_payment_event, process_mandate_event, detokenise, active_mandate


class PaymentCreateView(TemplateView):
    """
    If mandate exists get confirmation and create payment
    If mandate does not exist, redirect to create mandate
    """
    template_name = "cardless/payment_create.html"

    def get(self, request, *args, **kwargs):
        invoice = detokenise(kwargs['invoice_token'])
        if active_mandate(invoice.person):
            context = self.get_context_data(**kwargs)
            context['invoice'] = invoice
            context['person'] = invoice.person
            return self.render_to_response(context)
        else:
            return redirect('cardless_create_mandate', invoice_token=kwargs['invoice_token'])

    # def post(self, request, *args, **kwargs):
    #     if 'pay' in request.POST:
    #         pay_invoice(decode_invoice(kwargs['invoice_token']))
    #         return redirect(kwargs['next'])
    #     if 'query' in request.POST:

class PaymentSuccessView(TemplateView):
    template_name = "cardless/payment_success.html"

class MandateCreateView(View):
    """
    Starts the mandate creation through a Go Cardless page
    Can be initiated with an invoice token or person token
    """
    def get(self, request, *args, **kwargs):
        invoice_token = kwargs.pop('invoice_token', None)
        person_token = kwargs.pop('person_token', None)
        if invoice_token:
            invoice = detokenise(invoice_token)
            person = invoice.person
        else:
            person = detokenise(person_token)
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
                    "address_line3": "",
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
        invoice_token = request.session('invoice_token', None)
        if flow and session_token and person_id:
            new_flow = cardless_client().redirect_flows.complete(
                identity=flow.id,
                params={
                    "session_token": session_token
                })
            person = Person.objects.get(id=person_id)
            Mandate.objects.create(
                mandate_id=new_flow.links.mandate,
                customer_id=new_flow.links.customer,
                person=person,
                active=False
            )
            del request.session['flow']
            del request.session['session_token']
            del request.session['person_id']
            del request.session['invoice_token']
            if invoice_token:
                pay_invoice(detokenise(invoice_token))
            return redirect('cardless_mandate_success', invoice_token=invoice_token)
        else:
            return HttpResponseBadRequest()


class MandateSuccessView(TemplateView):
    template_name = "cardless/mandate_success.html"

    def get_context_data(self, **kwargs):
        context = super(MandateSuccessView, self).get_context_data(**kwargs)
        invoice_token = kwargs['invoice_token']
        if invoice_token != '0':
            context['invoice'] = detokenise(invoice_token, Invoice)
        return context


class MandateListView(ListView):
    """ All mandates for 1 person or all in our Go Cardless account"""
    template_name = "cardless/mandate_list.html"
    model = Mandate
    context_object_name = 'mandates'

    def get_context_data(self, **kwargs):
        context = super(MandateListView, self).get_context_data(**kwargs)
        person_id = self.kwargs.get('person_id', None)
        if person_id:
            context['person'] = Person.objects.get(id=person_id)
        return context


class MandateGcListView(TemplateView):
    """ Fetches list from GoCardless site """
    template_name = "cardless/mandate_gc_list.html"

    def get_context_data(self, **kwargs):
        context = super(MandateGcListView, self).get_context_data(**kwargs)
        context['mandates'] = cardless_client().mandates.list().records
        return context


class MandateDetailView(TemplateView):
    """ Detailed mandate data from Go Cardless """
    template_name = "cardless/mandate_detail.html"

    def get_context_data(self, **kwargs):
        context = super(MandateDetailView, self).get_context_data(**kwargs)
        gc_mandate = cardless_client().mandates.get(kwargs['mandate_id'])
        try:
            mandate = Mandate.objects.get(mandate_id=gc_mandate.id)
        except Mandate.DoesNotExist:
            mandate = None
        context['gc_mandate'] = gc_mandate
        context['mandate'] = mandate
        if mandate and gc_mandate.status == 'cancelled' or gc_mandate.status == 'expired':
            context['remove'] = True
        if gc_mandate.status != 'cancelled':
            context['cancel'] = True
        return context

    def post(self, request, *args, **kwargs):
        mandate = Mandate.objects.filter(mandate_id=kwargs['mandate_id'])
        if 'remove' in request.POST:
            mandate.delete()
        elif 'cancel' in request.POST:
            cardless_client().mandates.cancel(kwargs['mandate_id'])
            mandate.delete()
        return redirect('cardless_mandate_list')


class CustomerDetailView(TemplateView):
    """ Detailed customer data from Go Cardless """
    template_name = "cardless/customer_detail.html"

    def get_context_data(self, **kwargs):
        context = super(CustomerDetailView, self).get_context_data(**kwargs)
        customer = cardless_client().customers.get(kwargs['customer_id'])
        mandate = Mandate.objects.filter(customer_id=customer.id)[0]
        if mandate:
            context['person'] = mandate.person
            context['address'] = mandate.person.address
        context['customer'] = customer
        return context


class EventDetailView(TemplateView):
    """ Detailed event data from Go Cardless """
    template_name = "cardless/event_detail.html"

    def get_context_data(self, **kwargs):
        context = super(EventDetailView, self).get_context_data(**kwargs)
        return context





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