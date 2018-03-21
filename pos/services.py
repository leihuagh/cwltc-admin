from datetime import datetime
from decimal import Decimal
from django.db.models import Sum
from django.db import transaction
from django.forms.models import model_to_dict
from .models import Transaction, LineItem, Layout, PosPayment
from members.models import InvoiceItem, ItemType

TWO_PLACES = Decimal(10) ** -2


@transaction.atomic
def create_transaction_from_receipt(creator_id, layout_id, receipt, total, people,
                                    complementary=False):
    """ Create Transaction, LineItem and PosPayment records in the database """
    count = len(people)
    if count > 0:
        person_id = people[0]['id']
    else:
        person_id = None
    trans = Transaction(
        creator_id=creator_id,
        person_id=person_id,
        layout_id=layout_id,
        total=Decimal(total).quantize(TWO_PLACES),
        billed=False,
        cash=person_id == None,
        complementary=complementary,
        split=count > 1
        )
    trans.save()

    for item_dict in receipt:
        line_item = LineItem(
            item_id=item_dict['id'],
            sale_price=Decimal(item_dict['sale_price']).quantize(TWO_PLACES),
            cost_price=Decimal(item_dict['cost_price']).quantize(TWO_PLACES),
            quantity=1,
            transaction=trans
            )
        line_item.save()

    for person in people:
        pos_payment = PosPayment(
            transaction=trans,
            person_id=person['id'],
            billed=False,
            amount=Decimal(person['amount']/100).quantize(TWO_PLACES)
        )
        pos_payment.save()


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
