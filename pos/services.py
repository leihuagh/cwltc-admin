from datetime import datetime
from decimal import Decimal
from django.db.models import Sum
from django.forms.models import model_to_dict
from .models import Transaction, LineItem, Layout
from members.models import InvoiceItem, ItemType


def create_transaction_from_receipt(creator_id, person_id, layout_id, receipt):
    ''' Create transaction and lineitem records in the database '''
    total = Decimal(0)
    trans = Transaction(
        creator_id=creator_id,
        person_id=person_id,
        layout_id=layout_id,
        total=total,
        billed=False
        )
    trans.save()
    for item_dict in receipt:
        line_item = LineItem(
            item_id=item_dict['id'],
            sale_price=Decimal(item_dict['sale_price'])/100,
            cost_price=Decimal(item_dict['cost_price'])/100,
            quantity=item_dict['quantity'],
            transaction=trans
            )       
        line_item.save()
        total += line_item.quantity * line_item.sale_price
    trans.total = total
    trans.save()
    return trans

def create_invoiceitems_from_transactions():
    ''' create invoiceitem records from the transaction total record '''
    
    # cache the item types in a dictionary indexed by layout for performance
    itemTypes = ItemType.objects.all().select_related("invoice_item") 
    layoutDict = {}
    layouts = Layout.objects.all()
    for layout in layouts:
        layoutDict[layout.id]=[layout.invoice_itemtype_id, layout.invoice_itemtype.description]

    trans_records = Transaction.objects.filter(
        billed=False).values('person_id','layout_id').annotate(inv_total=Sum('total'))
    description = ItemType.objects.get(pk=ItemType.BAR)
    for record in trans_records:
        itemData = layoutDict[record['layout_id']]
        inv_item = InvoiceItem(
            item_date=datetime.today(),
            item_type_id=itemData[0],
            description=itemData[1],
            amount=record['inv_total'],
            person_id=record['person_id'],
            paid=False                      
            )
        inv_item.save()
    return Transaction.objects.filter(billed=False).update(billed=True)      

