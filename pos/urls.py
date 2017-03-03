from django.conf.urls import url, include
from pos.views import *

urlpatterns = [
    url(r'start/', StartView.as_view(), name='pos-start'),
    url(r'layout/(?P<layout_id>\d+)/$', PosView.as_view(), name='pos-view'),
    url(r'transactions', TransactionListView.as_view(), name='transactions'),
    url(r'lineitems',LineItemListView.as_view(), name='lineitems'),
    url(r'getuser',GetUserView.as_view(), name='get-user')
    ]
