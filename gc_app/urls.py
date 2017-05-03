#   GO CARDLESS URLs
from django.conf.urls import url
from gc_app.views import *

urlpatterns = [
    url(r'confirm/$',
        GCConfirm.as_view(template_name = "gc_app/success.html"),
        name='gc-success'
    ),
    url(r'webhook/$',
        GCWebhook.as_view(),
        name='gc-webhook'
    ),
    url(r'hook/list/$',
        WebHookList.as_view(),
        name='gc-hook-list'
    ),
    url(r'hook/(?P<pk>\d+)/$',
        WebHookDetailView.as_view(),
        name='gc-hook-detail'
    ),
    url(r'import/$',
        GcImportView.as_view(),
        name='gc-import'
    )
    ]