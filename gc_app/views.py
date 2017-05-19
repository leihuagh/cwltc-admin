# Go cardless views
import gocardless
from decimal import Decimal
from datetime import date, datetime
import json
import logging
import csv
from django.views.generic import View, RedirectView, TemplateView, ListView, DetailView, FormView
from django import http
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.conf import settings
from django.shortcuts import redirect, render
from django.contrib import messages
from django.core.urlresolvers import reverse
from braces.views import LoginRequiredMixin

from members.models import Invoice, Payment, ExcelBook
from members.services import invoice_pay_by_gocardless

from .models import WebHook
from .forms import  UploadForm

logger = logging.getLogger(__name__)

# Read settings from setting.py and initialise go cardless api
GO_CARDLESS = getattr(settings, 'GO_CARDLESS')

gocardless.set_details(app_id=GO_CARDLESS['APP_ID'],
                       app_secret=GO_CARDLESS['APP_SECRET'],
                       access_token=GO_CARDLESS['ACCESS_TOKEN'],
                       merchant_id=GO_CARDLESS['MERCHANT_ID'])

gocardless.environment = GO_CARDLESS['ENVIRONMENT']

   
def gc_create_bill_url(invoice):
    '''
    Create a GoCardless bill for an invoice
    '''
    user = invoice.person
    if gocardless.environment == 'sandbox':
        email = 'ian@ktconsultants.co.uk' 
    else:
        email = user.email
    url = gocardless.client.new_bill_url(
        amount=invoice.total,
        state=invoice.id,
        name='Payment for Coombe Wood invoice',
        description='Reference: '+ invoice.number(),
        user={'email': email,
              'first_name': user.first_name,
              'last_name': user.last_name,
              'billing_address1': user.address.address1,
              'billing_address2': user.address.address2,
              'billing_town': user.address.town,
              'billing_postcode': user.address.post_code}
        )
    return url

class GCConfirm(TemplateView):
    """
    Confirms payment creation after a bill request has been processed by user
    """
    def dispatch(self, request, *args, **kwargs):
        # Confirm successful receipt of the payment details
        # before rendering the template
        gocardless.client.confirm_resource(request.GET)
        # store the bill id in the invoice record
        invoice_id = request.GET.get('state')
        invoice = Invoice.objects.get(pk=invoice_id)
        invoice.gocardless_bill_id = request.GET.get('resource_id')
        invoice.gocardless_action = "created"
        invoice.save()
        return super(GCConfirm, self).dispatch(request, *args, **kwargs)

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
            resource_type = data['resource_type']
            action = data['action']

            # First save the hook to the database
            # we update it later after it is parsed
            hook = WebHook(resource_type=resource_type,
                           action=action,
                           message=request.body,
                           processed=False,
                           error="")
            hook.save()

            if resource_type == 'bill':
                for bill in data['bills']:
                    try:
                        invoice = Invoice.objects.get(gocardless_bill_id=bill['id'])
                        invoice.gocardless_action = action
                        hook.invoice = invoice
                        hook.save()
                        invoice.save()
                    except:                                      
                        hook.error = "Invoice {} not found".format(bill_id)
                        hook.save()
                        continue

                    # fake the sandbox webhooks to match the invoice total
                    if gocardless.environment == 'sandbox':
                        amount = invoice.total
                        fee = amount / 100
                        if amount > 2:
                            fee = 2
                    else:
                        amount = Decimal(bill['amount'])
                        fee = amount - Decimal(bill['amount_minus_fees'])

                    if action == 'paid':
                        try:
                            invoice_pay_by_gocardless(invoice, amount, fee, datetime.now())
                            hook.processed = True
                        except Exception as ex:                                      
                            hook.error = ex.message
                           
                    elif action == 'created':
                        pass
                    elif action == 'withdrawn':
                        pass
                    elif action == 'failed':
                        pass
                    elif action == 'cancelled':
                        pass
                    elif action == 'refunded':
                        pass
                    elif action == 'chargeback':
                        pass
                    elif action == 'retried':
                        pass                
                    else:
                        hook.error= "Unknown action" 
                    hook.save()                        
                return HttpResponse(status=200)

            elif resource_type == 'subscription':
                if action == 'cancelled':
                    for subscription in data['subscriptions']:
                        # Lookup the subscription using subscription['resource_id']
                        # Perform logic to cancel the subscription
                        # Any time-consuming jobs should be performed asynchronously
                        print("Subscription {0} cancelled".format(subscription['id']))
                elif action== 'expired':
                    pass
                return HttpResponse(status=200)

            elif resource_type == 'pre_authorization':
                return HttpResponse(status=200)

        else:
            hook = WebHook(resource_type="Bad payload",
                action="",
                message=json_data,
                processed=False,
                error="Bad payload")
            hook.save()       
            return HttpResponse(status=403)

class WebHookList(LoginRequiredMixin, ListView):
    model = WebHook 
    template_name = 'gc_app/webhook_list.html'
    context_object_name = 'hooks'

    def get_queryset(self):
        qset =  WebHook.objects.all().order_by('-creation_date')
        return qset

class WebHookDetailView(LoginRequiredMixin, DetailView):
    model = WebHook 
    template_name = 'gc_app/webhook_detail.html'

    def get_context_data(self, **kwargs):
        context = super(WebHookDetailView, self).get_context_data(**kwargs)
        hook = self.get_object()
        context['hook'] = hook
        context['message'] = '<pre>' + json.dumps(json.loads(hook.message), indent=4) + '</pre>' # .replace('\n', '<br />').replace(' ','&nbsp')
        return context

class GcImportView(LoginRequiredMixin, FormView):
    '''
    Import a GoCardless csv file
    '''
    form_class = UploadForm
    template_name = 'members/file_select.html'

    def get_context_data(self, **kwargs):
        context =  super(GcImportView, self).get_context_data(**kwargs)
        context['title'] = "Import GoCardless csv file"
        return context

    def form_valid(self, form):
        result, errors = process_csvfile(self.request.FILES['upload_file'])
        if errors:
            messages.error(self.request, errors)
        else:
            messages.success(self.request, result)
        return super(GcImportView, self).form_valid(form)

    def get_success_url(self):
        return reverse('gc-import')


def process_csvfile(f):
    '''
    Read a GoCardless export and update all invoices that are now paid out
    '''
    reader = csv.DictReader(f)
    record_count = 0
    paid_count = 0
    mismatches = []
    notfounds = []
    errors = ""
    result = ""
    try:
        for row in reader:         
            id = row['id']
            status= row['status']
            amount = Decimal(row['amount'])
            fee = Decimal(row['transaction_fee'])
            payout_date = unpack_date(row['payout_date'])
            meta = row['metadata.description'].split(':')
            ids = meta[1].split('/')
            person_id = ids[0].strip()
            invoice_id = ids[1].strip()

            record_count += 1
            if status == 'paid_out':
                try:
                    invoice = Invoice.objects.get(pk=invoice_id)
                    if invoice.gocardless_bill_id == id:
                        if invoice.state != Invoice.PAID_IN_FULL:
                            invoice_pay_by_gocardless(invoice, amount, fee, payout_date)
                            paid_count += 1
                    else:
                        mismatches.append(invoice_id)
                except Exception as ex:
                    notfounds.append(invoice_id)
        result = "{} records processed and {} invoices changed to paid state.".format(
            record_count, paid_count)        
        if len(mismatches) > 0:
            errors = "Mismatched invoice ids: " + ",".join(map(str, mismatches))
        if len(notfounds) > 0:
            errors += " Not found invoice ids: " + ",".join(map(str, notfounds))
        
    except KeyError:

        errors = "Invalid file format"
    return [result, errors]

def unpack_date_helper(date_string):
    '''
    Unpack a date string separated by - or / into parts
    original gocardless file uses yyyy-mm-dd
    If its been through Excel it will be dd/mm/yyyy
    always return list [yyyy, mm, dd]
    ''' 
    dateparts = date_string.split('-')
    if len(dateparts) == 3:
        return dateparts
    dateparts = date_string.split('/')      
    if len(dateparts) == 3:
        return  [dateparts[2], dateparts[1], dateparts[0]]
    raise ValueError("Cannot parse date", date_string)

def unpack_date(date_string):
    '''
    Unpack a date string separated by - or / to a date
    '''
    dateparts = unpack_date_helper(date_string)
    return  date(int(dateparts[0]), int(dateparts[1]), int(dateparts[2]))

def unpack_datetime(datetime_string):
    '''
    Unpack a datetime string separated by - or / to a datetime
    '''
    parts = datetime_string.split(' ')
    if len(parts) == 2:
        dateparts = unpack_date_helper(parts[0])
        timeparts = parts[1].split(':')
        if len(timeparts) == 3:
            return datetime(int(dateparts[0]), int(dateparts[1]), int(dateparts[2]),
                              int(timeparts[0]), int(timeparts[1]), int(timeparts[2]))
    raise ValueError("Cannot parse time from ", datetime_string)