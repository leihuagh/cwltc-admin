import django_tables2 as tables
from django_tables2.utils import A
from .models import Tournament, Event


class EventTable(tables.Table):

    class Meta:
        model = Event
        fields = ('name', 'date', 'cost', 'active', 'billed', 'online_entry')
        attrs = {'class': 'table table-sm table-responsive table-borderless bg-white dark-header with-border'}

    name = tables.LinkColumn('events:update', args=[A('pk')], text=lambda record: record.name)
    tournament = tables.LinkColumn('events:tournament_update', args=[A('tournament.id')],
                                   text=lambda record: record.tournament.name)
    tickets = tables.Column(accessor=A('total_ticket_count'))
    preview = tables.LinkColumn('events:register', args=[A('pk')], text='Preview', orderable=False)


class TournamentTable(tables.Table):

    class Meta:
        model = Tournament
        fields = ('name', 'description', 'draw_date', 'finals_date', 'event_cost', 'active')
        attrs = {'class': 'table table-sm table-responsive table-borderless bg-white dark-header with-border'}

    billed = tables.BooleanColumn(accessor='billed')
    edit = tables.LinkColumn('events:tournament_update', text='Edit', args=[A('pk')], orderable=False)