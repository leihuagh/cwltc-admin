import datetime
from decimal import Decimal
from django.db import transaction
from django.http import HttpResponse
from openpyxl import Workbook
from openpyxl.utils import get_column_letter
from openpyxl.styles import Font
from .views.ipad_views import build_pos_array
from .models import Transaction, LineItem, Layout, PosPayment, Item, TWO_PLACES
from members.models import InvoiceItem, ItemType

@transaction.atomic
def create_transaction_from_receipt(creator_id, terminal, layout_id, receipt, total, people, attended):
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
        split=count > 1,
        attended=attended
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


def dump_items_to_excel(item_type_id):
    """ https://djangotricks.blogspot.co.uk/2013/12/how-to-export-data-as-excel.html """
    queryset= Item.objects.filter(item_type_id=item_type_id)

    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename=Items.xlsx'

    wb = Workbook()
    ws = wb.active
    ws.title = 'Items'

    row_num = 0

    columns = [
        ('Description', 40),
        ('Price', 10),
    ]

    for col_num in range(len(columns)):
        c = ws.cell(row=row_num + 1, column=col_num + 1)
        c.value = columns[col_num][0]
        c.font = Font(sz=12, bold=True)
        ws.column_dimensions[get_column_letter(col_num + 1)].width = columns[col_num][1]

    for obj in queryset:
        row_num += 1
        row = [
            obj.description,
            obj.sale_price,
        ]
        for col_num in range(len(row)):
            c = ws.cell(row=row_num + 1, column=col_num + 1)
            c.value = row[col_num]
            if col_num == 1:
                c.number_format = '£0.00'

    wb.save(response)
    return response

def dump_layout_to_excel(layout):
    """ https://djangotricks.blogspot.co.uk/2013/12/how-to-export-data-as-excel.html """
    array, items = build_pos_array(layout)
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename=Price list.xlsx'

    wb = Workbook()
    ws = wb.active
    ws.title = 'Price List'

    widths = [10, 40, 10]

    for col_num in range(len(widths)):
        ws.column_dimensions[get_column_letter(col_num + 1)].width = widths[col_num]

    c = ws.cell(row=1, column=2, value='Price List')

    row_num = 2
    for row in array:
        for col_num in range(len(row)):
            if col_num == 0:
                if len(row[col_num]) > 2:
                    description = row[col_num][2]
                    ws.cell(row=row_num, column=1, value=description)
                    row_num += 1
            else:
                if len(row[col_num]) > 2:
                    item = row[col_num][2]
                    ws.cell(row=row_num, column=2, value=item.description)
                    c = ws.cell(row=row_num, column=3, value=item.sale_price)
                    c.number_format = '£0.00'
                    row_num += 1
    wb.save(response)
    return response