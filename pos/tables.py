import django_tables2 as tables
from django_tables2.utils import A
from pos.models import *

class TransactionTable(tables.Table):
    
    class Meta:
        model = Transaction
        fields = ('creation_date', 'id', 'person.first_name','person.last_name', 'total',
                  'layout.invoice_itemtype.description', 'billed')                 
        attrs = {'class': 'table table-condensed'}
         
    total = tables.Column(
        attrs={
            'td':{'style':'text-align: right;'}
            }
        )

    detail = tables.LinkColumn('transaction-detail', text='Detail', args=[A('pk')], orderable=False)

class LineItemTable(tables.Table):
    
    class Meta:
        model = LineItem
        fields = ('transaction.creation_date', 'transaction_id', 'item.description', 'quantity', 'sale_price')
        attrs = {'class': 'table table-condensed'} 


    transaction_id = tables.LinkColumn('transactions', text='Transaction', args=[A('transaction_id')], orderable=False)
