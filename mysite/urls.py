from django.conf.urls import url, include
from django.contrib import admin
from django.contrib.staticfiles.storage import staticfiles_storage
from django_mail_viewer import urls as django_mail_viewer_urls
from django.views.generic.base import RedirectView
from mysite.views import *
from members.views import *
from members.viewsets import UserViewSet, GroupViewSet, InvoiceViewSet
from public.views import *
from members.tables import *
from rest_framework import routers

handler500 = 'mysite.views.custom_500'

admin.autodiscover()

router = routers.DefaultRouter()
router.register(r'Xusers', UserViewSet)
router.register(r'Xgroups', GroupViewSet)
router.register(r'Xinvoices', InvoiceViewSet)

urlpatterns = [
    url(r'^$', index_view, name='index'),
    url(r'^', include('authentication.urls')),
    url(r'^celery/$', test_celery_view, name='celery'),
    url(r'^public/', include('public.urls')),
    url(r'^mv/', include(django_mail_viewer_urls)),
    url(r'^api/', include(router.urls)),
#    url(r'^rest/', include('rest_framework.urls', namespace='rest_framework')),
#    url(r'^report_builder/', include('report_builder.urls')),
    url(r'^pos/', include('pos.urls')),
    url(r'^club/', include('club.urls')),
    url(r'^cardless/', include('cardless.urls')),
    url(r'^wimbledon/', include('wimbledon.urls')),
    url(r'^events/', include('events.urls')),
    url(r'^diary/', include('diary.urls')),
    url(r'^home/',
        HomeView.as_view(),
        name='home'
        ),

    # url(r'^markdownx/', include('markdownx.urls')),
    url(r'^ajax/people/',
        ajax_people,
        name="ajax-people"
        ),
    url(r'^search/person/',
        search_person,
        name="search-person"
        ),

    # YEAR END
    url(r'^yearend/$', YearEndView.as_view(), name='yearend'),
    url(r'^yearend/year$',ChangeYearView.as_view(), name='yearend-year'),


    # GROUPS
    url(r'^group/create/$',
        GroupCreateView.as_view(),
        name='group-create'
        ),
    url(r'^group/(?P<pk>\d+)/$',
        GroupDetailView.as_view(),
        name='group-detail'
        ),
    url(r'^group/(?P<slug>[\w-]+)/$',
        GroupDetailView.as_view(),
        name='group-detail'
        ),
    url(r'^groups/$',
        GroupListView.as_view(),
        name='group-list'
        ),
    url(r'^groups/addperson/(?P<person_id>\d+)/$',
        GroupAddPersonView.as_view(),
        name='group-add-person'
        ),
    url(r'^groups/addlist/$',
        GroupAddListView.as_view(),
        name='group-add-list'),

    #   MEMBERSHIP CATEGORIES
    url(r'^categories/list/$',
        MembershipTableView.as_view(),
        name='categories-list'
        ),
    #   FEES
    url(r'^fees/update/(?P<pk>\d+)/$',
        FeesUpdateView.as_view(),
        name='fees-update'
        ),
    url(r'^fees/list/$',
        FeesListView.as_view(),
        name='fees-list'
        ),
    url(r'^fees/list/(?P<year>[0-9]{4})/$',
        FeesListView.as_view(),
        name='fees-list'
        ),

    #   SUBSCRIPTIONS
    url(r'^sub/update/(?P<pk>\d+)/$',
        SubUpdateView.as_view(),
        name='sub-update'
        ),
    url(r'^sub/correct/(?P<pk>\d+)/$',
        SubCorrectView.as_view(),
        name='sub-correct'
        ),
    url(r'^sub/create/(?P<person_id>\d+)/$',
        SubCreateView.as_view(),
        name='sub-create'
        ),
    url(r'^sub/(?P<pk>\d+)/$',
        SubDetailView.as_view(),
        name='sub-detail'
        ),
    url(r'^sub/renew/all$',
        SubRenewAllView.as_view(),
        name='sub-renew-all'
        ),
    url(r'^sub/renew/list$',
        SubRenewSelectionView.as_view(),
        name='sub-renew-list'
        ),
    url(r'^sub/history/(?P<person_id>\d+)/$',
        SubHistoryView.as_view(),
        name='sub-history'
        ),

    #   INVOICES (excludes public invoice view)
    url(r'^sub/invoicecancel/(?P<pk>\d+)/$',
        SubInvoiceCancel.as_view(),
        name='sub-invoice-cancel'
        ),
    url(r'^invoices/$',
        InvoiceTableView.as_view(),
        name='invoice-list'
        ),
    url(r'^invoice/(?P<pk>\d+)/$',
        InvoiceDetailView.as_view(),
        name='invoice-detail'
        ),
    # This url temporarily retained for compatibility with pre 2018 invoices
    # now replaced by public-invoice-token in public app
    url(r'^invoice/public/(?P<token>.+)/$',
        InvoicePublicView.as_view(),
        name='invoice-public'
        ),
    url(r'^invoice/generate/(?P<pk>\d+)/$',
        InvoiceGenerateView.as_view(),
        name='invoice-generate'
        ),
    url(r'^invoices/generate/$',
        InvoicesGenerateSelectionView.as_view(),
        name='invoices-generate'
        ),
    url(r'^invoice/mail/(?P<pk>\d+)/(?P<option>[a-zA-Z]+)$',
        InvoiceMailView.as_view(),
        name='invoice-mail'
        ),
    url(r'^invoice/mail/config/(?P<pk>\d+)/$',
        InvoiceMailConfigView.as_view(),
        name='invoice-mail-config'
        ),
    url(r'^invoice/mail/batch(?:/(?P<send>\d+))?/$',
        InvoiceMailBatchView.as_view(),
        name='invoice-mail-batch'
        ),
    url(r'^select$',
        InvoiceSelectView.as_view(),
        name='select'
        ),
    url(r'^invoice/batch$',
        InvoiceBatchView.as_view(),
        name='invoice-batch'
        ),

    #   PAYMENTS

    url(r'^payment/list/$',
        PaymentListView.as_view(),
        name='payment-list'
        ),
    url(r'^payment/invoice/(?P<invoice_id>\d+)/$',
        PaymentCreateView.as_view(),
        name='payment-invoice'
        ),
    url(r'^payment/(?P<pk>\d+)/$',
        PaymentDetailView.as_view(),
        name='payment-detail'
        ),
    url(r'^payment/update/(?P<pk>\d+)/$',
        PaymentUpdateView.as_view(),
        name='payment-update'
        ),

    #   CREDIT NOTES
    url(r'^creditnote/create/(?P<person_id>\d+)/$',
        CreditNoteCreateView.as_view(),
        name='creditnote-create'
        ),
    url(r'^creditnote/(?P<pk>\d+)/$',
        CreditNoteDetailView.as_view(),
        name='creditnote-update'
        ),

    #   PEOPLE

    url(r'^people/members/$', SubsTableView.as_view(
        table_class=SubsTable,
        model=Subscription,
        members=True,
        filter_class=SubsFilter,
    ),
        name='members-list'),

    url(r'^people/juniors/$', SubsTableView.as_view(
        table_class=SubsTable,
        model=Subscription,
        juniors=True,
        filter_class=JuniorFilter,
    ),
        name='juniors-list'),

    url(r'^people/parents/$', SubsTableView.as_view(
        table_class=PersonTable,
        model=Person,
        parents=True,
        filter_class=JuniorFilter,
    ),
        name='parents-list'
        ),
    url(r'^people/all/$', SubsTableView.as_view(
        table_class=PersonTable,
        model=Person,
    ),
        name='all-people-list'
        ),
    url(r'^people/applied/$', AppliedTableView.as_view(),
        name='applied-list'),

    # url(r'^list/$',
    #     PersonList.as_view(),
    #     name='person-list'
    #     ),
    url(r'^(?P<pk>\d+)/$',
        PersonDetailView.as_view(),
        name='person-detail'
        ),
    url(r'^person/create(?:/(?P<link>\d+))?/$',
        PersonCreateView.as_view(),
        name='person-create'
        ),
    url(r'^person/update/(?P<pk>\d+)/$',
        PersonUpdateView.as_view(),
        name='person-edit'
        ),
    url(r'^person/merge/(?P<pk>\d+)/$',
        PersonMergeView.as_view(),
        name='person-merge'
        ),
    url(r'^person/link/(?P<pk>\d+)/$',
        PersonLinkView.as_view(),
        name='person-link'
        ),
    url(r'^junior/create$',
        JuniorCreateView.as_view(),
        name='junior-create'
        ),

    url(r'^person/export$',
        PersonExportView.as_view(),
        name='person-export'
        ),

    url(r'^person/profile/(?P<pk>\d+)$',
        AdultProfileView.as_view(edit=False),
        name='person-profile'
        ),

    url(r'^person/profile/edit/(?P<pk>\d+)$',
        AdultProfileView.as_view(edit=True),
        name='person-profile-edit'
        ),

    url(r'^junior/profile/(?P<pk>\d+)$',
        JuniorProfileView.as_view(edit=False),
        name='junior-profile'
        ),

    url(r'^junior/profile/edit/(?P<pk>\d+)$',
        JuniorProfileView.as_view(edit=True),
        name='junior-profile-edit'
        ),

    #   ADDRESSES
    url(r'^person/address/(?P<person_id>\d+)/$',
        AddressUpdateView.as_view(),
        name='person-address'
        ),

    #   INVOICE ITEMS
    url(r'^items/(?P<pk>\d+)/$',
        InvoiceItemListView.as_view(),
        name='item-list'
        ),
    url(r'^item/create/(?P<person_id>\d+)/$',
        InvoiceItemCreateView.as_view(),
        name='item-create'
        ),
    url(r'^item/update/(?P<pk>\d+)/$',
        InvoiceItemUpdateView.as_view(),
        name='item-update'
        ),
    url(r'^item/(?P<pk>\d+)/$',
        InvoiceItemDetailView.as_view(),
        name='item-detail'
        ),
    url(r'^item/table/$',
        InvoiceItemTableView.as_view(),
        name='item-table'
        ),

    # TEXTBLOCK
    url(r'^text/create/$',
        TextBlockCreateView.as_view(),
        name='text-create'
        ),
    url(r'^text/(?P<pk>\d+)/$',
        TextBlockUpdateView.as_view(),
        name='text-update'
        ),
    url(r'^text/list/$',
        TextBlockListView.as_view(),
        name='text-list'
        ),

    # EMAIL
    url(r'^email/$',
        EmailView.as_view(),
        name='email'
        ),
    url(r'^email/selection/$',
        EmailView.as_view(selection=True),
        name='email-selection'
        ),
    url(r'^email/person/(?P<person>\d+)/$',
        EmailView.as_view(),
        name='email-person'
        ),
    url(r'^email/group/(?P<group>\d+)/$',
        EmailView.as_view(),
        name='email-group'
        ),
    url(r'^email/campaign/(?P<campaign>\d+)/$',
        EmailView.as_view(),
        name='email-campaign'
        ),

    # MAIL TYPES

    url(r'^mailtype/create/$',
        MailTypeCreateView.as_view(),
        name='mailtype-create'
        ),
    url(r'^mailtype/update/(?P<pk>\d+)/$',
        MailTypeUpdateView.as_view(),
        name='mailtype-update'
        ),
    url(r'^mailtype/(?P<pk>\d+)/$',
        MailTypeDetailView.as_view(),
        name='mailtype-detail'
        ),
    url(r'^mailtype/list/$',
        MailTypeListView.as_view(),
        name='mailtype-list'
        ),
    url(r'^mailtype/public/subscribe/(?P<token>.+)/$',
        MailTypeSubscribeView.as_view(),
        name='mailtype-subscribe-public'
        ),
    url(r'^mailtype/subscribe/(?P<person>\d+)/$',
        MailTypeSubscribeView.as_view(),
        name='mailtype-subscribe'
        ),

    # CAMPAIGNS

    url(r'^mailcampaign/create/$',
        MailCampaignCreateView.as_view(),
        name='mail-campaign-create'
        ),
    url(r'^mailcampaign/bee/(?P<pk>\d+)/$',
        MailCampaignBeeView.as_view(),
        name='mail-campaign-bee'
        ),
    url(r'^MailCampaign/update/(?P<pk>\d+)/$',
        MailCampaignUpdateView.as_view(),
        name='mail-campaign-update'
        ),
    # url(r'^mailcampaign/(?P<pk>\d+)/$',
    #    MailCampaignDetailView.as_view(),
    #    name='mail-campaign-detail'
    # ),
    url(r'^mailcampaign/list/$',
        MailCampaignListView.as_view(),
        name='mail-campaign-list'
        ),

    # EXCEL IMPORT AND EXPORT
    url(r'^import/$',
        ImportExcelView.as_view(),
        name='import'
        ),
    # url(r'^import1/(?P<pass>\d+)/(?P<start>\d+)/(?P<size>\d+)/$',
    #     ImportExcelMore.as_view(),
    #     name='import_more'
    #     ),
    url(r'^select/sheets$',
        SelectSheets.as_view(),
        name='select-sheets'
        ),

    url(r'^export/$',
        export,
        name='export'
        ),
    url(r'^export/(?P<option>\w+)/$',
        PersonExportView.as_view(),
        name='export-option'
        ),
    # url(r'^reports/$',
    #     reports,
    #     name='reports'
    #     ),
    url(r'^bee/$',
        bee_test,
        name='bee'
        ),

    url(r'^admin/', admin.site.urls),
    url(r'^favicon.ico/$', RedirectView.as_view(url=staticfiles_storage.url('favicons/favicon.ico'))),
    url(r'^apple-touch-icon.png/$', RedirectView.as_view(url=staticfiles_storage.url('apple-touch-icon.png'))),
]

if settings.DEBUG:
    import debug_toolbar

    urlpatterns += [
        url(r'^__debug__/', include(debug_toolbar.urls)),
    ]
