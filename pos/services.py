import datetime
from decimal import Decimal
from django.db.models import Sum
from django.db import transaction
from .models import Transaction, LineItem, Layout, PosPayment, TWO_PLACES
from members.models import InvoiceItem, ItemType

@transaction.atomic
def create_transaction_from_receipt(creator_id, terminal, layout_id, receipt, total, people):
    """
    Create Transaction, LineItem and PosPayment records in the database
    Return a description of it
    """
    complimentary = False
    count = len(people)
    dec_total = Decimal(total).quantize(TWO_PLACES)
    item_type = Layout.objects.get(pk=layout_id).item_type
    if count > 0:
        person_id = int(people[0]['id'])
        if person_id == -1:
            complimentary = True
            person_id = None
    else:
        person_id = None
    trans = Transaction(
        creator_id=creator_id,
        person_id=person_id,
        terminal=terminal,
        item_type=item_type,
        total=dec_total,
        billed=False,
        cash=person_id == None and not complimentary,
        complimentary=complimentary,
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

    if complimentary:
        return ('Complimentary', dec_total)

    for person in people:
        pos_payment = PosPayment(
            transaction=trans,
            person_id=person['id'],
            billed=False,
            amount=Decimal(person['amount']/100).quantize(TWO_PLACES)
        )
        pos_payment.save()
    if people:
        return (people[0]['name'], dec_total)
    else:
        return ('Cash', dec_total)


def create_invoiceitems_from_payments(item_type_id):
    """
    Create invoiceitem records from the payment records
    """
    dict = {}
    records = PosPayment.objects.filter(transaction__item_type_id=item_type_id, billed=False).order_by('person_id')
    last_id = 0
    count = 0
    for record in records:
        if record.person_id:
            count += 1
            if record.person_id != last_id:
                last_id = record.person_id
                dict[record.person_id] = Decimal(record.amount)
            else:
                dict[record.person_id] += record.amount

    description = ItemType.objects.get(pk=item_type_id)
    with transaction.atomic():
        for id, total in dict.items():
            inv_item = InvoiceItem(
                item_date=datetime.date.today(),
                item_type_id=item_type_id,
                description=description,
                amount=total,
                person_id=id,
                paid=False
            )
            inv_item.save()
        records.update(billed=True)
        Transaction.objects.filter(item_type_id=item_type_id, billed=False) .update(billed=True)
    return count, len(dict)


def delete_billed_transactions(before_date):
    """
    Delete transactions and linked items and payments
    """
    trans = Transaction.objects.filter(billed=True, creation_date__lt=before_date)
    count = trans.count()
    trans.delete()
    return count


def fix_tea_transactions():
    Transaction.objects.filter(creation_date__gt=datetime.date(2018, 3, 1)).filter(
        creation_date__lt=datetime.date(2018, 3, 15)).update(item_type_id=ItemType.TEAS)
