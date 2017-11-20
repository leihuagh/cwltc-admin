import django_tables2 as tables
from django_tables2.utils import A
from pos.models import *

class TransactionTable(tables.Table):
    
    class Meta:
        model = Transaction
        fields = ('creation_date', 'id', 'person.first_name','person.last_name', 'total', 'billed')
        attrs = {'class': 'table table-condensed'}
         
    total = tables.Column(
        attrs={
            'td':{'style':'text-align: right;'}
            }
        )

    detail = tables.LinkColumn('pos_transaction_detail', text='Detail', args=[A('pk')], orderable=False)


class LineItemTable(tables.Table):
    
    class Meta:
        model = LineItem
        fields = ('transaction.creation_date', 'item.description', 'quantity', 'sale_price', 'item.item_type.description',
                  'transaction.person.first_name', 'transaction.person.last_name', 'transaction_id' )
        attrs = {'class': 'table table-condensed'}


    transaction_id = tables.LinkColumn('pos_transaction_detail', text='view', args=[A('transaction.id')], orderable=False)


class ItemTable(tables.Table):

    class Meta:
        model = LineItem
        fields = ('id', 'button_text', 'description', 'sale_price', 'cost_price', 'item_type')
        attrs = {'class': 'table table-condensed'}

    id = tables.LinkColumn('pos_item_update', text='Edit', args=[A('pk')], orderable=True)
    item_type = tables.Column(accessor='item_type.description',
                                verbose_name='Charge to',
                                order_by='item_type.description',
                                orderable=True)

class LayoutTable(tables.Table):

    class Meta:
        model = Layout
        fields = ('edit', 'name')
        attrs = {'class': 'table'}

    edit = tables.TemplateColumn('<a href="{% url "pos_layout_update" record.id %}" class="btn btn-primary btn-xs">Edit</a>', verbose_name = u'Edit',)



