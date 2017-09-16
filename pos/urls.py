from django.conf.urls import url
from pos.views import *

# POS App URLs

urlpatterns = [
    url(r'^$', StartView.as_view(), name='pos-start'),
    url(r'layout/$', PosView.as_view(), name='pos-view'),
    url(r'transactions/$', TransactionListView.as_view(), name='transactions'),
    url(r'transactions/main/$', TransactionListView.as_view(main_menu=True), name='transactions-main'),
    url(r'transactions/person/(?P<person_id>\d+)/$', TransactionListView.as_view(),
        name='transactions-person'),
    url(r'transaction/(?P<pk>\d+)/$', TransactionDetailView.as_view(), name='transaction-detail'),
    url(r'lineitems/$', LineItemListView.as_view(), name='lineitems'),
    url(r'lineitems/(?P<trans_id>\d+)/$', LineItemListView.as_view(), name='lineitems'),
    url(r'getuser/$', GetUserView.as_view(), name='get-user'),
    url(r'menu/$', MemberMenuView.as_view(), name='member-menu')
    ]
