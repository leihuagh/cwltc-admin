from django.conf.urls import url
from wimbledon.views import *


urlpatterns = [
    url(r'^ballot/$', BallotView.as_view(), name='wimbledon_ballot'),
    url(r'^choice/$', ChoiceView.as_view(), name='wimbledon_choice'),
    url(r'^done/$', DoneView.as_view(), name='wimbledon_done'),
    url(r'^export/$', ExportView.as_view(), name='wimbledon_export')
    ]