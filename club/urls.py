from django.conf.urls import url, include
from club.views import *

# URLs for logged in club members

urlpatterns = [
    url(r'$', ClubHomeView.as_view(), name='club_home'),
    url(r'personal/$', ClubPersonalView.as_view(), name='club_person'),
    url(r'account/$', ClubAccountView.as_view(), name='club_account'),
    url(r'search/$', ClubSearchView.as_view(), name='club_search'),
    ]
