from os import path
from django import forms
from django.forms import Form, ModelForm
from django.contrib.auth.forms import AuthenticationForm
from django.utils.translation import ugettext_lazy as _
from django.forms.widgets import RadioSelect, CheckboxSelectMultiple, Textarea
from django.core.urlresolvers import reverse_lazy
from django.conf import settings

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Div, Submit, HTML, Button, Row, Field, Fieldset, ButtonHolder
from crispy_forms.bootstrap import AppendedText, PrependedText, FormActions

from .models import (Person, Address, Subscription, Membership, Invoice, InvoiceItem,
                     Payment, ExcelBook, TextBlock)
from .excel import *

class FilterMemberForm(Form):
   
    success_url = '/list'
    helper = FormHelper()
    helper.form_method = 'POST'
    helper.form_class = 'form-horizontal'
    helper.add_input(Submit('submit', 'Go', css_class='btn-group-lg'))

    def __init__(self, *args, **kwargs):
        super(FilterMemberForm, self).__init__(*args, **kwargs)
        memcats = Membership.objects.all()
        self.fields= {}
        for cat in memcats:
            self.fields[str(cat.id)] = forms.BooleanField(required = False, label = cat.description)

class PersonForm(ModelForm):
    ''' Handles creation of a person with new address
        creation of a linked person with linked address
        update of a person '''

    address1 = forms.CharField(max_length=50)
    address2 = forms.CharField(max_length=50, required=False)
    town = forms.CharField(max_length=30)
    post_code = forms.CharField(max_length=15)
    home_phone = forms.CharField(max_length=20, required=False)

    class Meta:
        model = Person
        fields = ['gender',
                'first_name',
                'last_name',
                'dob',
                'state',
                'email',
                'mobile_phone',
                'british_tennis',
                'pays_own_bill',
                'pays_family_bill',
                'date_joined',
                'notes']

    def __init__(self, *args, **kwargs):
        self.link = kwargs.pop('link', None)
        super(PersonForm, self).__init__(*args, **kwargs)
        self.fields['dob'].label = 'Date of birth'
        self.fields['dob'].widget.format = '%d/%m/%Y'
        self.fields['dob'].input_formats = settings.DATE_INPUT_FORMATS
        instance = getattr(self, 'instance', None)
           
        self.helper = FormHelper(self)
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-lg-2'
        self.helper.field_class = 'col-lg-6'
        self.helper.form_method = 'post'
        self.helper.form_show_errors = True
        name_set = Div(
                'first_name',
                'last_name', 
                'gender',
                'dob',
                'state',
            )
        address_set = Fieldset('Address',
                'address1',
                'address2',
                'town',
                'post_code', 
                'home_phone', 
            )
        contact_set = Fieldset('Contact details',        
                'mobile_phone',
                'email'
            )
        other_set = Fieldset('Other information',
                'notes',
                'british_tennis',
                'pays_own_bill',
                'pays_family_bill',
                'date_joined'      
            )       
            
        self.helper.layout = Layout(name_set)
        if not self.link and not instance:
            self.helper.layout.append(address_set)
        self.helper.layout.append(contact_set)
        self.helper.layout.append(other_set)
        self.helper.add_input(Submit('submit', 'Save', css_class='btn-group-lg'))
        self.helper.add_input(Submit('cancel', 'Cancel', css_class='btn-group-lg'))            


    def clean(self):
        ''' remove address errors if linked person or update '''
        super(PersonForm, self).clean()
        if self.link or self.instance:
            del self._errors['address1']
            del self._errors['town']
            del self._errors['post_code']
        return self.cleaned_data

    def save(self, commit=True):
        if 'submit' in self.data:
            person = super(PersonForm, self).save(commit=False)
            if self.link:
                parent = Person.objects.get(pk=self.link)
                person.linked = parent
                person.address = parent.address
            else:
                if not self.instance:
                    address = Address.objects.create(
                        address1 = self.cleaned_data['address1'],
                        address2 = self.cleaned_data['address2'],
                        town = self.cleaned_data['town'],
                        post_code = self.cleaned_data['post_code']
                    )
                    person.address = address
            person.save()

class AddressForm(ModelForm):
    
    class Meta:
        model = Address
        fields = [
                'address1',
                'address2',
                'town',
                'post_code',
                'home_phone'
                ]

    def __init__(self, *args, **kwargs):
        super(AddressForm, self).__init__(*args, **kwargs)      
        self.helper = FormHelper(self)
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-lg-2'
        self.helper.field_class = 'col-lg-6'
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            Fieldset("",
                'address1',
                'address2',
                'town',
                'post_code',
                'home_phone' 
             ),    
             ButtonHolder(
                Submit('submit', 'Save', css_class='btn-group-lg')
                )
             )
              
class JuniorForm(ModelForm):

    success_url = '/list'
    ''' additional fields for this form '''
    parent_gender = forms.ChoiceField(choices=Person.GENDERS, initial='F')
    parent_first_name = forms.CharField(max_length=30)
    parent_last_name = forms.CharField(max_length=30)
    parent_email =  forms.EmailField(max_length=75)
    parent_mobile_phone = forms.CharField(max_length=20, required=False)
    home_phone = forms.CharField(max_length=20, required=False)
    address1 = forms.CharField(max_length=50)
    address2 = forms.CharField(max_length=50, required=False)
    town = forms.CharField(max_length=30)
    post_code = forms.CharField(max_length=15)
    start_date = forms.DateField(widget=forms.widgets.DateInput(format='%d/%m/%Y'))

    def __init__(self, *args, **kwargs):
        super(JuniorForm, self).__init__(*args, **kwargs)
        self.fields['dob'].widget.format = '%d/%m/%Y'
        self.fields['dob'].input_formats = ['%d/%m/%Y']

        self.helper = FormHelper(self)
        self.helper.form_id = 'id-juniorForm'
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-lg-2'
        self.helper.field_class = 'col-lg-6'
        self.helper.form_method = 'post'
        self.helper.form_action = 'junior-create'
        self.helper.form_show_errors = True
        self.helper.form_error_title = 'Errors'
        self.helper.error_text_inline = True
        self.helper.layout = Layout(
            Fieldset(
                'Child details',
                'start_date',
                'gender',
                'first_name',
                'last_name',
                'dob',
                'email',
                'mobile_phone'
            ),
            Fieldset(
                'Parent details',
                'parent_gender',
                'parent_first_name',
                'parent_last_name',
                'parent_email',
                'parent_mobile_phone',
                'home_phone', 
            ),
            Fieldset(
                'Address',
                'address1',
                'address2',
                'town',
                'post_code',   
            ),
            ButtonHolder(
                Submit('submit', 'Save', css_class='btn-group-lg'),
                HTML('<a class="btn btn-default btn-group-lg" href={% url "person-list" %}>Cancel</a>')
            )
        )

    class Meta:
        model = Person
        fields = ['gender',
                'first_name',
                'last_name',
                'dob',
                'email',
                'mobile_phone']

  
    def clean(self):
        self.errorString = "\n".join(self.errors)
        #self.cleaned_data['membership'] = Membership.objects.get(id= int(self.cleaned_data['mem_type']))
        if self.errorString:
            raise forms.ValidationError(self.errorString)      
        return self.cleaned_data    

    def save(self, commit=True):
        ''' Create a child record linked to a parent record '''
        junior = super(JuniorForm, self).save(commit=False)

        address = Address.objects.create(
            address1=self.cleaned_data['address1'],
            address2=self.cleaned_data['address2'],
            town=self.cleaned_data['town'],
            post_code=self.cleaned_data['post_code'],
            home_phone=self.cleaned_data['home_phone']
            )

        parent = Person.objects.create(
            state=Person.ACTIVE,
            gender=self.cleaned_data['parent_gender'],
            first_name=self.cleaned_data['parent_first_name'],
            last_name=self.cleaned_data['parent_last_name'],
            mobile_phone=self.cleaned_data['parent_mobile_phone'],
            email=self.cleaned_data['parent_email'],
            address=address
            )

        junior.state = Person.ACTIVE
        junior.linked = parent
        junior.address = address
        junior.save()
        
        start_date = self.cleaned_data['start_date']
        month = start_date.month
        year = start_date.year
        if month < Subscription.START_MONTH:
            year -= 1
        sub  = Subscription.create(person=junior, sub_year=year, start_month=month, new_member=True)
        sub.activate()
        sub.generate_invoice_items(month)

class PersonLinkForm(Form):
    ''' Link a person to another '''

    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)

    
    def __init__(self, *args, **kwargs):
        super(Form, self).__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-lg-2'
        self.helper.field_class = 'col-lg-6'
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            Fieldset('Select parent / bill payer:',
                'first_name',
                'last_name'
                ),
            ButtonHolder(
                Submit('link', 'Link', css_class='btn-group-lg'),
                Submit('cancel', 'Cancel', css_class='btn-group-lg')
            )
        )

    def clean_first_name(self):
        data = self.cleaned_data['first_name']
        if len(data) < 1:
            raise forms.ValidationError('Specify at least 1 character')
        return data

    def clean_last_name(self):
        data = self.cleaned_data['last_name']
        if len(data) < 1:
            raise forms.ValidationError('Specify at least 1 character')
        return data
    
    def clean(self):
        cleaned_data = super(PersonLinkForm, self).clean()
        matches = Person.objects.filter(
            first_name__startswith=cleaned_data.get('first_name'),
            last_name__startswith=cleaned_data.get('last_name')
            )
        if matches.count() == 1:
            self.person = matches[0]
        elif matches.count() == 0:
            raise forms.ValidationError('No matching person')
        else:
            raise forms.ValidationError('Too many matching people')

class SubscriptionForm(ModelForm):
    
    def __init__(self, *args, **kwargs):
        super(SubscriptionForm, self).__init__(*args, **kwargs)
        instance = getattr(self, 'instance', None)
        self.helper = FormHelper(self)
        self.helper.form_id = 'id-SubscriptionForm'
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-lg-2'
        self.helper.field_class = 'col-lg-6'
        self.helper.form_method = 'post'
        self.helper.form_show_errors = True
        self.helper.form_error_title = 'Errors'
        self.helper.error_text_inline = True
        self.helper.layout = Layout(
            Fieldset(
                'Edit subscription',
                'sub_year',
                'period',
                'start_date',
                'end_date',
                'no_renewal',              
                'membership'
                ),
            HTML("""{% if items %}
            <h3>Subscription cannot be edited unless linked items / invoice are deleted</h3>
            {% for item in items %}
            <ul>{{ item.date|date }} {{ item.description }}
            {% if item.invoice %} Invoice: {{ item.invoice.id }}
            {% else %} Not invoiced {% endif %} </ul>
            {% endfor %}
            {% endif %}""")
           ) 
        self.fields['start_date'].widget.format = '%d/%m/%Y'
        self.fields['end_date'].widget.format = '%d/%m/%Y'
        self.fields['start_date'].input_formats = ['%d/%m/%Y']
        self.fields['end_date'].input_formats = ['%d/%m/%Y']
        
        if instance and instance.pk:
            if instance.invoiceitem_set.all().count() > 0:
                self.helper['sub_year'].wrap(Field, readonly="true")
                self.helper['period'].wrap(Field, readonly="true")
                self.helper['start_date'].wrap(Field, readonly="true")
                self.helper['end_date'].wrap(Field, readonly="true")
                self.helper['no_renewal'].wrap(Field, readonly="true")
                self.helper['membership'].wrap(Field, readonly="true")

                self.has_invoice = False
                for item in instance.invoiceitem_set.all():
                    if item.invoice and item.invoice.state == Invoice.UNPAID:
                        self.has_invoice = True
                        break
                if self.has_invoice:
                    self.helper.add_input(Submit('delete_items', 'Delete item & invoice', css_class='btn-danger'))
                else:
                    self.helper.add_input(Submit('delete_items', 'Delete item', css_class='btn-danger'))
            else:
                self.helper.add_input(Submit('submit', 'Save', css_class='btn-primary'))
        else:
            self.helper.add_input(Submit('submit', 'Save', css_class='btn-primary'))

    class Meta:
        model = Subscription
        fields = ['sub_year', 'start_date', 'end_date', 'period', 'membership', 'no_renewal']


class InvoiceItemForm(ModelForm):

    def __init__(self, *args, **kwargs):
        super(InvoiceItemForm, self).__init__(*args, **kwargs)
        instance = getattr(self, 'instance', None)
        # If you pass FormHelper constructor a form instance
        # It builds a default layout with all its fields
        self.helper = FormHelper(self)
        self.helper.form_id = 'id-InvoiceItemForm'
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-lg-2'
        self.helper.field_class = 'col-lg-6'
        self.helper.form_method = 'post'
        self.helper.form_show_errors = True
        self.helper.form_error_title = 'Errors'
        self.helper.error_text_inline = True
        if instance and instance.id:
            self.helper.add_input(Submit('delete', 'Delete', css_class='btn-danger'))
        self.helper.add_input(Submit('submit', 'Save', css_class='btn-group_lg'))
        self.fields['item_date'].widget.format = '%d/%m/%Y'
        self.fields['item_date'].input_formats = ['%d/%m/%Y']
       
    class Meta:
        model = InvoiceItem
        fields = ['item_type', 'item_date', 'description', 'amount']
        widgets = {'item_date': forms.DateInput(attrs={'class':'datepicker'}),}

class InvoiceSelectForm(Form):
    CHOICES=[(1, 'Invoice reference number'),
             (2, 'Person reference number')]

    ref = forms.IntegerField(label='Reference number')
    choice = forms.ChoiceField(choices=CHOICES, widget=forms.RadioSelect(), label='Select')
    
    def __init__(self, *args, **kwargs):
        super(InvoiceSelectForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-lg-2'
        self.helper.field_class = 'col-lg-6'
        self.helper.form_method = 'post'
        self.helper.add_input(Submit('submit', 'GO', css_class='btn-group-lg'))
        self.initial['choice'] = 1
        
    def clean(self):
        cleaned_data = super(InvoiceSelectForm, self).clean()
        choice = int(cleaned_data.get('choice'))
        ref = int(cleaned_data.get('ref'))
        if choice == 1:
            try:
                inv = Invoice.objects.get(pk=ref)
            except:
                raise forms.ValidationError("Invoice with id {} not found".format(ref))
        elif choice == 2:
            try:
                p = Person.objects.get(pk=ref)
            except:
                raise forms.ValidationError("Person with id {} not found".format(ref))

class PaymentForm(ModelForm):

    def __init__(self, *args, **kwargs):
        ''' optional kwarg amount sets the default amount '''
        amount = kwargs.pop('amount', None)
        super(PaymentForm, self).__init__(*args, **kwargs)
        if amount:
            self.fields['amount'].initial = amount
        self.helper = FormHelper(self)
        self.helper.form_id = 'id-InvoiceItemForm'
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-lg-2'
        self.helper.field_class = 'col-lg-6'
        self.helper.form_method = 'post'
        self.helper.form_show_errors = True
        self.helper.form_error_title = 'Errors'
        self.helper.error_text_inline = True
        self.helper.add_input(Submit('submit', 'Save', css_class='btn-group-lg'))
    
    class Meta:
        model = Payment
        fields = ['type', 'reference', 'amount']

class TextBlockForm(ModelForm):

    def __init__(self, *args, **kwargs):
        super(TextBlockForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.field_class = 'input-xlarge'
        self.helper.form_method = 'post'
        self.helper.form_show_errors = True
        self.helper.form_error_title = 'Errors'
        self.helper.error_text_inline = True
        self.helper.add_input(Submit('submit', 'Save', css_class='btn-group-lg'))

    class Meta:
        model = TextBlock
        fields = ['name', 'text']
        widgets = {
            'text': Textarea(attrs={'cols': 20, 'rows': 30, 'class': 'col-md'
            })}

class XlsInputForm(Form):
    IMPORT_FILE_TYPES = ['.xls', ]
    BASE = 0
    MEMBERS = 1
    ITEMS = 2
    BACKUP = 3
    CHOICES=[(BASE, 'Basic tables'),
             (MEMBERS, 'Members file'),
             (ITEMS, 'Invoice items'),
             (BACKUP, 'Backup file')
            ]

    input_excel = forms.FileField(required=True, label=u"Select the Excel file")
    sheet_type = forms.ChoiceField(choices=CHOICES, widget=forms.RadioSelect())
    batch_size = forms.IntegerField(label=u"Batch size")
    
    def __init__(self, *args, **kwargs):
        super(XlsInputForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-lg-2'
        self.helper.field_class = 'col-lg-6'
        self.helper.form_method = 'post'
        self.helper.add_input(Submit('submit', 'Start', css_class='btn-group-lg'))
        self.initial['sheet_type'] = XlsInputForm.MEMBERS
        self.initial['batch_size'] = 100

    def clean_input_excel(self):
        input_excel = self.cleaned_data['input_excel']
        extension = path.splitext( input_excel.name )[1]
        if not (extension in XlsInputForm.IMPORT_FILE_TYPES):
            raise forms.ValidationError( u'%s is not a valid excel file' % extension )
        else:
            return input_excel

class XlsMoreForm(Form):

    def __init__(self, *args, **kwargs):
        super(XlsMoreForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_class = 'form-horizontal'
        self.helper.form_method = 'post'
        self.helper.add_input(Submit('submit', 'Next', css_class='btn-group-lg'))

class GenericMoreForm(Form):
    
    def __init__(self, *args, **kwargs):
        super(GenericMoreForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_class = 'form-horizontal'
        self.helper.form_method = 'post'
        self.helper.add_input(Submit('submit', 'Go', css_class='btn-group-lg'))

class BootstrapAuthenticationForm(AuthenticationForm):
    """Authentication form which uses boostrap CSS."""
    username = forms.CharField(max_length=254,
                               widget=forms.TextInput({
                                   'class': 'form-control',
                                   'placeholder': 'User name'}))
    password = forms.CharField(label=_("Password"),
                               widget=forms.PasswordInput({
                                   'class': 'form-control',
                                   'placeholder':'Password'}))

class SelectSheetsForm(Form):
    
    def __init__(self, *args, **kwargs):
        super(SelectSheetsForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_class = 'form-horizontal'
        self.helper.form_method = 'post'
        self.helper.add_input(Submit('submit', 'Import', css_class='btn-group-lg'))
        
        my_book = ExcelBook.objects.all()[0]
        with open_excel_workbook(my_book.file) as book:
            for sheet_name in book.sheet_names():
                self.fields[sheet_name] = forms.BooleanField(required = False)
