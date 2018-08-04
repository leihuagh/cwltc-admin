import django_tables2 as tables
from django_tables2.utils import A
from .models import Tournament, Event


class EventTable(tables.Table):

    class Meta:
        model = Event
        fields = ('name', 'end_date', 'cost', 'active', 'billed', 'tournament.name')
        attrs = {'class': 'table table-sm table-responsive table-borderless bg-white dark-header with-border'}

    edit = tables.LinkColumn('events:update', text='Edit', args=[A('pk')], orderable=False)


class TournamentTable(tables.Table):

    class Meta:
        model = Tournament
        fields = ('name', 'description', 'draw_date', 'finals_date', 'event_cost', 'active')
        attrs = {'class': 'table table-sm table-responsive table-borderless bg-white dark-header with-border'}

    billed = tables.BooleanColumn(accessor='billed')
    edit = tables.LinkColumn('events:tournament_update', text='Edit', args=[A('pk')], orderable=False)