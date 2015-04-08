from django.http import HttpResponse
from django.db.models.loading import get_model
from django.db import connection, transaction
from django.conf import settings
from datetime import date, datetime
from xlrd import open_workbook, xldate_as_tuple
from xlwt import Workbook

from members.models import (Membership, Person, Address, Fees, Subscription, ItemType,
                            Invoice, InvoiceItem)


def open_local_workbook():
    book = open_workbook('transaction.xls')


def open_excel_workbook(input_file):
    book = open_workbook(file_contents=input_file.read())
    return book


def import_items(sheet):
    ''' Import invoice items an Excel sheets in the book
        Return [count, errorlist] 
    '''
    errors=[]
    col_id = -1
    col_item_id = -1
    col_amount = -1
    col_description = -1
    row = 0
    for col in range(0, sheet.ncols):
        value = sheet.cell(row,col).value.upper() 
        if value == u'ID':
            col_id = col
        elif value == u'CODE':
            col_item_id = col
        elif value == u'AMOUNT':
            col_amount = col
        elif value == u'DESCRIPTION':
            col_description = col

    if col_id > -1 and col_item_id > -1 and col_amount > -1:  
        count=0
        for row in range(1, sheet.nrows):
            try:
                if sheet.cell_value(row, col_id) <> u"":
                    person_id = int(sheet.cell_value(row, col_id))                 
                    amount = sheet.cell_value(row, col_amount)
                    item_id = int(sheet.cell_value(row, col_item_id))
                    description = u''
                    if col_description > 0:
                        description = sheet.cell_value(row, col_description)
                    if description == u'':
                        description = ItemType.objects.get(pk=item_id).description
                    new_item = InvoiceItem(person_id=person_id,
                                            item_type_id=item_id,
                                            description=description,
                                            amount=amount)
                    count += 1
                    new_item.save()  
            except Exception, e:
                errors.append(repr(e) + 'Error on row {}' .format(row))
                continue  
        return [count, errors]
    else:
        errors.append('Missing columns')
        return[0, errors]

            
def import_base_tables(book):
    try:
        import_categories(book)
        import_fees(book)
        import_itemtypes(book)
        return True
    except:
        return false
    return True

def import_categories(book):
    sheet = book.sheet_by_name('Categories')
    if sheet.row(0)[0].value.upper() == u'ID':
        for row in range(1, sheet.nrows):
            id = sheet.cell_value(row, 0)
            description = sheet.cell_value(row, 1)
            Membership.create(id, description)

def import_fees(book):
    sheet = book.sheet_by_name('Fees')
    if sheet.row(0)[0].value.upper() == u'ID':
        for row in range(1, sheet.nrows):
            f = Fees()
            f.id = sheet.cell_value(row, 0)
            f.membership = Membership.objects.get(id=sheet.cell_value(row, 1))
            f.sub_year = sheet.cell_value(row, 2)
            f.annual_sub = sheet.cell_value(row, 3)
            f.monthly_sub = sheet.cell_value(row, 4)
            f.joining = sheet.cell_value(row, 5)
            f.save()

def import_itemtypes(book):    
    sheet = book.sheet_by_name('ItemTypes')
    if sheet.row(0)[0].value.upper() == u'ID':
        for row in range(1, sheet.nrows):
            i = ItemType()
            i.id = sheet.cell_value(row, 0)
            i.description = sheet.cell_value(row, 1)
            i.credit = sheet.cell_value(row, 2)
            i.save()

def import_members_1(book, start, size):
    ''' Import a batch of members data from the Excel book
        return start for next batch, 0 if last, -1 if error
    '''
    try:
        ''' We build a reverse dictionary of description : id to 
            eliminate the need to query membership when setting the subscription
        '''  
        mem_dict = {}
        for mem in Membership.objects.all():
            mem_dict[mem.description] = mem.id 
        
        sheet = book.sheet_by_name('Members')
        if sheet.row(0)[0].value.upper() == u'ID':
            last_time = False
            if size > sheet.nrows - start:
                size = sheet.nrows - start 
            for row in range(start, start + size):
                p = Person()
                p.id = int(sheet.cell_value(row, 0))
                p.gender = sheet.cell_value(row, 1)[0]
                p.first_name = sheet.cell_value(row, 2)
                p.last_name = sheet.cell_value(row, 3)
                p.mobile_phone = sheet.cell_value(row, 9)
                p.email = sheet.cell_value(row, 10)
                p.notes = sheet.cell_value(row, 14)
                dob = sheet.cell_value(row, 15)
                if dob:
                    date_value = xldate_as_tuple(dob, book.datemode)
                    p.dob = date(*date_value[:3])
                
                btn = sheet.cell_value(row, 25)
                if btn:
                    p.british_tennis = btn
                p.membership_id = mem_dict[sheet.cell_value(row, 12)]
                p.linked = None
                p.state = Person.ACTIVE
                if sheet.cell_value(row, 11):
                    year = int(sheet.cell_value(row, 11))
                    p.date_joined = date(year, 5, 1)
                else:
                    p.date_joined = date(1900, 5, 1)
                if not(p.membership_id == Membership.JUNIOR or p.membership_id == Membership.CADET):
                    a = Address()
                    a.address1= sheet.cell_value(row, 4)
                    a.address2 = sheet.cell_value(row, 5)
                    a.town = sheet.cell_value(row, 6)
                    a.post_code = sheet.cell_value(row, 7)
                    a.home_phone = sheet.cell_value(row, 8)
                    a.save()
                    p.address=(a)         
                p.save()
                # For initial load generate and activate a sub for 2014
                s = Subscription.create(
                    person=p,
                    sub_year=2014,
                    membership_id =p.membership_id,
                    paid=True,
                    active=True
                    )
            row += 1
            if row < sheet.nrows:
                return row
            else:
                return 0
    except:
        return -1

def import_members_2(book):
    ''' Pass 2 
        Link existing juniors to parent '''
    try:
        sheet = book.sheet_by_name('Members')
        count = 0
        for row in range(1, sheet.nrows):
            if sheet.cell_value(row, 17):
                child = Person.objects.get(id=sheet.cell_value(row, 0))
                parent = Person.objects.get(id=sheet.cell_value(row, 17))
                parent.pays_family_bill = True  
                parent.save()
                child.linked = parent
                child.address = parent.address
                child.save()
                count += 1  
        return count
    except:
        return -1

def import_members_3(book, size):
    ''' Pass 3 
        Generate parents for unlinked children '''
    mem_dict = {}
    for mem in Membership.objects.all():
        mem_dict[mem.description] = mem.id 
    count = 0

    if not settings.ON_AZURE:
        # Reset postgres id
        cursor = connection.cursor()
        cursor.execute("SELECT setval('members_person_id_seq', (SELECT MAX(id) FROM members_person)+1)")

    sheet = book.sheet_by_name('Members')
    errors = []
    for row in range(1, sheet.nrows):
        try:
            membership_id = mem_dict[sheet.cell_value(row, 12)]
            if membership_id == Membership.JUNIOR or membership_id == Membership.CADET:
                if not sheet.cell_value(row, 17):
                    child = Person.objects.get(id=int(sheet.cell_value(row, 0)))
                    if not child.linked:
                        a = None
                        parent = None
                        ads = Address.objects.filter(post_code=sheet.cell_value(row, 7), address1 = sheet.cell_value(row, 4))                  
                        if ads.count() > 0:
                            a = ads[0]
                            parent_set = a.person_set.filter(pays_family_bill = True)
                            if parent_set.count() > 0:
                                parent = parent_set[0]
                                if parent.first_name == "Unknown" and sheet.cell_value(row, 19):
                                    parent.first_name = sheet.cell_value(row, 19)
                                    parent.last_name = sheet.cell_value(row, 20)
                                    parent.save()
                        if not parent: 
                            if not a:
                                # Create an address
                                a = Address()
                                a.address1 = sheet.cell_value(row, 4)
                                a.address2 = sheet.cell_value(row, 5)
                                a.town = sheet.cell_value(row, 6)
                                a.post_code = sheet.cell_value(row, 7)
                                a.home_phone = sheet.cell_value(row, 8)
                                a.save()
                            # Create a parent
                            parent = Person()
                            parent.gender = "F"
                            if sheet.cell_value(row, 19):
                                parent.first_name = sheet.cell_value(row, 19)
                                parent.last_name = sheet.cell_value(row, 20)
                            else:
                                parent.first_name = "Unknown"
                                parent.last_name = child.last_name
                            if sheet.cell_value(row, 21):
                                parent.mobile_phone = sheet.cell_value(row, 21)
                            else:
                                parent.mobile_phone = sheet.cell_value(row, 21)
                            parent.mobile_phone = sheet.cell_value(row, 8)   
                            parent.address = a
                            parent.membership_id = Membership.NON_MEMBER 
                            parent.pays_family_bill = True                  
                            parent.save()

                        child.linked = parent
                        child.address = parent.address
                        child.save()
                        count += 1
                        if count == size:
                            break
        except Exception, e:
            errors.append(repr(e) + 'Row {} for {} of {}'.format(row, child,parent))
            continue
    return [count, errors]


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
    my_model = get_model ('members', model_name)
    
    # get list of column names including foreign keys with _id
    # but ignore creation_date or update_date
    columns = []
    for field in my_model._meta.fields:
        if field.name <> 'creation_date' and field.name <> 'update_date':
            columns.append(field.attname)
    
    # write a header row
    for col_num in xrange(len(columns)):
        sheet.write(0, col_num, columns[col_num].decode('utf-8','ignore')) 
    
    # write all objects
    row_num=0
    for object in my_model.objects.all():
        row_num += 1
        for col_num in xrange(len(columns)): 
                      
            sheet.write(row_num, col_num, getattr(object, columns[col_num])) 
        
    


def export_invoices():
    response = HttpResponse(content_type='application/vnd.ms-excel')
    response['Content-Disposition'] = 'attachment; filename=Invoices.xls'
    book = Workbook(encoding='utf-8')
    sheet = book.add_sheet('Invoices')
    invs = Invoice.objects.all()

    columns = [
        'Id',
        'State',   
        'Person_id',
        'Total', 
        'Emailed', 
        'Posted',      
        'Reference'
    ]
    for col_num in xrange(len(columns)):
        sheet.write(0, col_num, columns[col_num].decode('utf-8','ignore'))
                             
    row_num = 0
    for inv in invs:
        row_num += 1
        row = [
        inv.id,
        inv.state,
        inv.person_id,
        inv.total,
        inv.email_count,
        inv.posted_count,         
        inv.reference
        ]
        for col_num in xrange(len(row)):
            sheet.write(row_num, col_num, row[col_num].decode('utf-8','ignore'))  
      
    book.save(response)
    return response  

def export_members():
    response = HttpResponse(content_type='application/vnd.ms-excel')
    response['Content-Disposition'] = 'attachment; filename=Members.xls'
    book = Workbook(encoding='utf-8')
    sheet = book.add_sheet('Members')
    people = Person.objects.all()  

    columns = [
        'id',
        'gender',   
        'first_name',
        'last_name', 
        'mobile_phone', 
        'email',      
        'dob',
        'british_tennis',
        'notes',
        'pays_own_bill',
        'pays_family_bill', 
        'state',
        'membership_id',
        'linked_id',
        'address_id'
        ]
    for col_num in xrange(len(columns)):
        sheet.write(0, col_num, columns[col_num].decode('utf-8','ignore'))     
        
    row_num = 0
    for person in people:
        row_num += 1
        row = [
        person.id,
        person.gender,   
        person.first_name,
        person.last_name, 
        person.mobile_phone, 
        person.email,      
        person.dob,
        person.british_tennis,
        person.notes,
        person.pays_own_bill,
        person.pays_family_bill, 
        person.state,
        person.membership_id,
        person.linked_id,
        person.address_id
        ]
        for col_num in xrange(len(row)):
            sheet.write(row_num, col_num, row[col_num]) 
    book.save(response)
    return response   

       