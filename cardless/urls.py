#   GO CARDLESS URLs
from django.conf.urls import url
from .views import RedirectFlowView

urlpatterns = [
    url(r'redirectflow/$', RedirectFlowView.as_view(), name='cardless-redirect-flow'),
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