#   GO CARDLESS URLs
from django.conf.urls import url
from .views import *

urlpatterns = [
    url(r'^redirectflow/$', RedirectFlowView.as_view(), name='cardless-redirect-flow'),
    url(r'^mandate/create/(?P<pk>\d+)/$', MandateCreateView.as_view(), name='cardless-mandate-create'),
    url(r'^mandate/success/$', MandateSuccessView.as_view(), name='cardless-mandate-success'),
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