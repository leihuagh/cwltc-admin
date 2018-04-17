from django.conf.urls import url
from events.views import *

# POS App URLs

app_name = 'events'
urlpatterns = [
    url(r'^create/$', EventCreateView.as_view(), name='create'),
    url(r'^update/(?P<pk>\d+)/$', EventUpdateView.as_view(), name='update'),
    url(r'^detail/(?P<pk>\d+)/$', EventDetailView.as_view(), name='detail'),
    url(r'^list/$', EventListView.as_view(), name='list')
    ]
