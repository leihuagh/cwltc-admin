from datetime import datetime
from decimal import Decimal
from django.db.models import Sum
from django.db import transaction
from django.forms.models import model_to_dict
from .models import Transaction, LineItem, Layout, PosPayment
from members.models import InvoiceItem, ItemType


@transaction.atomic
def create_transaction_from_receipt(creator_id, people_ids, layout_id, receipt,
                                    cash=False, complementary=False):
    """ Create Transaction, LineItem and PosPayment records in the database """
    total = Decimal(0)
    count = len(people_ids)
    if count > 0:
        person_id = people_ids[0]
    else:
        person_id=None
    trans = Transaction(
        creator_id=creator_id,
        person_id=person_id,
        layout_id=layout_id,
        total=total,
        billed=False,
        cash=cash,
        complementary=complementary,
        split=count > 1
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
    if count > 0:
        first_amount, split_amount = get_split_amounts(total * 100, count)
        i = 0
        for person_id in people_ids:
            amount = first_amount if i==0 else split_amount
            pos_payment = PosPayment(
                transaction=trans,
                person_id=person_id,
                billed=False,
                amount=Decimal(amount/100)
            )
            pos_payment.save()
            i += 1


def create_invoiceitems_from_transactions():
    """ create invoiceitem records from the transaction total record """
    
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


def create_invoiceitems_from_payments():
    """ Create invoiceitem records from the payment records """

    # cache the item types in a dictionary indexed by layout for performance
    itemTypes = ItemType.objects.all().select_related("invoice_item")
    layoutDict = {}
    layouts = Layout.objects.all()
    for layout in layouts:
        layoutDict[layout.id] = [layout.invoice_itemtype_id, layout.invoice_itemtype.description]

    payment_records = PosPayment.objects.filter(
        billed=False).values('person_id', 'transaction__layout_id').annotate(inv_total=Sum('amount'))
    description = ItemType.objects.get(pk=ItemType.BAR)
    for record in payment_records:
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
    return PosPayment.objects.filter(billed=False).update(billed=True)


def get_split_amounts(total, count):
    """
    Split a receipt total into n parts
    :param total: Decimal
    :param count: integer
    :return: tuple( first_amount, subsequent_amount)
    """
    split_amount = total // count
    first_amount = split_amount
    split_total = split_amount * count
    if split_total != total:
        first_amount += 1
    return first_amount, split_amount