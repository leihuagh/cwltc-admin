from .models import *
from decimal import *

def create_transaction_from_receipt(creator_id, person_id, receipt):
    trans = Transaction()
    total = Decimal(0)
    trans.creator_id = creator_id
    trans.person_id = person_id
    trans.total = total
    trans.save()
    for item_dict in receipt:
        line_item = LineItem()
        line_item.item_id = item_dict['id']
        line_item.sale_price = Decimal(item_dict['sale_price'])/100
        line_item.cost_price = Decimal(item_dict['cost_price'])/100
        line_item.quantity = item_dict['quantity']
        total += line_item.quantity * line_item.sale_price
        line_item.transaction = trans
        line_item.save()
    trans.total = total
    trans.save()
    return trans