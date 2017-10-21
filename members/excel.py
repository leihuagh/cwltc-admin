from numbers import Number
from django.http import HttpResponse
from django.apps import apps
from datetime import date, datetime
from xlrd import open_workbook, xldate_as_tuple
from xlwt import Workbook, Style, easyxf
from members.models import (Membership, Person, Address, Fees, Subscription, ItemType,
                            Invoice, InvoiceItem, Payment)


def open_local_workbook():
    book = open_workbook('transaction.xls')


def open_excel_workbook(input_file):
    book = open_workbook(file_contents=input_file.read())
    return book

def export_all():
    response = HttpResponse(content_type='application/vnd.ms-excel')
    response['Content-Disposition'] = 'attachment; filename=Cwltc.xls'
    book = Workbook(encoding='utf-8')
    sheets = [
        'fees',
        'membership',
        'itemtype',
        'address',
        'person',
        'subscription',
        'invoiceitem',
        'invoice',
        'payment',
        'creditnote',
        'textblock'
        ]
    for sheet in sheets:
        export_sheet(book, sheet)
    book.save(response)
    return response

def export_sheet(book, model_name):
    sheet = book.add_sheet(model_name)
    my_model = apps.get_model ('members', model_name)
    
    # get list of column names including foreign keys with _id
    # but ignore creation_date or update_date
    columns = []
    for field in my_model._meta.fields:
        if field.name !='creation_date' and field.name != 'update_date':
            columns.append(field.attname)
    
    # write a header row
    for col_num in range(len(columns)):
        sheet.write(0, col_num, columns[col_num])
    
    # write all objects
    row_num=0
    for object in my_model.objects.all():
        row_num += 1
        for col_num in range(len(columns)):
                      
            sheet.write(row_num, col_num, getattr(object, columns[col_num])) 
   

def export_invoices(invoices):
    response = HttpResponse(content_type='application/vnd.ms-excel')
    response['Content-Disposition'] = 'attachment; filename=Invoices.xls'
    book = Workbook(encoding='utf-8')
    sheet = book.add_sheet('Invoices')
    date_style = easyxf(num_format_str='dd/mm/yyyy')
    default_style = Style.default_style
    
    columns = [
        'Id',
        'State',
        'Created',
        'Updated',
        'Year', 
        'Person_id',
        'Person',
        'Total', 
        'Emailed',   
        'Reference',
        'GoCardless Id',
        'GC Action',
        'Payment Id',
        'Credit note Id'
    ]
    for col_num in range(len(columns)):
        sheet.write(0, col_num, columns[col_num])
                             
    row_num = 0
    for inv in invoices:
        row_num += 1
        payment = ""
        if inv.payment_set.count():
            payment = inv.payment_set.all()[0].id
        cnote = ""
        if inv.creditnote_set.count():
            cnote = inv.creditnote_set.all()[0].id
        row = [
            inv.id,
            Invoice.STATES[inv.state][1],
            inv.creation_date,
            inv.update_date,
            inv.membership_year,
            inv.person_id,
            inv.person.fullname,
            inv.total,
            inv.email_count,    
            inv.reference,
            inv.gocardless_bill_id,
            inv.gocardless_action,
            payment,
            cnote          
        ]
        for col_num in range(len(row)):
            data = row[col_num]
            if isinstance(data, datetime):
                style = date_style
                data = date(data.year, data.month, data.day)
            else:
                style = default_style
            sheet.write(row_num, col_num, data, style=style)  
      
    book.save(response)
    return response

def export_payments(payments):
    response = HttpResponse(content_type='application/vnd.ms-excel')
    response['Content-Disposition'] = 'attachment; filename=Payments.xls'
    book = Workbook(encoding='utf-8')
    sheet = book.add_sheet('Payments')
    date_style = easyxf(num_format_str='dd/mm/yyyy')
    default_style = Style.default_style
    
    columns = [
        'Year',
        'Number',
        'Date',
        'Type',
        'Person_Id',
        'Person',
        'Reference',
        'Invoice_Id',
        'Amount',
        'Fee',
        'Banked',
        'Banked date'
    ]
    for col_num in range(len(columns)):
        sheet.write(0, col_num, columns[col_num])
                             
    row_num = 0
    for pay in payments:
        row_num += 1
        row = [
            pay.membership_year,
            pay.id,
            pay.update_date,
            Payment.TYPES[pay.type][1],
            pay.person_id,
            pay.person.fullname,
            pay.reference,
            pay.invoice.id,
            pay.amount,
            pay.fee,
            pay.banked,
            pay.banked_date
        ]
        for col_num in range(len(row)):
            data = row[col_num]
            if isinstance(data, datetime) or isinstance(data, date):
                style = date_style
                data = date(data.year, data.month, data.day)
            else:
                style = default_style
            sheet.write(row_num, col_num, data, style=style)  
      
    book.save(response)
    return response    

def export_members(option):
    ''' Export a members list in the format used by the bar system '''

    people = Person.objects.all()  
    if option == 'parents':
        people = Person.parent_objects.all() 
        sheetName = 'Parents'
    else:
        people = Person.objects.all() 
        sheetName = 'Members'
    return export_people(sheetName, people, option)


def export_people(sheetName, people, option=""):
   
    response = HttpResponse(content_type='application/vnd.ms-excel')
    response['Content-Disposition'] = 'attachment; filename=' + sheetName + '.xls'
    book = Workbook(encoding='utf-8')
    sheet = book.add_sheet(sheetName)                
    columns = [
        'Id',
        'State',
        'Gender',
        'First name',
        'Last name',
        'Address 1',
        'Address 2',
        'Town',
        'Post code',
        'Home phone',
        'Mobile phone',
        'Email',
        'Year joined',
        'Membership',
        'Paid',
        'Resigned'
        ]
    for col_num in range(len(columns)):
        sheet.write(0, col_num, columns[col_num])
                   
    row_num = 0
    for person in people:
        valid = False
        if option == 'bar':
            if not person.mem_id in Membership.NO_BAR_ACCOUNT:
                valid = True
        else:
            valid=True
        if valid:
            row_num += 1
            address = person.address              
            joined = date.today()
            if person.date_joined:
                joined = person.date_joined
            if person.sub:
                desc = person.sub.membership.description
                paid = person.sub.paid
                resigned = person.sub.resigned
            else:
                desc = "No sub"
                paid = False
                resigned = False
            row = [
                person.id,
                person.state,
                person.gender,   
                person.first_name,
                person.last_name,
                address.address1,
                address.address2,
                address.town,
                address.post_code,
                address.home_phone,
                person.mobile_phone, 
                person.email,      
                joined.year,
                desc,
                paid,
                resigned
            ]
            for col_num in range(len(row)):
                sheet.write(row_num, col_num, row[col_num])
    book.save(response)
    return response   


def export_members(memlist, juniors=False):
   
    if juniors:
        sheet_name = 'Juniors'            
        columns = [
            'Id',
            'Gender',
            'First name',
            'Last name',
            'Membership',
            'Date of birth',
            'Date joined',
            'Parent first name',
            'Parent last name',
            'Email',
            'Mobile phone',
            'Home phone',
            'Address 1',
            'Address 2',
            'Town',
            'Post code'
            ]
    else:
        sheet_name = 'Members'
        columns = [
            'Id',
            'Gender',
            'First name',
            'Last name',
            'Address 1',
            'Address 2',
            'Town',
            'Post code',
            'Home phone',
            'Mobile phone',
            'Email',
            'Year joined',
            'Membership'
            ]
    response = HttpResponse(content_type='application/vnd.ms-excel')
    response['Content-Disposition'] = 'attachment; filename=' + sheet_name + '.xls'
    book = Workbook(encoding='utf-8')
    sheet = book.add_sheet(sheet_name) 
    for col_num in range(len(columns)):
        sheet.write(0, col_num, columns[col_num])
                   
    row_num = 0
    for row in memlist:
        row_num += 1
        for col_num in range(len(row)):
            sheet.write(row_num, col_num, row[col_num]) 
    book.save(response)
    return response

def import_items(sheet, save_data):
    """
    Import invoice items and Excel sheets in the book
     return [count, errorlist]
    """
    errors=[]
    col_id = -1
    col_item_id = -1
    col_amount = -1
    col_description = -1
    row = 0
    for col in range(0, sheet.ncols):
        value = sheet.cell(row,col).value.upper()
        if value == 'ID':
            col_id = col
        elif value == 'CODE':
            col_item_id = col
        elif value == 'AMOUNT':
            col_amount = col
        elif value == 'DESCRIPTION':
            col_description = col

    if col_id > -1 and col_item_id > -1 and col_amount > -1:
        count=0
        for row in range(1, sheet.nrows):
            try:
                if sheet.cell_value(row, col_id) != u"":
                    person_id = int(sheet.cell_value(row, col_id))
                    amount = sheet.cell_value(row, col_amount)
                    item_id = int(sheet.cell_value(row, col_item_id))
                    description = ''
                    if col_description > 0:
                        description = sheet.cell_value(row, col_description)
                    if description == '':
                        description = ItemType.objects.get(pk=item_id).description

                    count += 1
                    if save_data:
                        new_item = InvoiceItem(person_id=person_id,
                                                item_type_id=item_id,
                                                description=description,
                                                amount=amount)
                        new_item.save()
                    else:
                        person = Person.objects.get(id=person_id)
                        if not isinstance(amount, Number):
                            raise TypeError()
                        item = ItemType.objects.get(id=item_id)
            except (ValueError, TypeError):
                errors.append('Error on row {}' .format(row + 1))
                continue
        return [count, errors]
    else:
        errors.append('Column headers are missing')
        return[0, errors]

# def import_all(book):
#     model_name = 'fees'
#     import_sheet(book, model_name)
#     return HttpResponse("Imported")
#
# def import_sheet(book, model_name):
#     try:
#         sheet = book.sheet_by_name(model_name)
#         my_model = apps.get_model('members', model_name)
#         # get list of column names including foreign keys with _id
#         # but ignore creation_date or update_date
#         columns = []
#         for col in range(0, sheet.ncols):
#             f_name = sheet.cell(0, col).value
#             field = my_model._meta.get_field(f_name)
#             columns.append(field)
#             type = field.get_internal_type()
#     except:
#         return False
#     return True
#
# def import_base_tables(book):
#     try:
#         import_categories(book)
#         import_fees(book)
#         import_itemtypes(book)
#         return True
#     except:
#         return false
#     return True
#
# def import_categories(book):
#     sheet = book.sheet_by_name('Categories')
#     if sheet.row(0)[0].value.upper() == 'ID':
#         for row in range(1, sheet.nrows):
#             id = sheet.cell_value(row, 0)
#             description = sheet.cell_value(row, 1)
#             Membership.create(id, description)
#
# def import_fees(book):
#     sheet = book.sheet_by_name('Fees')
#     if sheet.row(0)[0].value.upper() == 'ID':
#         for row in range(1, sheet.nrows):
#             f = Fees()
#             f.id = sheet.cell_value(row, 0)
#             f.membership = Membership.objects.get(id=sheet.cell_value(row, 1))
#             f.sub_year = sheet.cell_value(row, 2)
#             f.annual_sub = sheet.cell_value(row, 3)
#             f.monthly_sub = sheet.cell_value(row, 4)
#             f.joining = sheet.cell_value(row, 5)
#             f.save()
#
# def import_itemtypes(book):
#     sheet = book.sheet_by_name('ItemTypes')
#     if sheet.row(0)[0].value.upper() == 'ID':
#         for row in range(1, sheet.nrows):
#             i = ItemType()
#             i.id = sheet.cell_value(row, 0)
#             i.description = sheet.cell_value(row, 1)
#             i.credit = sheet.cell_value(row, 2)
#             i.save()
#
# def import_members_1(book, start, size):
#     ''' Import a batch of members data from the Excel book
#         return start for next batch, 0 if last, -1 if error
#     '''
#     try:
#         ''' We build a reverse dictionary of description : id to
#             eliminate the need to query membership when setting the subscription
#         '''
#         mem_dict = {}
#         for mem in Membership.objects.all():
#             mem_dict[mem.description] = mem.id
#
#         sheet = book.sheet_by_name('Members')
#         if sheet.row(0)[0].value.upper() == 'ID':
#             last_time = False
#             if size > sheet.nrows - start:
#                 size = sheet.nrows - start
#             for row in range(start, start + size):
#                 p = Person()
#                 p.id = int(sheet.cell_value(row, 0))
#                 p.gender = sheet.cell_value(row, 1)[0]
#                 p.first_name = sheet.cell_value(row, 2)
#                 p.last_name = sheet.cell_value(row, 3)
#                 p.mobile_phone = sheet.cell_value(row, 9)
#                 p.email = sheet.cell_value(row, 10)
#                 p.notes = sheet.cell_value(row, 14)
#                 dob = sheet.cell_value(row, 15)
#                 if dob:
#                     date_value = xldate_as_tuple(dob, book.datemode)
#                     p.dob = date(*date_value[:3])
#
#                 btn = sheet.cell_value(row, 25)
#                 if btn:
#                     p.british_tennis = btn
#                 p.membership_id = mem_dict[sheet.cell_value(row, 12)]
#                 p.linked = None
#                 p.state = Person.ACTIVE
#                 if sheet.cell_value(row, 11):
#                     year = int(sheet.cell_value(row, 11))
#                     p.date_joined = date(year, 5, 1)
#                 else:
#                     p.date_joined = date(1900, 5, 1)
#                 if not(p.membership_id == Membership.JUNIOR or p.membership_id == Membership.CADET):
#                     a = Address()
#                     a.address1= sheet.cell_value(row, 4)
#                     a.address2 = sheet.cell_value(row, 5)
#                     a.town = sheet.cell_value(row, 6)
#                     a.post_code = sheet.cell_value(row, 7)
#                     a.home_phone = sheet.cell_value(row, 8)
#                     a.save()
#                     p.address=(a)
#                 p.save()
#                 # For initial load generate and activate a sub for 2014
#                 s = subscription_create(
#                     person=p,
#                     sub_year=2014,
#                     membership_id =p.membership_id,
#                     paid=True,
#                     active=True
#                     )
#             row += 1
#             if row < sheet.nrows:
#                 return row
#             else:
#                 return 0
#     except:
#         return -1
#
# def import_members_2(book):
#     ''' Pass 2
#         Link existing juniors to parent '''
#     try:
#         sheet = book.sheet_by_name('Members')
#         count = 0
#         for row in range(1, sheet.nrows):
#             if sheet.cell_value(row, 17):
#                 child = Person.objects.get(id=sheet.cell_value(row, 0))
#                 parent = Person.objects.get(id=sheet.cell_value(row, 17))
#                 parent.pays_family_bill = True
#                 parent.save()
#                 child.linked = parent
#                 child.address = parent.address
#                 child.save()
#                 count += 1
#         return count
#     except:
#         return -1
#
# def import_members_3(book, size):
#     ''' Pass 3
#         Generate parents for unlinked children '''
#     mem_dict = {}
#     for mem in Membership.objects.all():
#         mem_dict[mem.description] = mem.id
#     count = 0
#
#     if not settings.ON_AZURE:
#         # Reset postgres id
#         cursor = connection.cursor()
#         cursor.execute("SELECT setval('members_person_id_seq', (SELECT MAX(id) FROM members_person)+1)")
#
#     sheet = book.sheet_by_name('Members')
#     errors = []
#     for row in range(1, sheet.nrows):
#         try:
#             membership_id = mem_dict[sheet.cell_value(row, 12)]
#             if membership_id == Membership.JUNIOR or membership_id == Membership.CADET:
#                 if not sheet.cell_value(row, 17):
#                     child = Person.objects.get(id=int(sheet.cell_value(row, 0)))
#                     if not child.linked:
#                         a = None
#                         parent = None
#                         ads = Address.objects.filter(post_code=sheet.cell_value(row, 7), address1 = sheet.cell_value(row, 4))
#                         if ads.count() > 0:
#                             a = ads[0]
#                             parent_set = a.person_set.filter(pays_family_bill = True)
#                             if parent_set.count() > 0:
#                                 parent = parent_set[0]
#                                 if parent.first_name == "Unknown" and sheet.cell_value(row, 19):
#                                     parent.first_name = sheet.cell_value(row, 19)
#                                     parent.last_name = sheet.cell_value(row, 20)
#                                     parent.save()
#                         if not parent:
#                             if not a:
#                                 # Create an address
#                                 a = Address()
#                                 a.address1 = sheet.cell_value(row, 4)
#                                 a.address2 = sheet.cell_value(row, 5)
#                                 a.town = sheet.cell_value(row, 6)
#                                 a.post_code = sheet.cell_value(row, 7)
#                                 a.home_phone = sheet.cell_value(row, 8)
#                                 a.save()
#                             # Create a parent
#                             parent = Person()
#                             parent.gender = "F"
#                             if sheet.cell_value(row, 19):
#                                 parent.first_name = sheet.cell_value(row, 19)
#                                 parent.last_name = sheet.cell_value(row, 20)
#                             else:
#                                 parent.first_name = "Unknown"
#                                 parent.last_name = child.last_name
#                             if sheet.cell_value(row, 21):
#                                 parent.mobile_phone = sheet.cell_value(row, 21)
#                             else:
#                                 parent.mobile_phone = sheet.cell_value(row, 21)
#                             parent.mobile_phone = sheet.cell_value(row, 8)
#                             parent.address = a
#                             parent.membership_id = Membership.NON_MEMBER
#                             parent.pays_family_bill = True
#                             parent.save()
#
#                         child.linked = parent
#                         child.address = parent.address
#                         child.save()
#                         count += 1
#                         if count == size:
#                             break
#         except Exception:
#             errors.append('Row {} for {} of {}'.format(row, child,parent))
#             continue
#     return [count, errors]
         