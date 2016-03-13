# Go cardless views
import gocardless
from django.views.generic import View, RedirectView, TemplateView
from django import http
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.conf import settings
from members.models import Invoice


import json
import logging
logger =logging.getLogger(__name__)

# Read settings from setting.py and initialise go cardless api
GO_CARDLESS=getattr(settings, 'GO_CARDLESS')

gocardless.set_details(app_id=GO_CARDLESS['APP_ID'],
        app_secret=GO_CARDLESS['APP_SECRET'],
        access_token=GO_CARDLESS['ACCESS_TOKEN'],
        merchant_id=GO_CARDLESS['MERCHANT_ID'])

gocardless.environment = GO_CARDLESS['ENVIRONMENT']

    
def gc_create_bill_url(invoice):
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
            if data['resource_type'] == 'subscription':
                if data['action'] == 'cancelled':
                    for subscription in data['subscriptions']:
                        # Lookup the subscription using subscription['resource_id']
                        # Perform logic to cancel the subscription
                        # Any time-consuming jobs should be performed asynchronously
                        print("Subscription {0} cancelled".format(subscription['id']))
                elif data['action'] == 'expired':
                    pass
                return http.HttpResponse(status=200)

            elif data['resource_type'] == 'bill':
                logger.debug("Bill webhook")
                for bill in data['bills']:
                    try:
                        bill_id = pk=bill['resource_id']
                        invoice = Invoice.objects.get(gocardless_bill_id=bill_id)
                    except:
                        logger.debug("Invoice {} not found".format(bill_id))
                        return http.HttpResponse(status=403)
                    if invoice.process_cardless(data['action'],
                                                bill['amount'],
                                                bill['amount_minus_fees']
                                                ):
                        return http.HttpResponse(status=200)                  

            elif data['resource_type'] == 'pre_authorization':
                if data['action'] == 'cancelled':
                    pass
                elif data['action'] == 'expired':
                    pass
                
        return http.HttpResponse(status=403)



