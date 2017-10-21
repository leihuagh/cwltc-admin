#   GO CARDLESS URLs
from django.conf.urls import url
from .views import *

urlpatterns = [
    url(r'^redirectflow/$', RedirectFlowView.as_view(), name='cardless_redirect_flow'),
    url(r'^mandate/create/i/(?P<invoice_token>.+)/$', MandateCreateView.as_view(), name='cardless_mandate_create_i'),
    url(r'^mandate/create/p/(?P<person_token>.+)/$', MandateCreateView.as_view(), name='cardless_mandate_create_p'),
    url(r'^mandate/create/pi/(?P<person_token>.+)/(?P<invoice_token>.+)/$', MandateCreateView.as_view(),
        name='cardless_mandate_create_pi'),
    url(r'^mandate/success/(?P<invoice_token>.+)/$', MandateSuccessView.as_view(), name='cardless_mandate_success'),
    url(r'^mandate/list/(?P<person_id>\d+)/$', MandateListView.as_view(), name='cardless_mandate_person_list'),
    url(r'^mandate/list/$', MandateListView.as_view(), name='cardless_mandate_list'),
    url(r'^mandate/gc/list/$', MandateGcListView.as_view(), name='cardless_mandate_gc_list'),
    url(r'^mandate/detail/(?P<mandate_id>.+)/$', MandateDetailView.as_view(), name='cardless_mandate_detail'),
    url(r'^customer/detail/(?P<customer_id>.+)/$', CustomerDetailView.as_view(), name='cardless_customer_detail'),
    url(r'^event/detail/(?P<event_id>.+)/$', EventDetailView.as_view(), name='cardless_event_detail'),
    url(r'^payment/create/(?P<invoice_token>.+)/$', PaymentCreateView.as_view(), name='cardless_payment_create'),
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