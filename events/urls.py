from django.conf.urls import url
from events.views import *

# POS App URLs

app_name = 'events'
urlpatterns = [
    url(r'^create/$', EventCreateView.as_view(), name='create'),
    url(r'^create/social$', EventCreateView.as_view(social=True), name='create_social'),

    url(r'^update/(?P<pk>\d+)/$', EventUpdateView.as_view(), name='update'),
    url(r'^detail/(?P<pk>\d+)/$', EventDetailView.as_view(), name='detail'),
    url(r'^admin/(?P<tournament_id>\d+)/$', EventAdminTableView.as_view(), name='admin_tournament'),
    url(r'^admin/$', EventAdminTableView.as_view(), name='admin'),
    url(r'^list/$', EventListView.as_view(), name='list'),
    url(r'^register/done/$', EventRegisterDone.as_view(), name='register_done'),
    url(r'^register/token/(?P<token>.+)/(?P<pk>\d+)$', EventRegisterView.as_view(), name='register_token'),
    url(r'^register/admin/(?P<pk>\d+)/$', EventRegisterView.as_view(admin=True), name='register_admin'),
    url(r'^register/(?P<pk>\d+)/$', EventRegisterView.as_view(), name='register'),
    url(r'^help/$', EventHelpView.as_view(), name='help'),

    url(r'^tournament/create/$', TournamentCreateView.as_view(), name='tournament_create'),
    url(r'^tournament/update/(?P<pk>\d+)/$', TournamentUpdateView.as_view(), name='tournament_update'),
    url(r'^tournament/detail/(?P<pk>\d+)/$', TournamentDetailView.as_view(), name='tournament_detail'),
    url(r'^tournament/admin/$', TournamentAdminView.as_view(), name='tournament_admin'),
    url(r'^tournament/people/(?P<pk>\d+)/$', TournamentPlayersView.as_view(), name='tournament_players'),
    url(r'^tournament/download/(?P<pk>\d+)/$', TournamentDownloadView.as_view(), name='tournament_download'),

    url(r'^participant/list/(?P<pk>\d+)/$', ParticipantListView.as_view(), name='participant_list'),
    url(r'^participant/download/(?P<pk>\d+)/$', ParticipantDownloadView.as_view(), name='participant_download'),
    url(r'^participant/add/(?P<pk>\d+)/$', ParticipantAddView.as_view(), name='participant_add'),
    url(r'^participant/edit/(?P<pk>\d+)/$', ParticipantEditView.as_view(), name='participant_edit'),
    ]
