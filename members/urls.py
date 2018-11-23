from django.urls import path

from public.views import AdultProfileView, JuniorProfileView

from members.views.ajax_views import ajax_people, ajax_person, ajax_adults, ajax_password, ajax_postcode, \
    ajax_dob, ajax_chart, ajax_set_pin
from members.views.person_views import PersonDetailView, PersonCreateView, PersonUpdateView, PersonMergeView, \
    PersonLinkView, JuniorCreateView, AddressUpdateView
from members.views.people_views import MembersTableView, JuniorsTableView, ParentsTableView, AllPeopleTableView, \
    GroupPeopleTableView, AppliedTableView, ResignView
from members.views.group_views import GroupAddPersonView, GroupCreateView, GroupTableView
from members.views.membership_views import MembershipCreateView, MembershipUpdateView, MembershipTableView
from members.views.fees_views import FeesCreateView, FeesUpdateView, FeesListView, VisitorFeesUpdateView, \
    VisitorFeesListView
from members.views.sub_views import SubCreateView, SubUpdateView, SubCorrectView, SubDetailView, SubHistoryView, \
    SubRenewAllView, SubRenewSelectionView
from members.views.invoiceitem_views import InvoiceItemCreateView, InvoiceItemUpdateView, InvoiceItemDetailView, \
    InvoiceItemListView, InvoiceItemTableView
from members.views.invoice_views import \
    InvoiceGenerateSelectionView, InvoiceTableView, InvoiceDetailView, InvoiceSelectView, InvoiceMailView, \
    InvoiceMailConfigView, InvoiceMailBatchView, InvoiceDeleteView, InvoicePublicView, InvoiceBatchView
from members.views.payment_views import PaymentCreateView, PaymentUpdateView, PaymentDetailView, PaymentListView, \
    CreditNoteCreateView, CreditNoteDetailView
from members.views.email_views import EmailView, EmailSelectionView, \
    TextBlockCreateView, TextBlockUpdateView, TextBlockListView, \
    MailTypeCreateView, MailTypeUpdateView, MailTypeDetailView, MailTypeListView, MailTypeSubscribeView
from members.views.billing_views import BillingView, YearEndView
from members.views.charts_views import ChartMembers

ajax_patterns = [
    path('people/', ajax_people, name='ajax-people'),
    path('person/', ajax_person, name='ajax-person'),
    path('adults/', ajax_adults, name='ajax-adults'),
    path('password/', ajax_password, name='ajax-password'),
    path('postcode/', ajax_postcode, name='ajax-postcode'),
    path('dob/', ajax_dob, name='ajax-dob'),
    path('set_pin/', ajax_set_pin, name='ajax-set-pin'),
    path('chart/', ajax_chart, name='ajax-chart-members', ),
]
person_patterns = [
    path('create/', PersonCreateView.as_view(), name='person-create'),
    path('junior/create/', JuniorCreateView.as_view(), name='person-junior-create'),
    path('create/<int:link>/', PersonCreateView.as_view(), name='person-create-link'),
    path('update/<int:pk>/', PersonUpdateView.as_view(), name='person-update'),
    path('detail/<int:pk>/', PersonDetailView.as_view(), name='person-detail'),
    path('merge/<int:pk>/', PersonMergeView.as_view(), name='person-merge'),
    path('link/<int:pk>/', PersonLinkView.as_view(), name='person-link'),
    path('address/<int:person_id>', AddressUpdateView.as_view(), name='person-address'),

    path('profile/<int:pk>/', AdultProfileView.as_view(edit=False), name='person-profile'),
    path('profile/edit/<int:pk>/', AdultProfileView.as_view(edit=True), name='person-profile-edit'),
    path('junior/profile/<int:pk>/', JuniorProfileView.as_view(edit=False), name='junior-profile'),
    path('junior/profile/edit/<int:pk>/', JuniorProfileView.as_view(edit=True), name='junior-profile-edit'),
]
people_patterns = [
    path('members/', MembersTableView.as_view(), name='members-list'),
    path('juniors/', JuniorsTableView.as_view(), name='juniors-list'),
    path('parents/', ParentsTableView.as_view(), name='parents-list'),
    path('all/', AllPeopleTableView.as_view(), name='all-people-list'),
    path('applied/', AppliedTableView.as_view(), name='applied-list'),
    path('resigned/', ResignView.as_view(), name='people-resign'),
]
group_patterns = [
    path('create/', GroupCreateView.as_view(), name='group-create'),
    path('detail/<int:pk>/', GroupPeopleTableView.as_view(), name='group-detail'),
    path('list/', GroupTableView.as_view(), name='group-list'),
    path('add/person/<int:person_id>/', GroupAddPersonView.as_view(), name='group-add-person'),
]
membership_patterns = [
    path('create/', MembershipCreateView.as_view(), name='membership-create'),
    path('update/<int:pk>', MembershipUpdateView.as_view(), name='membership-update'),
    path('list/', MembershipTableView.as_view(), name='membership-list'),
]
fees_patterns = [
    path('create/', FeesCreateView.as_view(), name='fees-create'),
    path('update/<int:pk>/', FeesUpdateView.as_view(), name='fees-update'),
    path('list/', FeesListView.as_view(), name='fees-list'),
    path('list/<int:year>/', FeesListView.as_view(), name='fees-list-year'),
    path('visitor/update/<int:pk>/', VisitorFeesUpdateView.as_view(), name='visitor-fees-update'),
    path('visitor/list/', VisitorFeesListView.as_view(), name='visitor-fees-list'),
]
sub_patterns = [
    path('create/<int:person_id>/', SubCreateView.as_view(), name='sub-create'),
    path('update/<int:pk>/', SubUpdateView.as_view(), name='sub-update'),
    path('correct/<int:pk>/', SubCorrectView.as_view(), name='sub-correct'),
    path('detail/<int:pk>/', SubDetailView.as_view(), name='sub-detail'),
    path('renew/all/', SubRenewAllView.as_view(), name='sub-renew-all'),
    path('renew/list/', SubRenewSelectionView.as_view(), name='sub-renew-list'),
    path('history/<int:person_id>/', SubHistoryView.as_view(), name='sub-history'),
]
invoiceitem_patterns = [
    path('create/<int:person_id>/', InvoiceItemCreateView.as_view(), name='item-create'),
    path('update/<int:pk>/', InvoiceItemUpdateView.as_view(), name='item-update'),
    path('detail/<int:pk>/', InvoiceItemDetailView.as_view(), name='item-detail'),
    path('list/<int:pk>/', InvoiceItemListView.as_view(), name='item-list'),
    path('table/', InvoiceItemTableView.as_view(), name='item-table'),
]
invoice_patterns = [
    path('generate/', InvoiceGenerateSelectionView.as_view(), name='invoices-generate'),
    path('delete/<int:pk>/', InvoiceDeleteView.as_view(), name='invoice-delete'),
    path('table/', InvoiceTableView.as_view(), name='invoice-list'),
    path('detail/<int:pk>/', InvoiceDetailView.as_view(), name='invoice-detail'),
    path('public/<str:token>/', InvoicePublicView.as_view(), name='public-invoice-token'),
    path('select/', InvoiceSelectView.as_view(), name='select'),
    path('batch/', InvoiceBatchView.as_view(), name='invoice-batch'),
    path('mail/<int:pk>/<str:option>/', InvoiceMailView.as_view(), name='invoice-mail'),
    path('mail/config/<int:pk>/', InvoiceMailConfigView.as_view(), name='invoice-mail-config'),
    path('mail/batch/<int:send>/', InvoiceMailBatchView.as_view(), name='invoice-mail-batch'),
]
payment_patterns = [
    path('list/', PaymentListView.as_view(), name='payment-list'),
    path('invoice/<int:invoice_id>/', PaymentCreateView.as_view(), name='payment-invoice'),
    path('detail/<int:pk>/', PaymentDetailView.as_view(), name='payment-detail'),
    path('update/<int:pk>/', PaymentUpdateView.as_view(), name='payment-update'),
    path('creditnote/create/<int:person_id>/', CreditNoteCreateView.as_view(), name='creditnote-create'),
    path('creditnote/<int:pk>/', CreditNoteDetailView.as_view(), name='creditnote-update'),
]
text_patterns = [
    path('create/', TextBlockCreateView.as_view(), name='text-create'),
    path('update/<int:pk>/', TextBlockUpdateView.as_view(), name='text-update'),
    path('list/', TextBlockListView.as_view(), name='text-list'),
]
email_patterns = [
    path('single/', EmailView.as_view(), name='email'),
    path('selection/', EmailSelectionView.as_view(), name='email-selection'),
    path('person/<int:person_id>/', EmailView.as_view(), name='email-person'),
    path('group/<int:group_id>/', EmailView.as_view(), name='email-group'),
    path('campaign/<int:campaign_id>/', EmailView.as_view(), name='email-campaign'),
]
mailtype_patterns = [
    path('create/', MailTypeCreateView.as_view(), name='mailtype-create'),
    path('update/<int:pk>/', MailTypeUpdateView.as_view(), name='mailtype-update'),
    path('detail/<int:pk>/', MailTypeDetailView.as_view(), name='mailtype-detail'),
    path('list/', MailTypeListView.as_view(), name='mailtype-list'),
    path('public/subscribe/<str:token>/', MailTypeSubscribeView.as_view(), name='mailtype-subscribe-public'),
    path('subscribe/<int:person>/', MailTypeSubscribeView.as_view(), name='mailtype-subscribe'),
]
billing_patterns = [
    path('period/', BillingView.as_view(), name='billing-period'),
    path('year_end/', YearEndView.as_view(), name='billing-year-end')
]
charts_patterns = [
    path('members/', ChartMembers.as_view(), name='charts-members')
]
