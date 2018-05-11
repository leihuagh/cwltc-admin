from django.conf.urls import url
from events.views import *

# POS App URLs

app_name = 'events'
urlpatterns = [
    url(r'^create/$', EventCreateView.as_view(), name='create'),
    url(r'^update/(?P<pk>\d+)/$', EventUpdateView.as_view(), name='update'),
    url(r'^detail/(?P<pk>\d+)/$', EventDetailView.as_view(), name='detail'),
    url(r'^list/$', EventListView.as_view(), name='list'),
    url(r'^admin/$', EventAdminView.as_view(), name='admin'),
    url(r'^help/$', EventHelpView.as_view(), name='help'),
    url(r'^tournament/create/$', TournamentCreateView.as_view(), name='tournament_create'),
    url(r'^tournament/update/(?P<pk>\d+)/$', TournamentUpdateView.as_view(), name='tournament_update'),
    url(r'^tournament/detail/(?P<pk>\d+)/$', TournamentDetailView.as_view(), name='tournament_detail'),
    url(r'^tournament/list/$', TournamentListView.as_view(), name='tournament_list'),
    url(r'^tournament/admin/$', TournamentAdminView.as_view(), name='tournament_admin'),
    url(r'^tournament/active/$', TournamentActiveView.as_view(), name='tournament_active'),
    url(r'^tournament/people/(?P<pk>\d+)/$', TournamentPlayersView.as_view(), name='tournament_players'),
    url(r'^participant/list/(?P<pk>\d+)/$', ParticipantListView.as_view(), name='participant_list'),
    url(r'^participant/add/(?P<pk>\d+)/$', ParticipantAddView.as_view(), name='participant_add'),
    url(r'^participant/edit/(?P<pk>\d+)/$', ParticipantEditView.as_view(), name='participant_edit'),
    ]
