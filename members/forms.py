from os import path
from datetime import date, datetime, timedelta
from django import forms
from django.forms import Form, ModelForm, ModelMultipleChoiceField, HiddenInput
from django.forms.widgets import RadioSelect, CheckboxSelectMultiple, Textarea
from django.contrib.auth.forms import AuthenticationForm
from django.utils.translation import ugettext_lazy as _
from django.utils.safestring import mark_safe
from django.db.models import Q
from django.core.urlresolvers import reverse_lazy
from django.conf import settings
from django.forms.extras import SelectDateWidget
from django.template.defaultfilters import slugify
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Div, Submit, HTML, Button, Row, Field, Fieldset, ButtonHolder, BaseInput
from crispy_forms.bootstrap import AppendedText, PrependedText, FormActions, InlineCheckboxes

from .widgets import MonthYearWidget
from .models import (Person, Address, Subscription, Membership, Invoice, InvoiceItem,
                     Payment, CreditNote, ExcelBook, TextBlock, Group, Settings)
from .excel import *

# 
TEMPLATE_PACK = getattr(settings, 'CRISPY_TEMPLATE_PACK', 'bootstrap')
class SubmitButton(BaseInput):
    ''' Replacement for Submit that allows button class to be defined
        https://github.com/maraujop/django-crispy-forms/issues/242
    '''
    input_type = 'submit'
    field_classes = 'button' if TEMPLATE_PACK == 'uni_form' else 'btn' #removed btn-primary

def DefaultHelper(form):
    helper = FormHelper(form)
    helper.form_class = 'form-horizontal'
    helper.label_class = 'col-lg-2'
    helper.field_class = 'col-lg-6'
    helper.form_method = 'post'
    return helper

class HorizontalRadioRenderer(forms.RadioSelect.renderer):
  def render(self):
    return mark_safe(u'\n'.join([u'%s\n' % w for w in self]))

class FilterMemberForm(Form):
    
    success_url = '/list/'
    helper = FormHelper()
    helper.form_method = 'POST'
    helper.form_class = 'form-horizontal'
    helper.add_input(SubmitButton('submit', 'Go', css_class='btn-primary'))

    def __init__(self, *args, **kwargs):
        super(FilterMemberForm, self).__init__(*args, **kwargs)
        memcats = Membership.objects.all()
        self.fields= {}
        for cat in memcats:
            self.fields[str(cat.id)] = forms.BooleanField(required = False, label = cat.description)

class FilterMemberAjaxForm(Form):
    categories = forms.ChoiceField()

    def __init__(self, *args, **kwargs):
        super(FilterMemberAjaxForm, self).__init__(*args, **kwargs)
        self.fields['categories'].choices = Membership.FILTER_CHOICES + [
            (x.id, x.description) for x in Membership.objects.all()
            ]

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
                'notes']

    def __init__(self, *args, **kwargs):
        self.link = kwargs.pop('link', None)
        super(PersonForm, self).__init__(*args, **kwargs)
        if self.link:
            self.parent = Person.objects.get(pk=self.link)
            self.fields['last_name'].initial = self.parent.last_name
            self.fields['mobile_phone'].initial = self.parent.mobile_phone
            self.fields['email'].initial = self.parent.email
        self.updating =False
        instance = getattr(self, 'instance', None)
        self.updating = instance and instance.id

        self.fields['dob'].label = 'Date of birth'
        self.fields['dob'].widget.format = settings.DATE_INPUT_FORMATS[0]
        self.fields['dob'].input_formats = settings.DATE_INPUT_FORMATS

        if self.link:
            self.fields['email'].required = False  
             
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
            )       
            
        self.helper.layout = Layout(name_set)

        if not self.link and not self.updating:
            self.helper.layout.append(address_set)
        self.helper.layout.append(contact_set)
        self.helper.layout.append(other_set)
        self.helper.add_input(SubmitButton('submit', 'Save', css_class='btn-primary'))
        if not self.updating:
            self.helper.add_input(SubmitButton('submit_sub', 'Save and add sub', css_class='btn-primary'))
        self.helper.add_input(SubmitButton('cancel', 'Cancel', css_class='btn-default'))

    def clean(self):
        ''' remove address errors if linked person or update '''
        super(PersonForm, self).clean()
        if not self.updating:
            self.cleaned_data['date_joined'] = date.today()
        if self.link or self.updating:
            del self._errors['address1']
            del self._errors['town']
            del self._errors['post_code']
        return self.cleaned_data

    def save(self, commit=True):
        self.person = super(PersonForm, self).save(commit=False)
        if not self.updating:
            self.person.date_joined = date.today()
        if self.link:
            self.person.linked = self.parent
            self.person.address = self.parent.address
        else:
            if not self.updating:
                address = Address.objects.create(
                    address1 = self.cleaned_data['address1'],
                    address2 = self.cleaned_data['address2'],
                    town = self.cleaned_data['town'],
                    post_code = self.cleaned_data['post_code']
                )
                self.person.address = address
        self.person.save()

class PersonSearchForm(Form):
    first_name = forms.CharField(max_length=30)
    last_name = forms.CharField(max_length=30)
     
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
                SubmitButton('submit', 'Save', css_class='btn-primary'),
                SubmitButton('cancel', 'Cancel', css_class='btn-default')
                )
             )
             
class JuniorForm(ModelForm):

    class Meta:
        model = Person
        fields = ['gender',
                'first_name',
                'last_name',
                'dob',
                'notes'
                ]

    child_email = forms.EmailField(max_length=75, required=False)
    child_mobile = forms.CharField(max_length=20, required=False)
    parent_gender = forms.ChoiceField(choices=Person.GENDERS, initial='F')
    parent_first_name = forms.CharField(max_length=30)
    parent_last_name = forms.CharField(max_length=30)
    parent_email =  forms.EmailField(max_length=75)
    parent_mobile = forms.CharField(max_length=20, required=False)
    home_phone = forms.CharField(max_length=20, required=False)
    address1 = forms.CharField(max_length=50)
    address2 = forms.CharField(max_length=50, required=False)
    town = forms.CharField(max_length=30)
    post_code = forms.CharField(max_length=15)

    def __init__(self, *args, **kwargs):
        super(JuniorForm, self).__init__(*args, **kwargs)

        self.fields['dob'].widget.format = settings.DATE_INPUT_FORMATS[0]
        self.fields['dob'].input_formats = settings.DATE_INPUT_FORMATS
        self.fields['dob'].label = "Date of birth"
        self.fields['dob'].required = True
        
        self.helper = FormHelper(self)
        self.helper.form_id = 'id-juniorForm'
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-lg-2'
        self.helper.field_class = 'col-lg-6'
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            Fieldset('Child details',
                'gender',
                'first_name',
                'last_name',
                'dob',
                'child_email',
                'child_mobile'
            ),
            Fieldset('Parent details',
                'parent_gender',
                'parent_first_name',
                'parent_last_name',
                'parent_email',
                'parent_mobile',
                'home_phone', 
            ),
            Fieldset('Address',
                'address1',
                'address2',
                'town',
                'post_code',   
            ),
            Fieldset('Notes',
                'notes'
            ),
            ButtonHolder(
                SubmitButton('submit', 'Save', css_class='btn-primary'),
                SubmitButton('cancel', 'Cancel', css_class='btn-default')
            )
        )

    def clean(self):
        self.cleaned_data = super(JuniorForm, self).clean()

        if (len(self.cleaned_data['parent_mobile']) == 0 and
            len(self.cleaned_data['home_phone']) == 0):
            raise forms.ValidationError('Please enter at least one of home phone or mobile phone')  
        if len(self.cleaned_data['child_email']) > 0:
            self.cleaned_data['email'] = self.cleaned_data['child_email']
        else:
            self.cleaned_data['email'] = self.cleaned_data['parent_email']
        if len(self.cleaned_data['child_mobile']) > 0:
            self.cleaned_data['mobile'] = self.cleaned_data['child_mobile']
        else:
            self.cleaned_data['mobile'] = self.cleaned_data['parent_mobile']

        #self.errorString = "\n".join(self.errors)
        #if self.errorString:
        #    raise forms.ValidationError(self.errorString)      
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
            mobile_phone=self.cleaned_data['parent_mobile'],
            email=self.cleaned_data['parent_email'],
            address=address
            )
        junior.state = Person.ACTIVE
        junior.linked = parent
        junior.address = address
        junior.save()
        self.junior = junior

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
                SubmitButton('link', 'Link', css_class='btn-primary'),
                SubmitButton('cancel', 'Cancel', css_class='btn-default')
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

class FeesForm(ModelForm):
    class Meta:
        model = Fees
        fields = [
                'annual_sub',
                'monthly_sub',
                'joining_fee'
                ]

    def __init__(self, *args, **kwargs):
        year = kwargs.pop('year', None)              
        super(FeesForm, self).__init__(*args, **kwargs)
        instance = getattr(self, 'instance', None)
        self.updating = False
        if instance and instance.id:
            self.updating = True
        self.helper = FormHelper(self)
        self.helper.form_id = 'id-FeesForm'
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-lg-2'
        self.helper.field_class = 'col-lg-6'
        self.helper.form_method = 'post'
        self.helper.add_input(SubmitButton('submit', 'Save', css_class='btn-primary'))
        self.helper.add_input(SubmitButton('cancel', 'Cancel', css_class='btn-default'))
        message = "{}  {}".format(instance.sub_year, instance.membership.description)
        self.helper.layout = Layout(
            Fieldset(
                message,
                'annual_sub',
                'monthly_sub',
                'joining_fee'
                )
            )

    def clean(self):
        cleaned_data = super(FeesForm, self).clean()
        annual = cleaned_data.get('annual_sub')
        monthly = cleaned_data.get('monthly_sub')
        joining = cleaned_data.get('joining_fee')
        if joining:
            if joining < 0:
                raise forms.ValidationError('Value cannot be negative')
        else:
            joining = 0


class SubscriptionForm(ModelForm):
    membership_id = forms.ChoiceField()
    
    def __init__(self, *args, **kwargs):
        person_id = kwargs.pop('person_id', None)              
        super(SubscriptionForm, self).__init__(*args, **kwargs)
        person = Person.objects.get(pk=person_id)
        instance = getattr(self, 'instance', None)
        self.updating = False
        if instance and instance.id: 
            self.updating = True
        self.helper = FormHelper(self)
        self.helper.form_id = 'id-SubscriptionForm'
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-lg-2'
        self.helper.field_class = 'col-lg-6'
        self.helper.form_method = 'post'
        message = 'New subscription'
        if person.subscription_set.count() > 0:
            message += ' (add to history)'
        if self.updating:
            
            if instance.has_paid_invoice():
                message = 'This sub is linked to a paid invoice and cannot be changed'
            elif instance.has_unpaid_invoice():
                message = 'This sub cannot be changed until the linked unpaid invoice is deleted'
            elif instance.has_items():
                message = 'This sub cannot be changed until the linked unbilled item is deleted'
            else:
                message = 'Change subscription'
        self.helper.layout = Layout(
            Fieldset(
                message,
                'membership_id',
                'sub_year',
                'period',
                'start_date',
                'end_date',
                'no_renewal',              
                ),
            HTML("""
                {% for item in items %}
                    {{ item.item_date|date }} {{ item.description}}
                    {% if item.payment %}
                        {{ item.payment_id }}
                    {% else %}
                        Unpaid
                    {% endif %}          
                    {{ item.amount }}
                {% endfor item %}
                <br />
            """)
           ) 
        self.fields['start_date'].widget = MonthYearWidget()
        self.fields['start_date'].input_formats = settings.DATE_INPUT_FORMATS
        
        self.fields['end_date'].widget = MonthYearWidget()
        self.fields['end_date'].input_formats = settings.DATE_INPUT_FORMATS
        
        now = date.today()
        years = []
        for y in range(now.year - 2, now.year + 2):
            years.append(y)
        self.fields['start_date'].widget.years = years
        self.fields['end_date'].widget.years = years 
                  
        # set the default for a new subscription
        start_month = now.month
        start_year = now.year    
        if now.day > 15:
            start_month += 1
            if start_month > 12:
                start_month = 1
                start_year += 1
        sub_year = now.year
        end_year = start_year + 1
        if start_month < Subscription.START_MONTH:
            end_year = start_year
            sub_year -= 1
        self.fields['start_date'].initial = date(start_year, start_month, 1)
        self.fields['end_date'].initial = date(end_year, 4, 1)           
        self.fields['sub_year'].initial = sub_year        

        # Set the available membership choices according to the age
        age = person.age(date(sub_year, Subscription.START_MONTH,1))
        choices = list(Membership.ADULT_CHOICES)
        if age:
            if age < Subscription.CADET_AGE:
                choices = [
                    (Membership.CADET, "Cadet")
                    ]
            elif age < Subscription.JUNIOR_AGE:
                choices = [
                    (Membership.JUNIOR, "Junior")
                    ]
            elif age < Subscription.UNDER_26_AGE:
                choices = [
                    (Membership.UNDER_26, "Under 26"),
                    (Membership.COACH, "Coach")
                    ]
        if self.updating:
            choices.append((Membership.RESIGNED, "Resigned"))                       
        self.fields['membership_id'] = forms.ChoiceField(choices = choices)
       
        if self.updating:
            self.fields['membership_id'].initial = instance.membership_id
            self.fields['sub_year'].initial = instance.sub_year
            self.fields['start_date'].initial = instance.start_date
            self.fields['end_date'].initial = instance.end_date
            self.fields['period'].initial=instance.period
            
            if instance.has_items():
                for key in self.fields:
                    self.fields[key].widget.attrs['disabled'] = 'disabled'
                if instance.has_paid_invoice():
                    pass
                elif instance.has_unpaid_invoice():
                    self.helper.add_input(SubmitButton('delete', 'Delete unpaid invoice', css_class='btn-danger'))
                else:
                    self.helper.add_input(SubmitButton('delete', 'Delete unbilled item', css_class='btn-danger'))
            else:
                self.helper.add_input(SubmitButton('submit', 'Save', css_class='btn-primary'))
        else:
            self.helper.add_input(SubmitButton('submit', 'Save', css_class='btn-primary'))
        self.helper.add_input(SubmitButton('cancel', 'Cancel', css_class='btn-default'))
                
    def clean(self):
        cleaned_data = super(SubscriptionForm, self).clean()
        if self.updating:
            # Add missing fields from the instance
            instance = getattr(self, 'instance', None)
            for key in self.fields:
                if key in cleaned_data:
                    if not cleaned_data[key]:          
                        cleaned_data[key] = getattr(instance, key)
                else:
                    cleaned_data[key] = getattr(instance, key)
            # Remove the error fields
            for key in self.errors.keys():
                del self.errors[key]

        end_date = cleaned_data.get('end_date')
        y = end_date.year
        m = end_date.month
        m += 1
        if m > 12:
            m = 1
            Y += 1
        end_date = date(y, m, 1) - timedelta(days=1)
        cleaned_data['end_date'] = end_date
        start_date = cleaned_data['start_date']
        sub_start = date(cleaned_data['sub_year'], Subscription.START_MONTH, 1)
        sub_end = date(sub_start.year+1, Subscription.START_MONTH, 1)
        errors = []
        if start_date < sub_start or start_date >= sub_end:
            errors.append(forms.ValidationError(_('Start date must be inside the subscription year'), code ='invalid'))
        if end_date < sub_start or end_date >= sub_end:
            errors.append(forms.ValidationError(_('End date must be inside the subscription year'), code ='invalid'))                
        if end_date <= start_date:
            errors.append(forms.ValidationError(_('End date must be after start date'), code = 'invalid'))
        if errors:
            raise forms.ValidationError(errors)
        return cleaned_data

    class Meta:
        model = Subscription
        fields = ['sub_year', 'start_date', 'end_date', 'period', 'no_renewal']

class SubCorrectForm(ModelForm):
    ''' Allow changes without age validation '''

    def __init__(self, *args, **kwargs):
        super(SubCorrectForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_method = 'post'
        self.helper.add_input(SubmitButton('submit', 'Save', css_class='btn-primary'))

    class Meta:
        model = Subscription
        fields = ['membership', 'sub_year', 'start_date', 'end_date']

class SubRenewForm(Form):
    ''' Handle renewal process at start of membership year '''
    sub_year = forms.IntegerField(max_value=2100, min_value = 2014, required=True)

    def __init__(self, *args, **kwargs):
        super(SubRenewForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_method = 'post'
        self.helper.add_input(SubmitButton('renew', 'Renew all subs', css_class='btn-primary'))
        self.helper.add_input(SubmitButton('cancel', 'Cancel', css_class='btn-default'))
        self.fields['sub_year'].initial = datetime.now().year

    def clean(self):
        cleaned_data = super(SubRenewForm, self).clean()
        year = cleaned_data.get('sub_year')

class MembersListForm(Form):
    PAYCHOICES = [('paid','Paid'),('unpaid','Unpaid'),('all','All')]
    categories = forms.ChoiceField()
    membership_year = forms.IntegerField(min_value=2015, max_value=2100,
                        initial=Settings.current().membership_year)
    paystate = forms.ChoiceField(choices=PAYCHOICES,
                                 initial='paid')

    def __init__(self, *args, **kwargs):
        super(MembersListForm, self).__init__(*args, **kwargs)
        self.fields['categories'].choices = Membership.FILTER_CHOICES + [
            (x.id, x.description) for x in Membership.objects.all()
            ]

class InvoiceFilterForm(Form):
    membership_year = forms.IntegerField(min_value=2015, max_value=2100,
                              initial=Settings.current().membership_year)
    start_date = forms.DateTimeField(input_formats=settings.DATE_INPUT_FORMATS,
                                    initial=date(Settings.current().membership_year,4,1), required=False)
    start_date.widget.format = settings.DATE_INPUT_FORMATS[0]
    end_date = forms.DateTimeField(input_formats=settings.DATE_INPUT_FORMATS,
                                  initial=date.today(), required=False)
    end_date.widget.format = settings.DATE_INPUT_FORMATS[0]
    paid = forms.BooleanField(initial=True, required=False)
    unpaid = forms.BooleanField(initial=True, required=False)
    cancelled = forms.BooleanField(initial=False, required=False)

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
            self.helper.add_input(SubmitButton('delete', 'Delete', css_class='btn-danger'))
        self.helper.add_input(SubmitButton('submit', 'Save', css_class='btn-primary'))
        self.fields['item_date'].widget.format = '%d/%m/%Y'
        self.fields['item_date'].input_formats = settings.DATE_INPUT_FORMATS

    def clean(self):
        cleaned_data = super(InvoiceItemForm, self).clean()
        item_type = cleaned_data.get('item_type')
        amount = float(cleaned_data.get('amount'))
        if item_type.credit:
            if amount >=0:
                raise forms.ValidationError("This is a credit. The amount must be negative")
       
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
        self.helper.add_input(SubmitButton('submit', 'GO', css_class='btn-primary'))
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


class SettingsForm(Form):
    membership_year = forms.IntegerField(max_value=2100, min_value=0)

    def __init__(self, *args, **kwargs):
        super(SettingsForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-lg-2'
        self.helper.field_class = 'col-lg-6'
        self.helper.form_method = 'post'
        self.helper.add_input(SubmitButton('cancel', 'Cancel', css_class='btn-default'))
        self.helper.add_input(SubmitButton('submit', 'Save', css_class='btn-primary'))
        self.helper.add_input(SubmitButton('renew', 'Renew subs', css_class='btn-danger'))
        self.helper.add_input(SubmitButton('invoices', 'Create invoices', css_class='btn-danger'))
        self.helper.add_input(SubmitButton('count', 'Count mail invoices', css_class='btn-primary'))
        self.helper.add_input(SubmitButton('mail', 'Mail invoices', css_class='btn-danger'))

class GroupForm(ModelForm):

    class Meta:
        model = Group
        fields = ['description']

    def __init__(self, *args, **kwargs):
        super(GroupForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-lg-2'
        self.helper.field_class = 'col-lg-6'
        self.helper.form_method = 'post'
        self.helper.add_input(SubmitButton('cancel', 'Cancel', css_class='btn-default'))
        self.helper.add_input(SubmitButton('submit', 'Save', css_class='btn-primary'))
    
    def save(self, *args, **kwargs):
        grp = super(GroupForm, self).save(commit=False)
        grp.slug = slugify(grp.description)
        grp.save()
 
class GroupAddPersonForm(Form):
    #class meta:
    #    model = Group
    #    fields ['slug']

    #class MultipleGroupField(forms.ModelMultipleChoiceField):
        #def label_from_instance(self, group):
        #    url = reverse('group-detail', kwargs={'slug': group.slug})
        #    label = '<a href="%s">%s</a>' % (url, group.__unicode__())
        #    return mark_safe(label)
    
    groups = forms.ModelChoiceField(queryset=Group.objects.all(), empty_label=None)

    def __init__(self, *args, **kwargs):
        super(GroupAddPersonForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-lg-2'
        self.helper.field_class = 'col-lg-6'
        self.helper.form_method = 'post'
        self.helper.add_input(SubmitButton('cancel', 'Cancel', css_class='btn-default'))
        self.helper.add_input(SubmitButton('submit', 'Add', css_class='btn-primary'))
   

class EmailTextForm(forms.Form):
    intro = forms.ChoiceField()
    notes = forms.ChoiceField()
    closing = forms.ChoiceField()

    def __init__(self, *args, **kwargs):
        super(EmailTextForm, self).__init__(*args, **kwargs)
        text_choices = [(-1, u'None')] + [(x.id, x.name) for x in TextBlock.objects.filter(
            ~Q(name__startswith='_')).order_by('name')]
        self.fields['intro'].choices = text_choices
        self.fields['notes'].choices = text_choices
        self.fields['closing'].choices = text_choices

        self.helper = FormHelper()
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-lg-2'
        self.helper.field_class = 'col-lg-6'
        self.helper.form_method = 'post'
        self.helper.add_input(SubmitButton('submit', 'Save', css_class='btn-primary'))


class EmailForm(Form):
    from_email = forms.EmailField(required=True)
    to = forms.EmailField(required=False)
    group = forms.ChoiceField(required=False)
    cc = forms.CharField(required=False)
    bcc = forms.CharField(required=False)
    subject =forms.CharField(required=True)
    text = forms.CharField(required=True, widget=Textarea )

    def __init__(self, *args, **kwargs):
        to = kwargs.pop('to', '')
        group = kwargs.pop('group','')
        super(EmailForm, self).__init__(*args, **kwargs)
        choices = [(-1, u'None')] + [(x.id, x.slug) for x in Group.objects.order_by('slug')]
        self.fields['group'].choices = choices
        self.helper = FormHelper()
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-lg-1'
        self.helper.field_class = 'col-lg-5'
        self.helper.form_method = 'post'

        if to:
            div=Div('from_email',
                    'to',
                    'subject',
                    'text' 
                    )
        elif group:
            div=Div('from_email',
                    'group',
                    'subject',
                    'text' 
                    )
        else:
            div=Div('from_email',
                    'to',
                    'group'
                    'subject',
                    'text' 
                    )
        self.helper.layout = Layout(
            div,
            ButtonHolder(
                Submit('submit', 'Send', css_class='btn-primary')
            )
        )

    def clean(self):
        cleaned_data = super(EmailForm, self).clean()
        if cleaned_data['to'] == u'' and cleaned_data['group'] == '-1':
            raise forms.ValidationError('No To or group selected')
        return self.cleaned_data

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
        self.helper.add_input(SubmitButton('submit', 'Save', css_class='btn-primary'))
        
        self.fields['banked_date'].widget.format = '%d/%m/%Y'
        self.fields['banked_date'].input_formats = settings.DATE_INPUT_FORMATS

    class Meta:
        model = Payment
        fields = ['membership_year', 'type', 'reference', 'amount', 'banked_date']
        widgets = {'banked_date': forms.DateInput(attrs={'class':'datepicker'}),}

class PaymentFilterForm(Form):
    membership_year = forms.IntegerField(min_value=2015, max_value=2100,
                              initial=Settings.current().membership_year, required=False)
    start_date = forms.DateTimeField(input_formats=settings.DATE_INPUT_FORMATS,
                                    initial=date(Settings.current().membership_year,4,1), required=False)
    start_date.widget.format = settings.DATE_INPUT_FORMATS[0]
    end_date = forms.DateTimeField(input_formats=settings.DATE_INPUT_FORMATS,
                                  initial=date.today(), required=False)
    end_date.widget.format = settings.DATE_INPUT_FORMATS[0]
    direct_debit = forms.BooleanField(initial=True, required=False)
    bacs = forms.BooleanField(initial=True, required=False)
    cheque = forms.BooleanField(initial=True, required=False)
    cash = forms.BooleanField(initial=True, required=False)
    other = forms.BooleanField(initial=True, required=False)

class CreditNoteForm(ModelForm):

    def __init__(self, *args, **kwargs):
        super(CreditNoteForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-lg-2'
        self.helper.field_class = 'col-lg-6'
        self.helper.form_method = 'post'
        self.helper.form_show_errors = True
        self.helper.form_error_title = 'Errors'
        self.helper.error_text_inline = True
        self.helper.add_input(SubmitButton('submit', 'Save', css_class='btn-primary'))
    
    class Meta:
        model = CreditNote
        fields = ['membership_year', 'amount', 'reference']

class TextBlockForm(ModelForm):

    def __init__(self, *args, **kwargs):
        option = kwargs.pop('option', None)
        super(TextBlockForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.field_class = 'input-xlarge'
        self.helper.form_method = 'post'
        self.helper.form_show_errors = True
        self.helper.form_error_title = 'Errors'
        self.helper.error_text_inline = True
        if option:
            self.helper.add_input(SubmitButton('editor', 'Editor view', css_class='btn-primary'))
        else:
            self.helper.add_input(SubmitButton('html', 'HTML view', css_class='btn-primary'))
        self.helper.add_input(SubmitButton('save', 'Save', css_class='btn-primary'))

       
    class Meta:
        model = TextBlock
        fields = ['name', 'text']
        widgets = {
            'text': Textarea(attrs={'cols': 20, 'rows': 30, 'class': 'col-md'
            })}

class XlsInputForm(Form):
    IMPORT_FILE_TYPES = ['.xls', ]
    #BASE = 0
    #MEMBERS = 1
    #ITEMS = 2
    #BACKUP = 3
    #CHOICES=[(BASE, 'Basic tables'),
    #         (MEMBERS, 'Members file'),
    #         (ITEMS, 'Invoice items'),
    #         (BACKUP, 'Backup file')
    #        ]

    input_excel = forms.FileField(required=True, label=u"Select the Excel file")
    #sheet_type = forms.ChoiceField(choices=CHOICES, widget=forms.RadioSelect())
    #batch_size = forms.IntegerField(label=u"Batch size")
    
    def __init__(self, *args, **kwargs):
        super(XlsInputForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-lg-2'
        self.helper.field_class = 'col-lg-6'
        self.helper.form_method = 'post'
        self.helper.add_input(SubmitButton('submit', 'Open file', css_class='btn-primary'))
        #self.initial['sheet_type'] = XlsInputForm.MEMBERS
        #self.initial['batch_size'] = 100

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
        self.helper.add_input(SubmitButton('submit', 'Next', css_class='btn-primary'))

class GenericMoreForm(Form):
    
    def __init__(self, *args, **kwargs):
        super(GenericMoreForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_class = 'form-horizontal'
        self.helper.form_method = 'post'
        self.helper.add_input(SubmitButton('submit', 'Go', css_class='btn-primary'))

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
        self.helper.add_input(SubmitButton('check', 'Check data', css_class='btn-primary'))
        self.helper.add_input(SubmitButton('import', 'Import data', css_class='btn-primary'))
        
        my_book = ExcelBook.objects.all()[0]
        with open_excel_workbook(my_book.file) as book:
            for sheet_name in book.sheet_names():
                self.fields[sheet_name] = forms.BooleanField(required = False)

class ContactForm(Form):
    message = forms.CharField(max_length=2000, required=True, widget=forms.Textarea)
    email = forms.EmailField(required=True)

    def __init__(self, *args, **kwargs):
        resigned = kwargs.pop('resigned', False)
        super(ContactForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        postText = 'submit'
        if resigned:
            postText = 'resign'
        self.helper.add_input(SubmitButton(postText, 'Send', css_class='btn-primary'))




