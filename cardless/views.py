import json
import hmac
import hashlib
import logging
import secrets
from datetime import datetime, timedelta
from django.views.generic import View, TemplateView, ListView, FormView
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import redirect, render
from django.urls import reverse
from django.contrib import messages
from braces.views import LoginRequiredMixin
from members.models import Person, Invoice
from .models import Mandate
from .services import cardless_client, process_payment_event, process_mandate_event, detokenise, active_mandate, \
    create_cardless_payment, invoice_payments_list, webhook_secret, \
    payments_list
from .forms import UploadCSVForm, ProcessPaymentsForm
from .importcsv import process_csvfile, process_payments_list


logger = logging.getLogger(__name__)


class PaymentCreateView(TemplateView):
    """
    If mandate exists get confirmation and create payment
    If mandate does not exist, redirect to create mandate
    """
    template_name = "cardless/payment_create.html"

    def get(self, request, **kwargs):
        invoice = detokenise(kwargs['invoice_token'], Invoice)
        payments = invoice_payments_list(invoice, pending=True, paid=True)
        if payments:
            return redirect('public-home')
        mandate = active_mandate(invoice.person)
        if mandate:
            context = self.get_context_data(**kwargs)
            context['invoice_token'] = kwargs['invoice_token']
            context['invoice'] = invoice
            context['person'] = invoice.person
            return self.render_to_response(context)
        else:
            return redirect('cardless_mandate_create_i', invoice_token=kwargs['invoice_token'])

    def post(self, request, **kwargs):
        invoice = detokenise(kwargs['invoice_token'], Invoice)
        mandate = active_mandate(invoice.person)
        if 'pay' in request.POST:
            if create_cardless_payment(invoice, mandate):
                return redirect('cardless_payment_success', invoice_token=kwargs['invoice_token'])
            else:
                return redirect('cardless_payment_failure', invoice_token=kwargs['invoice_token'])
        return redirect('invoice-public', token=kwargs['invoice_token'])


class PaymentSuccessView(TemplateView):
    template_name = "cardless/payment_success.html"

    def get_context_data(self, **kwargs):
        context= super(PaymentSuccessView, self).get_context_data(**kwargs)
        context['invoice'] = detokenise(kwargs['invoice_token'], Invoice)
        return context


class PaymentFailureView(TemplateView):
    template_name = "cardless/payment_failure.html"

    def get_context_data(self, **kwargs):
        context= super(PaymentFailureView, self).get_context_data(**kwargs)
        context['invoice'] = detokenise(kwargs['invoice_token'], Invoice)
        return context


class PaymentProcessView(LoginRequiredMixin, FormView):
    template_name = 'members/generic_crispy_form.html'
    form_class = ProcessPaymentsForm

    def get_context_data(self, **kwargs):
        context = super(PaymentProcessView, self).get_context_data()
        context['title'] = 'Process recent GoCardless payments'
        return context

    def form_valid(self, form):
        days = form.cleaned_data['days']
        start_date = datetime.now() - timedelta(days=days)
        gc_payments = payments_list(start_date)
        updated, not_found, created = process_payments_list(gc_payments)
        context = {}
        context['payments'] = gc_payments
        context['updated'] = updated
        context['not_found'] = not_found
        context['created'] = created
        return render(self.request, 'cardless/payment_process.html', context)


class MandateCreateView(View):
    """
    Starts the mandate creation through a Go Cardless page
    Can be initiated with an invoice token or person token
    """
    def get(self, request, **kwargs):

        invoice_token = kwargs.pop('invoice_token', None)
        person_token = kwargs.pop('person_token', None)
        if invoice_token:
            invoice = detokenise(invoice_token, Invoice)
            person = invoice.person
        else:
            person = detokenise(person_token, Person)
        description = "CWLTC Mandate"
        session_token = secrets.token_urlsafe(20)
        url = request.build_absolute_uri(reverse('cardless_redirect_flow'))
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
    Confirm the mandate creation, create a mandate object linked to person
    redirect to create a payment if it was initiated by an invoice
    """
    def get(self, request, *args, **kwargs):
        flow = request.session.get('flow', None)
        session_token = request.session.get('session_token', None)
        person_id = request.session.get('person_id', None)
        invoice_token = request.session.get('invoice_token', None)
        if flow and session_token and person_id:
            try:
                new_flow = cardless_client().redirect_flows.complete(
                    identity=flow.id,
                    params={
                        "session_token": session_token
                    })
            except Exception as ex:
                return HttpResponseBadRequest()

            person = Person.objects.get(id=person_id)
            mandate = Mandate.objects.create(
                mandate_id=new_flow.links.mandate,
                customer_id=new_flow.links.customer,
                person=person,
            )
            del request.session['flow']
            del request.session['session_token']
            del request.session['person_id']
            del request.session['invoice_token']
            if invoice_token:
                return redirect('cardless_payment_create', invoice_token=invoice_token)
            return redirect('cardless_mandate_success')
        else:
            return HttpResponseBadRequest()


class MandateSuccessView(TemplateView):
    template_name = "cardless/mandate_success.html"


class MandateListView(LoginRequiredMixin, ListView):
    """ All mandates for 1 person or all in our Go Cardless account"""
    template_name = 'cardless/mandate_list.html'
    model = Mandate
    context_object_name = 'mandates'

    def get_context_data(self, **kwargs):
        context = super(MandateListView, self).get_context_data(**kwargs)
        person_id = self.kwargs.get('person_id', None)
        if person_id:
            context['person'] = Person.objects.get(id=person_id)
        return context


class MandateGcListView(LoginRequiredMixin, TemplateView):
    """ Fetches list from GoCardless site """
    template_name = "cardless/mandate_gc_list.html"

    def get_context_data(self, **kwargs):
        context = super(MandateGcListView, self).get_context_data(**kwargs)
        context['mandates'] = cardless_client().mandates.list().records
        return context


class MandateDetailView(LoginRequiredMixin, TemplateView):
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

    def post(self, request, **kwargs):
        mandate = Mandate.objects.filter(mandate_id=kwargs['mandate_id'])
        if 'remove' in request.POST:
            mandate.delete()
        elif 'cancel' in request.POST:
            cardless_client().mandates.cancel(kwargs['mandate_id'])
            mandate.delete()
        return redirect('cardless_mandate_list')


class CustomerDetailView(LoginRequiredMixin, TemplateView):
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


class EventDetailView(LoginRequiredMixin, TemplateView):
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
        secret = bytes(webhook_secret(), 'utf-8')
        computed_signature = hmac.new(
            secret, request.body, hashlib.sha256).hexdigest()
        provided_signature = request.META["HTTP_WEBHOOK_SIGNATURE"]
        return hmac.compare_digest(provided_signature, computed_signature)

    def post(self, request):
        if self.is_valid_signature(request):

            payload = json.loads(request.body.decode('utf-8'))
            # Each webhook may contain multiple events to handle, batched together.
            for event in payload['events']:
                logger.info("Webhook {}".format(event))
                self.process(event)
            return HttpResponse(status=204)
        else:
            return HttpResponse(status=498)

    def process(self, event):
        if event['resource_type'] == 'payments':
            process_payment_event(event)
        elif event['resource_type'] == 'mandates':
            process_mandate_event(event)
        elif event['resource_type'] == 'payouts':
            self.process_payouts(event)
        elif event['resource_type'] == 'refunds':
            self.process_refunds(event)
        elif event['resource_type'] == 'subscriptions':
            self.process_subscriptions(event)
        else:
            pass


    def process_payouts(self, event):
        action = event['action']

        if action == 'paid':
            pass

    def process_refunds(selfself, event):
        action = event['action']
        # TODO refunds
        pass

    def process_subscriptions(self, event):
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


class CardlessImportView(LoginRequiredMixin, FormView):
    '''
    Import a GoCardless csv file
    '''
    form_class = UploadCSVForm
    template_name = 'members/file_select.html'

    def get_context_data(self, **kwargs):
        context =  super(CardlessImportView, self).get_context_data(**kwargs)
        context['title'] = "Import GoCardless csv file of payments"
        return context

    def form_valid(self, form):
        result, errors = process_csvfile(self.request.FILES['upload_file'])
        if errors:
            messages.error(self.request, result + errors)
        else:
            messages.success(self.request, result)
        return super(CardlessImportView, self).form_valid(form)

    def get_success_url(self):
        return reverse('gc-import')
