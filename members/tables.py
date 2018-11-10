import django_tables2 as tables
from django_tables2.utils import A
from django.conf import settings
from django.utils.html import format_html
from members.models import Person, Subscription, Invoice, InvoiceItem, Payment, Membership, Group


class PersonTable(tables.Table):
    class Meta:
        model = Person
        fields = ('first_name', 'last_name', 'email')
        sequence = ('selection', '...')
        attrs = {'class': 'table table-condensed'}

    description = tables.Column(accessor='sub.membership_fulldescription',
                                verbose_name='Membership',
                                order_by='membership.description',
                                orderable=True)
    edit = tables.LinkColumn('person-detail', text='Edit', args=[A('pk')], orderable=False)
    selection = tables.CheckBoxColumn(accessor='pk',
                                      attrs={"th__input": {"onclick": "toggle(this)"},
                                             "td__input": {"onclick": "countChecked()", "class": "rowcheckbox"}
                                             },
                                      orderable=False)


class GroupTable(tables.Table):
    class Meta:
        model = Group
        fields = ('slug', 'description')
        attrs = {'class': 'table table-condensed'}

    count = tables.Column(accessor='person_set.count', verbose_name='Members', orderable=False)
    edit = tables.LinkColumn('group-detail', text='View', args=[A('pk')], orderable=False)


class ApplicantTable(tables.Table):
    class Meta:
        model = Person
        fields = ('first_name', 'last_name', 'date_joined', 'email', 'linked')
        attrs = {'class': 'table table-condensed'}

    membership = tables.Column(accessor='membership.description', verbose_name='Membership', orderable=True)
    edit = tables.LinkColumn('person-detail', text='Edit', args=[A('pk')], orderable=False)


class SubsTable(tables.Table):
    class Meta:
        model = Subscription
        fields = ('person_member.first_name', 'person_member.last_name', 'person_member.email',
                  'description', 'person_member.dob', 'paid')
        sequence = ('selection', '...')
        attrs = {'class': 'table table-condensed'}

    description = tables.Column(accessor='membership_fulldescription',
                                verbose_name='Membership',
                                order_by='membership.description',
                                orderable=True)
    edit = tables.LinkColumn('person-detail', text='Edit', args=[A('person_member.id')], orderable=False)
    selection = tables.CheckBoxColumn(accessor='person_member.id', verbose_name='Select',
                                      attrs={"th__input": {"onclick": "toggle(this)"},
                                             "td__input": {"onclick": "countChecked()", "class": "rowcheckbox"}
                                             },
                                      orderable=False)


class InvoiceTable(tables.Table):
    class Meta:
        model = Invoice
        fields = ('id', 'person.first_name', 'person.last_name', 'person.state',
                  'person.membership.description', 'age', 'state', 'special_case', 'note')
        sequence = ('selection', 'id', 'person.first_name', 'person.last_name', 'person.state', 'parent', '...')
        attrs = {'class': 'table table-condensed'}

    payment = tables.Column(accessor='payment_state_text')
    id = tables.LinkColumn('invoice-detail', verbose_name="Number", args=[A('id')])
    created = tables.DateColumn(settings.DATE_FORMAT, accessor='creation_date')
    updated = tables.DateColumn(settings.DATE_FORMAT, accessor='update_date')
    total = tables.Column(attrs={'td': {'style': 'text-align: right;'}})
    selection = tables.CheckBoxColumn(accessor='id',
                                      attrs={"th__input": {"onclick": "toggle(this)"},
                                             "td__input": {"onclick": "countChecked()", "class": "rowcheckbox"}
                                             },
                                      orderable=False)
    age = tables.Column(accessor='age', order_by='-creation_date')
    parent = tables.BooleanColumn(accessor='person.is_active_parent', verbose_name='Parent')
    special_case = tables.BooleanColumn(verbose_name='Flag')
    note = tables.BooleanColumn(default="")

    def render_special_case(self, value):
        if value:
            return format_html('<span class="label label-danger">Paid</span>')
        return ''

    def render_note(self, value):
        if value:
            return format_html('<span class="label label-warning">Note</span>')
        return ''


class InvoiceItemTable(tables.Table):
    class Meta:
        model = InvoiceItem
        fields = ('id', 'person.first_name', 'person.last_name', 'item_type.description', 'description',
                  'paid', 'invoice_id')
        sequence = ('id', 'year', '...')
        attrs = {'class': 'table table-condensed'}

    id = tables.LinkColumn('item-detail', verbose_name="Number", args=[A('id')])
    year = tables.Column(verbose_name="Year", accessor='invoice.membership_year')
    created = tables.DateColumn(settings.DATE_FORMAT, verbose_name="Created", accessor='creation_date')
    amount = tables.Column(attrs={'td': {'style': 'text-align: right;'}})


class PaymentTable(tables.Table):
    class Meta:
        model = Payment
        fields = ('update_date', 'person.first_name', 'person.last_name', 'person.membership.description', 'type',
                  'amount', 'state', 'banked', 'invoice')
        attrs = {'class': 'table table-condensed'}

    amount = tables.Column(attrs={'td': {'style': 'text-align: right;'}})
    invoice = tables.LinkColumn('invoice-detail', text=lambda r: r.invoice_id, args=[A('invoice_id')],
                                orderable=False)
    edit = tables.LinkColumn('payment-detail', text='Edit', args=[A('id')], orderable=False)


class MembershipTable(tables.Table):
    class Meta:
        model = Membership
        attrs = {'class': 'table table-condensed'}
    edit = tables.LinkColumn('categories-update', text='Edit', args=[A('id')], orderable=False)