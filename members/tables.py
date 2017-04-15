import django_tables2 as tables
from django_tables2.utils import A
from django.conf import settings
from members.models import Person, Subscription, Invoice, InvoiceItem, Payment

class PersonTable(tables.Table):
    
    class Meta:
        model = Person
        fields = ('first_name', 'last_name', 'email')
        attrs = {'class': 'table table-condensed'} 

    description = tables.Column(accessor='membership_fulldescription',
                                verbose_name='Membership',
                                order_by='membership.description',
                                orderable=True)
    edit = tables.LinkColumn('person-detail', text='Edit', args=[A('pk')], orderable=False)
    selection = tables.CheckBoxColumn(accessor='pk',
                                      attrs={ "th__input": {"onclick": "toggle(this)"},
                                              "td__input": {"onclick": "countChecked()",
                                                            "class": "rowcheckbox"}
                                            },
                                      orderable=False)


class SubsTable(tables.Table):
    
    class Meta:
        model = Subscription
        fields = ('person_member.first_name', 'person_member.last_name', 'person_member.email',
                  'description',  'person_member.dob', 'paid')
        attrs = {'class': 'table table-condensed'} 

    description = tables.Column(accessor='membership_fulldescription',
                                verbose_name='Membership',
                                order_by='membership.description',
                                orderable=True)

    edit = tables.LinkColumn('person-detail', text='Edit', args=[A('person_member.id')], orderable=False)
    #dob = tables.columns.DateColumn(settings.DATE_FORMAT, accessor='person_member.dob')
    selection = tables.CheckBoxColumn(accessor='person_member.id',
                                      attrs={ "th__input": {"onclick": "toggle(this)"},
                                              "td__input": {"onclick": "countChecked()",
                                                            "class": "rowcheckbox"}
                                            },
                                      orderable=False)


class InvoiceTable(tables.Table):

    class Meta:
        model = Invoice
        fields = ('creation_date','update_date', 'person.first_name', 'person.last_name', 'person.membership.description','email_count','total', 'state')
        attrs = {'class': 'table table-condensed'} 
    
    total = tables.Column(attrs={'td':{'style':'text-align: right;'}})
    edit = tables.LinkColumn('invoice-detail', text='Edit', args=[A('id')], orderable=False)


class InvoiceItemTable(tables.Table):
          
    class Meta:
        model = InvoiceItem
        fields = ('person.fullname', 'invoice.membership_year', 'creation_date', 'item_type.description', 'description', 'amount', 'invoice.id', 'paid')
        attrs = {'class': 'table table-condensed'} 

    amount = tables.Column(attrs={'td':{'style':'text-align: right;'}})
    edit = tables.LinkColumn('item-detail', text='Edit', args=[A('id')], orderable=False)


class PaymentTable(tables.Table):

    class Meta:
        model = Payment
        fields = ('update_date', 'person.first_name', 'person.last_name', 'person.membership.description', 'type', 'amount', 'banked','invoice')
        attrs = {'class': 'table table-condensed'} 

    amount = tables.Column(attrs={'td':{'style':'text-align: right;'}})
    invoice = tables.LinkColumn('invoice-detail', text ='Invoice', args=[A('pk')], orderable=False)
    edit = tables.LinkColumn('payment-detail', text='Edit', args=[A('id')], orderable=False)