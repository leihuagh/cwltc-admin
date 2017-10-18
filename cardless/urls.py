#   GO CARDLESS URLs
from django.conf.urls import url
from .views import *

urlpatterns = [
    url(r'^redirectflow/$', RedirectFlowView.as_view(), name='cardless_redirect_flow'),
    url(r'^mandate/create/(?P<invoice_token>.+)/$', MandateCreateView.as_view(), name='cardless_mandate_create'),
    url(r'^mandate/create/(?P<person_token>.+)/$', MandateCreateView.as_view(), name='cardless_mandate_person_create'),
    url(r'^mandate/success/(?P<invoice_token>.+)/$', MandateSuccessView.as_view(), name='cardless_mandate_success'),
    url(r'^payment/create/(?P<token>.+)/$', PaymentCreateView.as_view(), name='cardless_payment_create'),
    url(r'^payment/success/$', PaymentCreateView.as_view(), name='cardless_payment_success')
    # url(r'webhook/$',
    #     GCWebhook.as_view(),
    #     name='gc-webhook'
    # ),
    # url(r'hook/list/$',
    #     WebHookList.as_view(),
    #     name='gc-hook-list'
    # ),
    # url(r'hook/(?P<pk>\d+)/$',
    #     WebHookDetailView.as_view(),
    #     name='gc-hook-detail'
    # ),
    # url(r'import/$',
    #     GcImportView.as_view(),
    #     name='gc-import'
    # )
    ]