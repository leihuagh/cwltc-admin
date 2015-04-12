"""
Definition of urls for Cwltc.
"""

from datetime import datetime
from django.conf.urls import patterns, url
from members.forms import BootstrapAuthenticationForm
from members.views import *


# Uncomment the next lines to enable the admin:
from django.conf.urls import include
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    url(
        r'^$',
        'members.views.home',
        name='home'
    ),
    url(
        r'^fixup$',
        'members.views.fixup',
        name='test'
    ),

    #   SUBSCRIPTIONS
    url(
        r'^sub/update/(?P<pk>\d+)/',
        SubUpdateView.as_view(),
        name='sub-update'
    ),
    url(
        r'^sub/create/(?P<person_id>\d+)/',
        SubCreateView.as_view(),
        name='sub-create'
    ),
    url(
        r'^sub/(?P<pk>\d+)/',
        SubDetailView.as_view(),
        name='sub-detail'
    ),
    url(
        r'^sub/renew/(?P<pk>\d+)/',
        SubRenewView.as_view(),
        name='sub-renew'
    ),
    url(
        r'^sub/renewbatch$',
        SubRenewBatch.as_view(),
        name='sub-renew-batch'
    ),

    #   INVOICES
    url(
        r'^sub/invoicecancel/(?P<pk>\d+)/',
        SubInvoiceCancel.as_view(),
        name='sub-invoice-cancel'
    ),
   
    url(
        r'^invoices/(?P<option>[a-zA-Z]+)$',
        InvoiceListView.as_view(),
        name='invoice-list'
    ),
    url(
        r'^invoice/(?P<pk>\d+)/',
        InvoiceDetailView.as_view(),
        name='invoice-detail'
    ),
    url(
        r'^invoice/generate/(?P<pk>\d+)/',
        InvoiceGenerateView.as_view(),
        name='invoice-generate'
    ),
    url(
        r'^invoice/cancel/(?P<pk>\d+)/',
        InvoiceCancelView.as_view(),
        name='invoice-cancel'
    ),
    url(
        r'^invoice/mail/(?P<pk>\d+)/(?P<option>[a-zA-Z]+)$',
        InvoiceMailView.as_view(),
        name='invoice-mail'
    ),
    url(
        r'^invoice/mail/batch$',
        InvoiceMailBatchView.as_view(),
        name='invoice-mail-batch'
    ),
    url(
        r'^select$',
        InvoiceSelectView.as_view(),
        name='select'
    ),
    url(
        r'^invoice/batch$',
        InvoiceBatchView.as_view(),
        name='invoice-batch'
    ),
    url(
        r'^invoice/delete/(?P<pk>\d+)/',
        InvoiceDeleteView.as_view(),
        name='invoice-delete'
    ),

    #   PAYMENTS
    url(
        r'^payment/invoice/(?P<invoice_id>\d+)/',
        PaymentCreateView.as_view(),
        name='payment-invoice'
    ),
    url(
        r'^payment/(?P<pk>\d+)/',
        PaymentDetailView.as_view(),
        name='payment-detail'
    ),


    url(
        r'^list$',
       PersonList.as_view(),
       name='person-list'
    ),
    url(
       r'^list/(?P<tags>[\w\+]+)/',
       FilteredPersonList.as_view(),
       name='filteredperson-list'
    ),
    url(
        r'^filter$',
       FilterMemberView.as_view(),
       name='filter'
    ),
    url(
        r'^(?P<pk>\d+)/$',
       PersonDetailView.as_view(),
       name='person-detail'
    ),
    url(
        r'^person/create$',
       PersonCreateView.as_view(),
       name='person-create'
    ),
    url(
        r'^person/unlink/(?P<pk>\d+)/',
       PersonUnlinkView.as_view(),
       name='person-unlink'
    ),
    url(
        r'^junior/create$',
       JuniorCreateView.as_view(),
       name='junior-create'
    ),
    url(
        r'^edit/(?P<pk>\d+)/$',
       PersonUpdateView.as_view(),
       name='person-edit'
    ),
    url(
        r'^person/export$',
       PersonExportView.as_view(),
       name='person-export'
    ),

        #   INVOICE ITEMS
    url(
        r'^items/(?P<pk>\d+)/$',
        InvoiceItemListView.as_view(),
        name='item-list'
    ),
    url(
        r'^item/create/(?P<person_id>\d+)/$',
        InvoiceItemCreateView.as_view(),
        name='item-create'
    ),
    url(
        r'^item/update/(?P<pk>\d+)/$',
        InvoiceItemUpdateView.as_view(),
        name='item-update'
    ),
    url(
        r'^item/(?P<pk>\d+)/$',
        InvoiceItemDetailView.as_view(),
        name='item-detail'
    ),
    # TEXTBLOCK
    url(
        r'^text/create/$',
        TextBlockCreateView.as_view(),
        name='text-create'
    ),
    url(
        r'^text/(?P<pk>\d+)/$',
        TextBlockUpdateView.as_view(),
        name='text-update'
    ),
    url(
        r'^text/list/$',
        TextBlockListView.as_view(),
        name='text-list'
    ),

    # EXCEL IMPORT

    url(
        r'^import$',
        ImportExcelView.as_view(),
        name='import'
    ),
        url(
        r'^import1/(?P<pass>\d+)/(?P<start>\d+)/(?P<size>\d+)/$',
        ImportExcelMore.as_view(),
        name='import_more'
    ),
        url(
        r'^select/sheets$',
        SelectSheets.as_view(),
        name='select-sheets'
    ),

    url(
        r'^export$',
        'members.views.export',
        name='export'
    ),
    url(
        r'^testinv$',
        'members.views.testinv',
        name='test'
    ),
    url(
        r'^bar$',
       'members.views.bar',
       name='bar-view'
    ),
    url(
        r'^contact$',
        'members.views.contact',
        name='contact'
    ),
    url(
        r'^about',
        'members.views.about',
        name='about'
    ),
    url(
        r'^login/$',
        'django.contrib.auth.views.login',
        {
            'template_name': 'members/login.html',
            'authentication_form': BootstrapAuthenticationForm,
            'extra_context':
            {
                'title':'Log in',
                'year':datetime.now().year,
            }
        },
        name='login'),
    url(r'^logout$',
        'django.contrib.auth.views.logout',
        {
            'next_page': '/',
        },
        name='logout'),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    url(
        r'^admin/',
        include(admin.site.urls)
    ),
    
)
