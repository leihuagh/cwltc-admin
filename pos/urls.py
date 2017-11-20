from django.conf.urls import url
from pos.views import *

# POS App URLs

urlpatterns = [
    url(r'^$', LoadView.as_view(), name='pos_load'),
    url(r'start/$', StartView.as_view(), name='pos_start'),
    url(r'run/$', PosView.as_view(), name='pos_run'),
    url(r'transactions/$', TransactionListView.as_view(), name='pos_transactions'),
    url(r'transactions/main/$', TransactionListView.as_view(main_menu=True), name='pos_transactions_main'),
    url(r'transactions/person/(?P<person_id>\d+)/$', TransactionListView.as_view(),
        name='pos_transactions_person'),
    url(r'transaction/(?P<pk>\d+)/$', TransactionDetailView.as_view(), name='pos_transaction_detail'),
    url(r'lineitems/$', LineItemListView.as_view(), name='pos_lineitems'),
    url(r'lineitems/(?P<trans_id>\d+)/$', LineItemListView.as_view(), name='pos_lineitems'),
    url(r'user/$', GetUserView.as_view(), name='pos_user'),
    url(r'menu/$', MemberMenuView.as_view(), name='pos_member_menu'),
    url(r'item/list/$', ItemListView.as_view(), name='pos_item_list'),
    url(r'item/(?P<pk>\d+)/$', ItemUpdateView.as_view(), name='pos_item_update'),
    url(r'item/create/$', ItemCreateView.as_view(), name='pos_item_create'),
    url(r'layout/list/$', LayoutListView.as_view(), name='pos_layout_list'),
    url(r'layout/(?P<pk>\d+)/$', LayoutUpdateView.as_view(), name='pos_layout_update'),
    url(r'layout/create/$', LayoutCreateView.as_view(), name='pos_layout_create'),
    ]
