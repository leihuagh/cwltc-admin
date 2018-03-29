from django.conf.urls import url
from pos.views import *

# POS App URLs

urlpatterns = [
    url(r'^$', AdminView.as_view(), name='pos_admin'),
    url(r'^start/$', StartView.as_view(), name='pos_start'),
    url(r'^start/(?P<layout_id>\d+)/$', StartView.as_view(), name='pos_start_layout'),
    url(r'^start/default$', StartDefaultView.as_view(), name='pos_start_default'),
    url(r'^set_terminal$', SetTerminalView.as_view(), name='pos_set_terminal'),
    url(r'^disabled/$', DisabledView.as_view(), name='pos_disabled'),

    url(r'^user/$', GetUserView.as_view(), name='pos_user'),
    url(r'^password/$', GetPasswordView.as_view(), name='pos_password'),
    url(r'^menu/$', MemberMenuView.as_view(), name='pos_menu'),
    url(r'^menu/timeout/$', MemberMenuView.as_view(timeout=10000), name='pos_menu_timeout'),
    url(r'^run/$', PosView.as_view(), name='pos_run'),
    url(r'^ajax/items/$', ajax_items_view, name='pos_ajax_items'),

    url(r'^register/$', PosRegisterView.as_view(), name='pos_register'),
    url(r'^register/token/(?P<token>.+)/$', PosRegisterTokenView.as_view(), name='pos_register_token'),
    url(r'^consent/token/(?P<token>.+)/$', PosConsentView.as_view(), name='pos_consent_token'),

    url(r'^transactions/$', TransactionListView.as_view(), name='pos_transactions'),
    url(r'^transactions/main/$', TransactionListView.as_view(main_menu=True), name='pos_transactions_main'),
    url(r'^transactions/person/(?P<person_id>\d+)/$', TransactionListView.as_view(),
        name='pos_transactions_person'),
    url(r'^transaction/(?P<pk>\d+)/$', TransactionDetailView.as_view(), name='pos_transaction_detail'),

    url(r'^payments/$', PaymentListView.as_view(), name='pos_payments'),
    url(r'^payments/main$', PaymentListView.as_view(main_menu=True), name='pos_payments_main'),
    url(r'^payments/person/(?P<person_id>\d+)/$', PaymentListView.as_view(), name='pos_payments_main'),

    url(r'^lineitems/$', LineItemListView.as_view(), name='pos_lineitems'),
    url(r'^lineitems/(?P<trans_id>\d+)/$', LineItemListView.as_view(), name='pos_lineitems2'),

    url(r'^item/list/$', ItemListView.as_view(), name='pos_item_list'),
    url(r'^item/(?P<pk>\d+)/$', ItemUpdateView.as_view(), name='pos_item_update'),
    url(r'^item/create/$', ItemCreateView.as_view(), name='pos_item_create'),
    
    url(r'^layout/list/$', LayoutListView.as_view(), name='pos_layout_list'),
    url(r'^layout/(?P<pk>\d+)/$', LayoutUpdateView.as_view(), name='pos_layout_update'),
    url(r'^layout/create/$', LayoutCreateView.as_view(), name='pos_layout_create'),

    url(r'^colour/list/$', ColourListView.as_view(), name='pos_colour_list'),
    url(r'^colour/(?P<pk>\d+)/$', ColourUpdateView.as_view(), name='pos_colour_update'),
    url(r'^colour/create/$', ColourCreateView.as_view(), name='pos_colour_create'),
    ]
