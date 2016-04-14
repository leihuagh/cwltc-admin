"""
Definition of urls for Cwltc.
"""

from datetime import datetime
from django.conf.urls import url
from django.views.generic import TemplateView
from members.forms import BootstrapAuthenticationForm
from members.views import *
from gc_app.views import *

# Uncomment the next lines to enable the admin:
from django.conf.urls import include
from django.contrib import admin
from django.contrib.auth.views import *
admin.autodiscover()

urlpatterns = [
    url(
        r'^$',
        HomeView.as_view(),
        name='home'
    ),
    url(
        r'^yearend/$',
        YearEndView.as_view(),
        name='year-end'
    ),
    # GROUPS
    url(
        r'^group/create/$',
        GroupCreateView.as_view(),
        name='group-create'
    ),
    url(
        r'^group/(?P<slug>[\w-]+)/$',
        GroupDetailView.as_view(),
        name='group-detail'
    ),
    url(
        r'^groups/$',
        GroupListView.as_view(),
        name='group-list'
    ),
    url(
        r'^groups/addperson/(?P<person_id>\d+)$',
        GroupAddPersonView.as_view(),
        name='group-add-person'
    ),
    #   GO CARDLESS
    url(r'^gocardless/confirm/$',
        GCConfirm.as_view(template_name = "gc_app/success.html"),
        name='gc_success'
    ),
    url(r'^gocardless/webhook/$',
        GCWebhook.as_view(),
        name='gc_webhook'
    ),
    url(r'^webhook/list/$',
        WebHookList.as_view(),
        name='webhook-list'
    ),
    url(r'^webhook/(?P<pk>\d+)/$',
        WebHookDetailView.as_view(),
        name='webhook-detail'
    ),
    url(r'^resigned/$',
        ResignedView.as_view(),
        name='resigned'
    ),
    #   FEES
    url(
        r'^fees/update/(?P<pk>\d+)/$',
        FeesUpdateView.as_view(),
        name='fees-update'
    ),
    url(
        r'^fees/list/$',
        FeesListView.as_view(),
        name='fees-list'
    ),
    url(
        r'^fees/list/(?P<year>[0-9]{4})/$',
        FeesListView.as_view(),
        name='fees-list'
    ),
    #   SUBSCRIPTIONS
    url(
        r'^sub/update/(?P<pk>\d+)/$',
        SubUpdateView.as_view(),
        name='sub-update'
    ),
    url(
        r'^sub/correct/(?P<pk>\d+)/$',
        SubCorrectView.as_view(),
        name='sub-correct'
    ),
    url(
        r'^sub/create/(?P<person_id>\d+)/$',
        SubCreateView.as_view(),
        name='sub-create'
    ),
    url(
        r'^sub/(?P<pk>\d+)/$',
        SubDetailView.as_view(),
        name='sub-detail'
    ),
    url(
        r'^sub/renew/(?P<pk>\d+)/$',
        SubRenewView.as_view(),
        name='sub-renew'
    ),
    url(
        r'^sub/renewbatch$',
        SubRenewBatch.as_view(),
        name='sub-renew-batch'
    ),
    url(
        r'^sub/renew/all$',
        SubRenewAllView.as_view(),
        name='sub-renew-all'
    ),
    url(
        r'^sub/history/(?P<person_id>\d+)/$',
        SubListView.as_view(),
        name='sub-history'
    ),

    #   INVOICES
    url(
        r'^sub/invoicecancel/(?P<pk>\d+)/$',
        SubInvoiceCancel.as_view(),
        name='sub-invoice-cancel'
    ),
    url(
        r'^invoices/$',
        InvoiceListView.as_view(),
        name='invoice-list'
    ),
    url(
        r'^invoice/(?P<pk>\d+)/$',
        InvoiceDetailView.as_view(),
        name='invoice-detail'
    ),
    url(
        r'^invoice/public/(?P<token>.+)/$',
        InvoicePublicView.as_view(),
        name='invoice-public'
    ),
    url(
        r'^invoice/generate/(?P<pk>\d+)/$',
        InvoiceGenerateView.as_view(),
        name='invoice-generate'
    ),
    url(
        r'^invoice/cancel/(?P<pk>\d+)/$',
        InvoiceCancelView.as_view(),
        name='invoice-cancel'
    ),
    url(
        r'^invoice/mail/(?P<pk>\d+)/(?P<option>[a-zA-Z]+)$',
        InvoiceMailView.as_view(),
        name='invoice-mail'
    ),
    url(
        r'^invoice/mail/config/(?P<pk>\d+)/$',
        InvoiceMailConfigView.as_view(),
        name='invoice-mail-config'
    ),
    url(
        r'^invoice/mail/batch(?:/(?P<send>\d+))?/$',
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
        r'^invoice/delete/(?P<pk>\d+)/$',
        InvoiceDeleteView.as_view(),
        name='invoice-delete'
    ),

    #   PAYMENTS

    url(
        r'^payment/list/$',
        PaymentListView.as_view(),
        name='payment-list'
    ),
    url(
        r'^payment/invoice/(?P<invoice_id>\d+)/$',
        PaymentCreateView.as_view(),
        name='payment-invoice'
    ),
    url(
        r'^payment/(?P<pk>\d+)/$',
        PaymentDetailView.as_view(),
        name='payment-detail'
    ),

    #   CREDIT NOTES

    url(
        r'^creditnote/create/(?P<person_id>\d+)/$',
        CreditNoteCreateView.as_view(),
        name='creditnote-create'
    ),
    url(
        r'^creditnote/(?P<cnote_id>\d+)/$',
        CreditNoteCreateView.as_view(),
        name='creditnote-detail'
    ),

    #   PEOPLE

    url(
        r'^list$',
       PersonList.as_view(),
       name='person-list'
    ),
    url(
       r'^people/$',
       FilteredPersonListAjax.as_view(),
       name='filteredperson-list'
    ),
    url(
       r'^people/(?P<tags>[\w\+]+)/$',
       FilteredPersonListAjax.as_view(),
       name='filteredperson-list-tags'
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
        r'^person/create(?:/(?P<link>\d+))?/$',
       PersonCreateView.as_view(),
       name='person-create'
    ),
    url(
        r'^person/update/(?P<pk>\d+)/$',
       PersonUpdateView.as_view(),
       name='person-edit'
    ),
    url(
        r'^person/unlink/(?P<pk>\d+)/$',
       PersonUnlinkView.as_view(),
       name='person-unlink'
    ),
    url(
        r'^person/link/(?P<pk>\d+)/$',
       PersonLinkView.as_view(),
       name='person-link'
    ),
    url(
        r'^junior/create$',
       JuniorCreateView.as_view(),
       name='junior-create'
    ),

    url(
        r'^person/export$',
       PersonExportView.as_view(),
       name='person-export'
    ),
    
    #   ADDRESSES

    url(
        r'^person/address/(?P<person_id>\d+)/$',
       AddressUpdateView.as_view(),
       name='person-address'
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
        r'^text/(?P<pk>\d+)(?:/(?P<option>[a-z]+))?/$',
        TextBlockUpdateView.as_view(),
        name='text-update'
    ),
    url(
        r'^text/list/$',
        TextBlockListView.as_view(),
        name='text-list'
    ),

    # EXCEL IMPORT AND EXPORT

    url(
        r'^import/$',
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
        r'^export/$',
        export,
        name='export'
    ),
    url(
        r'^export/(?P<option>\w+)/$',
        PersonExportView.as_view(),
        name='export-option'
    ),
    url(
        r'^import_backup$',
        import_backup,
        name='import-backup'
    ),
    url(
        r'^bar$',
       bar,
       name='bar-view'
    ),
    url(
        r'^contact$',
        contact,
        name='contact'
    ),
    url(
        r'^login/$',
        login,
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
        logout,
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
    
]
