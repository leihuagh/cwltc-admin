import django_tables2 as tables
from django_tables2.utils import A
from pos.models import PosPayment, VisitorBook


class PosPaymentsTable(tables.Table):

    class Meta:
        model = PosPayment
        fields = ('transaction.creation_date',  'total', 'transaction.item_type.description',
                  'split', 'transaction.attended')
        attrs = {'class': 'table table-sm table-responsive table-borderless bg-white dark-header with-border'}


    split = tables.BooleanColumn(accessor='transaction.split', verbose_name='Split transaction')
    detail = tables.LinkColumn('club_pos_detail', text='View detail',
                               args=[A('transaction.pk')], orderable=False)

class VisitorBookTable(tables.Table):

    class Meta:
        model = VisitorBook
        fields = ('date', 'visitor', 'fee')
        attrs = {'class': 'table table-sm table-responsive table-borderless bg-white dark-header with-border'}
        sequence = ('date', 'visitor', 'visitor_junior', 'fee')

    visitor = tables.Column(accessor='visitor.fullname')
    visitor_junior = tables.Column(accessor='visitor.junior', verbose_name='Adult/Junior')

    def render_visitor_junior(self, value):
        if value:
            return 'Junior'
        return 'Adult'
