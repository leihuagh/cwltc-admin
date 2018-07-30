import django_tables2 as tables
from django_tables2.utils import A
from pos.models import PosPayment

class PosPaymentsTable(tables.Table):

    class Meta:
        model = PosPayment
        fields = ('transaction.creation_date', 'person.fullname', 'total', 'transaction.item_type.description',
                  'split', 'transaction.attended')
        attrs = {'class': 'table'}

    detail = tables.LinkColumn('club_pos_detail', text='View detail',
                               args=[A('transaction.pk')], orderable=False)