from django.conf.urls import url
from club.views import *

# URLs for logged in club members

urlpatterns = [
    url(r'^$', ClubHomeView.as_view(), name='club_home'),
    url(r'^person/$', PersonView.as_view(), name='club_person'),
    url(r'^person/(?P<pk>\d+)/$', PersonView.as_view(), name='club_person_pk'),
    url(r'^person/update/(?P<pk>\d+)/$', PersonUpdateView.as_view(), name='club_person_update'),
    url(r'^person/mailtypes/(?P<pk>\d+)/$', PersonUpdateView.as_view(), name='club_person_update'),
    url(r'^address/update/(?P<person_id>\d+)/$', AddressUpdateView.as_view(), name='club_address_update'),
    url(r'^search/$', ClubSearchView.as_view(), name='club_search'),
    url(r'^magazine/$', ClubMagazineView.as_view(), name='club_magazine'),
    url(r'^policies/$', PoliciesView.as_view(), name='club_policies'),
    url(r'^invoice/list/$', InvoiceListView.as_view(), name='club_invoice_list'),
    url(r'^invoice/(?P<token>.+)/$', ClubInvoiceView.as_view(), name='club_invoice'),
    url(r'^history/$', HistoryView.as_view(), name='club_history'),
    ]
