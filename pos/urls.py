from django.conf.urls import url, include
from pos.views import PosView, StartView

urlpatterns = [
    url(r'start/', StartView.as_view(), name='pos-start'),
    url(r'pos/(?P<layout_id>\d+)/$', PosView.as_view(), name='pos-view')
    ]
