from django.urls import path
from club.views import *

# URLs for logged in club members

urlpatterns = [
    path('', ClubHomeView.as_view(), name='club_home'),
    path('person/', PersonView.as_view(), name='club_person'),
    path('person/<int:pk>/', PersonView.as_view(), name='club_person_pk'),
    path('person/update/<int:pk>/', PersonUpdateView.as_view(), name='club_person_update'),
    path('person/mailtypes/<int:pk>/', PersonUpdateView.as_view(), name='club_person_update'),
    path('address/update/<int:pk>/', AddressUpdateView.as_view(), name='club_address_update'),

    path('search/', ClubSearchView.as_view(), name='club_search'),
    path('magazine/', ClubMagazineView.as_view(), name='club_magazine'),
    path('policies/', PoliciesView.as_view(), name='club_policies'),
    path('history/', HistoryView.as_view(), name='club_history'),

    path('account/overview/', StatementView.as_view(), name='club_account_overview'),
    path('invoice/<str:token>/', InvoiceView.as_view(), name='club_invoice'),
    path('account/bar/<int:pk>/', PosListView.as_view(bar=True), name='club_account_bar'),
    path('account/teas/<int:pk>/', PosListView.as_view(bar=False), name='club_account_teas'),
    path('account/visitors/<int:pk>/', VisitorsListView.as_view(), name='club_account_visitors'),
    path('account/pos-detail/<int:pk>/', PosDetailView.as_view(), name='club_pos_detail'),
    ]

