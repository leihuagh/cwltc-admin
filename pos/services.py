from datetime import datetime
from decimal import Decimal
from django.db.models import Sum
from .models import Transaction, LineItem
from members.models import InvoiceItem, ItemType


def create_transaction_from_receipt(creator_id, person_id, receipt):
    ''' Create transaction and lineitem records in the database '''
    total = Decimal(0)
    trans = Transaction(
        creator_id=creator_id,
        person_id=person_id,
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
    trans_records = Transaction.objects.filter(
        billed=False).values('person_id').annotate(inv_total=Sum('total'))
    description = ItemType.objects.get(pk=ItemType.BAR)
    for record in trans_records:
        inv_item = InvoiceItem(
            item_date=datetime.today(),
            item_type_id=ItemType.BAR,
            description=description,
            amount=record['inv_total'],
            person_id=record['person_id'],
            paid=False                      
            )
        inv_item.save()
    return Transaction.objects.filter(billed=False).update(billed=True)      

