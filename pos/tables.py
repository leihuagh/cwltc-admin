import django_tables2 as tables
from django_tables2.utils import A
from pos.models import *

class TransactionTable(tables.Table):
    
    class Meta:
        model = Transaction
        fields = ('creation_date', 'id', 'person.fullname', 'total', 'split', 'billed')
        attrs = {'class': 'table'}
         
    total = tables.Column(
        attrs={
            'td':{'style':'text-align: right;'}
            }
        )

    detail = tables.LinkColumn('pos_transaction_detail', text='Detail', args=[A('pk')], orderable=False)


class PosPaymentTable(tables.Table):

    class Meta:
        model = PosPayment
        fields = ('transaction.creation_date', 'person.fullname', 'transaction.person.fullname' 'amount', 'billed')
        attrs = {'class': 'table'}

    amount = tables.Column(
        attrs={
            'td': {'style': 'text-align: right;'}
        }
    )

    detail = tables.LinkColumn('pos_transaction_detail', text='Detail', args=[A('transaction.pk')], orderable=False)


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
        fields = ('id', 'button_text', 'description', 'sale_price', 'cost_price', 'margin', 'item_type', 'colour')
        attrs = {'class': 'table'}

    id = tables.LinkColumn('pos_item_update', verbose_name='', text='Edit', args=[A('pk')], orderable=True)
    item_type = tables.Column(accessor='item_type.description',
                              verbose_name='Charge to',
                              order_by='item_type.description',
                              orderable=True)
    margin = tables.Column(accessor=A('margin_formatted'),
                           verbose_name='Margin',
                           )
    colour = tables.Column(accessor='colour.name', verbose_name='Colour')


class LayoutTable(tables.Table):

    class Meta:
        model = Layout
        fields = ('edit', 'name', 'is_default', 'default')
        attrs = {'class': 'table'}

    edit = tables.TemplateColumn('<a href="{% url "pos_layout_update" record.id %}" class="btn btn-primary btn-xs">Edit</a>', verbose_name = u'Edit',)
    default = tables.TemplateColumn('<input type="submit" name="{{ record.id }}" class="btn btn-primary btn-xs" value="Set as default"></form>', verbose_name = u'',)


class ColourTable(tables.Table):

    class Meta:
        model = Colour
        fields = ('id', 'name', 'fore_colour', 'back_colour', 'outline_colour', 'sample')
        attrs = {'class': 'table'}

    id = tables.LinkColumn('pos_colour_update', verbose_name='', text='Edit', args=[A('pk')], orderable=True)
    sample = tables.TemplateColumn(
            '''<button class="posbutton" style="color: {{ record.fore_colour }};
                background-color: {{ record.back_colour }};
                border: {{ record.outline_colour }};">Sample</button>'''
    )

