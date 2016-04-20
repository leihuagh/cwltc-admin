# Go cardless views
import gocardless
from django.views.generic import View, RedirectView, TemplateView, ListView, DetailView
from django import http
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.conf import settings
from members.models import Invoice, Payment
from members.services import invoice_pay_by_gocardless
from gc_app.models import WebHook
from braces.views import LoginRequiredMixin
from decimal import Decimal
import json
import logging
import gc_app

logger =logging.getLogger(__name__)

# Read settings from setting.py and initialise go cardless api
GO_CARDLESS=getattr(settings, 'GO_CARDLESS')

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
        name = 'Payment for Coombe Wood invoice',
        description = 'Reference: '+ invoice.number(),
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
        invoice= Invoice.objects.get(pk = invoice_id)
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
                        return http.HttpResponse(status=403)

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
                            invoice_pay_by_gocardless(invoice, amount, fee)
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
                return http.HttpResponse(status=200)

            elif resource_type == 'subscription':
                if action == 'cancelled':
                    for subscription in data['subscriptions']:
                        # Lookup the subscription using subscription['resource_id']
                        # Perform logic to cancel the subscription
                        # Any time-consuming jobs should be performed asynchronously
                        print("Subscription {0} cancelled".format(subscription['id']))
                elif action== 'expired':
                    pass
                return http.HttpResponse(status=200)

            elif resource_type == 'pre_authorization':
                return http.HttpResponse(status=200)

        else:
            hook = WebHook(resource_type="Bad payload",
                action="",
                message=json_data,
                processed=False,
                error="Bad payload")
            hook.save()       
            return http.HttpResponse(status=403)

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

