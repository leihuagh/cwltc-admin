import os
from datetime import date, datetime, timedelta, time
from django import forms
from django.forms import Form, ModelForm, HiddenInput
from django.forms.widgets import CheckboxSelectMultiple, Textarea
from django.conf import settings
from django.contrib.auth.forms import AuthenticationForm
from django.utils.translation import ugettext_lazy as _
from django.db.models import Q
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Div, HTML, Fieldset, ButtonHolder, BaseInput
from tempus_dominus.widgets import DatePicker
from .widgets import MySelectDate, ListTextWidget
from .models import (Person, Address, Subscription, Membership, Fees, Invoice, InvoiceItem, Payment,
                     CreditNote, ExcelBook, TextBlock, MailType, MailCampaign, Group, Settings, VisitorFees)
from .excel import open_excel_workbook
from .filters import year_choices

TEMPLATE_PACK = getattr(settings, 'CRISPY_TEMPLATE_PACK', 'bootstrap')


class SubmitButton(BaseInput):
    """ Replacement for Submit that allows button class to be defined
        https://github.com/maraujop/django-crispy-forms/issues/242
    """
    input_type = 'submit'
    field_classes = 'button' if TEMPLATE_PACK == 'uni_form' else 'btn'  # removed btn-primary


class FilterMemberForm(Form):
    success_url = '/list/'
    helper = FormHelper()
    helper.form_method = 'POST'
    helper.form_class = 'form-horizontal'
    helper.add_input(SubmitButton('submit', 'Go', css_class='btn-primary'))

    def __init__(self, *args, **kwargs):
        super(FilterMemberForm, self).__init__(*args, **kwargs)
        memcats = Membership.objects.all()
        self.fields = {}
        for cat in memcats:
            self.fields[str(cat.id)] = forms.BooleanField(required=False, label=cat.description)


class PersonNameForm(ModelForm):
    class Meta:
        model = Person
        fields = [
            'first_name',
            'last_name',
            'gender',
            'dob',
            'state',
            'email',
            'mobile_phone',
            'british_tennis',
            'pays_own_bill',
            'notes'
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-4'
        self.helper.field_class = 'col'
        self.helper.form_tag = False
        self.title = "Edit person"


class PersonForm(ModelForm):
    """
    Handles creation of a person with new address
    creation of a linked person with linked address
    update of a person
    """

    address1 = forms.CharField(max_length=50, label='Address 1')
    address2 = forms.CharField(max_length=50, label='Address 2', required=False)
    town = forms.CharField(max_length=30)
    post_code = forms.CharField(max_length=15)
    home_phone = forms.CharField(max_length=20, required=False)

    class Meta:
        model = Person
        fields = ['gender',
                  'first_name',
                  'last_name',
                  'dob',
                  # 'state',
                  'email',
                  'mobile_phone',
                  # 'british_tennis',
                  # 'pays_own_bill',
                  # 'notes']
                  ]

    def __init__(self, *args, **kwargs):
        self.link = kwargs.pop('link', None)
        self.public = kwargs.pop('public', None)
        super().__init__(*args, **kwargs)
        self.person = None

        if self.link:
            self.parent = Person.objects.get(pk=self.link)
            self.fields['last_name'].initial = self.parent.last_name
            self.fields['mobile_phone'].initial = self.parent.mobile_phone
            self.fields['email'].initial = self.parent.email
            self.fields['email'].required = False
        self.updating = False
        instance = getattr(self, 'instance', None)
        self.updating = instance and instance.id

        no_complete = [
            'first_name',
            'last_name',
            'mobile_phone',
            # 'british_tennis',
            # 'notes',
            'address1',
            'address2',
            'post_code',
            'home_phone'
        ]
        for field in self.fields:
            self.fields[field].widget.attrs = {'autocomplete': "off"}
        self.fields['dob'].label = 'Date of birth'
        self.fields['dob'].widget.format = settings.DATE_INPUT_FORMATS[0]
        self.fields['dob'].input_formats = settings.DATE_INPUT_FORMATS
        self.fields['dob'].widget.attrs = {'autocomplete': "off", 'placeholder': 'DD/MM/YYYY'}
        # self.fields['email'].widget.attrs = {'autocomplete': "off"}

        self.helper = FormHelper(self)

        name_set = Div(HTML('<h3>Create Adult</h3>'),
                       Div('first_name',
                           'last_name',
                           'gender',
                           'dob',
                           'mobile_phone',
                           'email',
                           css_class="tile"
                           ),
                       css_class="col col-sm-4"
                       )

        address_set = Div(HTML('<h3>Address</h3>'),
                          Div('address1',
                              'address2',
                              'town',
                              'post_code',
                              'home_phone',
                              css_class="tile"
                              ),
                          css_class="col col-sm-4"
                          )

        if self.link or self.updating:
            self.helper.layout = Layout(Div(name_set, css_class="row"))
        else:
            self.helper.layout = Layout(Div(name_set, address_set, css_class="row"))
        self.helper.layout.append(Div(
            Div(
                ButtonHolder(
                    SubmitButton('submit', 'Save', css_class='btn-primary'),
                    SubmitButton('cancel', 'Cancel', css_class='btn-default')
                ),
                css_class="col col-sm-4"
            ),
            css_class="row"
        )
        )

    def clean(self):
        """ remove address errors if linked person or update """
        super().clean()
        if not self.updating:
            self.cleaned_data['date_joined'] = date.today()
        if self.link or self.updating:
            del self._errors['address1']
            del self._errors['town']
            del self._errors['post_code']
        return self.cleaned_data

    def save(self, commit=True):
        self.person = super().save(commit=False)
        if not self.updating:
            self.person.date_joined = date.today()
        if self.link:
            self.person.linked = self.parent
            self.person.address = self.parent.address
        else:
            if not self.updating:
                address = Address.objects.create(
                    address1=self.cleaned_data['address1'],
                    address2=self.cleaned_data['address2'],
                    town=self.cleaned_data['town'],
                    post_code=self.cleaned_data['post_code']
                )
                self.person.address = address
        self.person.save()


class JuniorForm(ModelForm):
    class Meta:
        model = Person
        fields = ['gender',
                  'first_name',
                  'last_name',
                  'dob',
                  'notes'
                  ]
        widgets = {'dob': forms.DateInput(attrs={'placeholder': 'DD/MM/YYYY'}), }

    child_email = forms.EmailField(max_length=75, required=False)
    child_mobile = forms.CharField(max_length=20, required=False)
    parent_gender = forms.ChoiceField(choices=Person.GENDERS, initial='F')
    parent_first_name = forms.CharField(max_length=30)
    parent_last_name = forms.CharField(max_length=30)
    parent_email = forms.EmailField(max_length=75)
    parent_mobile = forms.CharField(max_length=20, required=False)
    home_phone = forms.CharField(max_length=20, required=False)
    address1 = forms.CharField(max_length=50)
    address2 = forms.CharField(max_length=50, required=False)
    town = forms.CharField(max_length=30)
    post_code = forms.CharField(max_length=15)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

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
        self.cleaned_data = super().clean()

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

        # self.errorString = "\n".join(self.errors)
        # if self.errorString:
        #    raise forms.ValidationError(self.errorString)      
        return self.cleaned_data

    def save(self, commit=True):
        """ Create a child record linked to a parent record """
        junior = super().save(commit=False)
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
    """ Link a person to another """

    first_name = forms.CharField(max_length=30, required=False)
    last_name = forms.CharField(max_length=30, required=False)
    id = forms.IntegerField(required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-lg-2'
        self.helper.field_class = 'col-lg-6'
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            Fieldset('Select parent / bill payer:',
                     'first_name',
                     'last_name',
                     'id'
                     ),
            ButtonHolder(
                SubmitButton('link', 'Link', css_class='btn-primary'),
                SubmitButton('cancel', 'Cancel', css_class='btn-default')
            )
        )

    def clean(self):
        cleaned_data = super().clean()
        id = cleaned_data.get('id')
        if id:
            matches = Person.objects.filter(pk=id)
        else:
            if len(cleaned_data.get('first_name')) == 0 and len(cleaned_data.get('last_name')) == 0:
                raise forms.ValidationError('Specify at least name')
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
        super().__init__(*args, **kwargs)
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
        cleaned_data = super().clean()
        annual = cleaned_data.get('annual_sub')
        monthly = cleaned_data.get('monthly_sub')
        joining = cleaned_data.get('joining_fee')
        if joining:
            if joining < 0:
                raise forms.ValidationError('Value cannot be negative')
        else:
            joining = 0


class VisitorFeesForm(ModelForm):
    class Meta:
        model = VisitorFees
        fields = ['year', 'adult_fee', 'junior_fee']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_tag = False
        self.helper.form_class = 'form-horizontal'
        self.helper.well_class = 'col-md-4'
        self.helper.label_class = 'col-md-6'
        self.helper.field_class = 'col-md-6'


class SubscriptionForm(ModelForm):
    class Meta:
        model = Subscription
        fields = ['sub_year', 'period', 'start_date', 'end_date', 'no_renewal']

    membership_id = forms.ChoiceField()

    def __init__(self, *args, **kwargs):
        person_id = kwargs.pop('person_id', None)
        super().__init__(*args, **kwargs)
        person = Person.objects.get(pk=person_id)
        instance = getattr(self, 'instance', None)
        self.updating = True if instance and instance.id else False
        self.helper = FormHelper(self)
        message = 'New subscription'
        if person.subscription_set.count() > 0:
            message += ' (add to history)'
        if self.updating:
            if instance.has_paid_invoice():
                message = 'This sub is linked to a paid invoice and cannot be changed.'
            elif instance.has_unpaid_invoice():
                message = 'This sub cannot be changed until the linked unpaid invoice is deleted.'
            elif instance.has_items():
                message = 'This sub cannot be changed until the linked unbilled item is deleted.'
            else:
                message = 'Change subscription'
            if instance.resigned:
                message += " (Resigned)"
        self.helper.layout = Layout(
            HTML(f'<h4 class="text-danger"> {message}</h4>'),
            Fieldset('',
                     'membership_id',
                     'sub_year',
                     'period',
                     'start_date',
                     'end_date',
                     'no_renewal',
                     ),
            HTML("""
                {% for item in items %}
                <p class="text-danger">
                    {{ item.item_date|date }} {{ item.description}}
                    {% if item.payment %}
                        {{ item.payment_id }}
                    {% else %}
                        Unpaid
                    {% endif %}          
                    £ {{ item.amount }}
                {% endfor item %}
                </p>
            """)
        )

        self.fields['start_date'].widget = MySelectDate()
        self.fields['end_date'].widget = MySelectDate()
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
        end_month = Subscription.START_MONTH - 1
        if end_month == 0:
            end_month = 12
        self.fields['start_date'].initial = date(start_year, start_month, 1)
        self.fields['end_date'].initial = date(end_year, end_month, 1)
        self.fields['sub_year'].initial = sub_year

        # Set the available membership choices according to the age
        age = person.age(date(sub_year, Subscription.START_MONTH, 1))
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
                    (Membership.COACH, "Coach"),
                    (Membership.NON_PLAYING, "Non playing")
                ]

        self.fields['membership_id'] = forms.ChoiceField(choices=choices)

        if self.updating:
            self.fields['membership_id'].initial = instance.membership_id
            self.fields['sub_year'].initial = instance.sub_year
            self.fields['start_date'].initial = instance.start_date
            self.fields['end_date'].initial = instance.end_date
            self.fields['period'].initial = instance.period

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
                self.helper.add_input(SubmitButton('delete', 'Delete sub', css_class='btn-danger'))
                self.helper.add_input(SubmitButton('submit', 'Save', css_class='btn-primary'))
        else:
            self.helper.add_input(SubmitButton('submit', 'Save', css_class='btn-primary'))
        self.helper.add_input(SubmitButton('cancel', 'Cancel', css_class='btn-default'))

    def clean(self):
        cleaned_data = super().clean()
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
            self.errors.clear()

        end_date = cleaned_data['end_date']
        y = end_date.year
        m = end_date.month
        m += 1
        if m > 12:
            m = 1
            y += 1
        end_date = date(y, m, 1) - timedelta(days=1)
        cleaned_data['end_date'] = end_date
        start_date = cleaned_data['start_date']
        sub_start = date(cleaned_data['sub_year'], Subscription.START_MONTH, 1)
        sub_end = date(sub_start.year + 1, Subscription.START_MONTH, 1)
        errors = []
        if start_date < sub_start or start_date >= sub_end:
            errors.append(forms.ValidationError(_('Start date must be inside the subscription year'), code='invalid'))
        if end_date < sub_start or end_date >= sub_end:
            errors.append(forms.ValidationError(_('End date must be inside the subscription year'), code='invalid'))
        if end_date <= start_date:
            errors.append(forms.ValidationError(_('End date must be after start date'), code='invalid'))
        if errors:
            raise forms.ValidationError(errors)
        return cleaned_data


class SubCorrectForm(ModelForm):
    """ Allow changes without age validation """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_method = 'post'
        self.helper.add_input(SubmitButton('submit', 'Save', css_class='btn-primary'))

    class Meta:
        model = Subscription
        fields = ['membership', 'sub_year', "start_date", 'end_date']


class YearConfirmForm(Form):
    """ Handle renewal process at start of membership year """
    sub_year = forms.IntegerField(max_value=2100, min_value=2014, required=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_method = 'post'
        self.helper.add_input(SubmitButton('apply', 'Apply', css_class='btn-primary'))
        self.helper.add_input(SubmitButton('cancel', 'Cancel', css_class='btn-default'))
        self.fields['sub_year'].initial = Settings.objects.all()[0].membership_year

    def clean(self):
        cleaned_data = super().clean()
        year = cleaned_data.get('sub_year')


class MembershipForm(ModelForm):
    class Meta:
        model = Membership
        fields = ['description', 'long_description',
                  'is_adult', 'is_playing', 'is_tennis', 'apply_online', 'cutoff_age']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.add_input(SubmitButton('submit', 'Save', css_class='btn-primary'))


class InvoiceFilterForm(Form):
    membership_year = forms.IntegerField(min_value=2015, max_value=2100,
                                         initial=Settings.current_year())
    start_datetime = forms.DateTimeField(input_formats=settings.DATE_INPUT_FORMATS,
                                         initial=date(Settings.current_year(), 4, 1), required=False)
    start_datetime.widget.format = settings.DATE_INPUT_FORMATS[0]
    end_datetime = forms.DateTimeField(input_formats=settings.DATE_INPUT_FORMATS,
                                       initial=date.today(), required=False)
    end_datetime.widget.format = settings.DATE_INPUT_FORMATS[0]
    paid = forms.BooleanField(initial=True, required=False)
    unpaid = forms.BooleanField(initial=True, required=False)
    cancelled = forms.BooleanField(initial=False, required=False)

    def clean(self):
        super().clean()
        edate = self.cleaned_data['end_datetime']
        self.cleaned_data['end_datetime'] = datetime.combine(
            date(edate.year, edate.month, edate.day),
            time(23, 59, 59)
        )
        return self.cleaned_data


class PeriodForm(Form):
    from_date = forms.DateField(widget=DatePicker(options={'format': 'DD/MM/YYYY'}))
    to_date = forms.DateField(widget=DatePicker(options={'format': 'DD/MM/YYYY'}))
    minimum_amount = forms.IntegerField(required=True)
    invoice_date = forms.DateField(widget=DatePicker(options={'format': 'DD/MM/YYYY'}))

    def clean(self):
        cleaned = super().clean()
        if cleaned['to_date'] < cleaned['from_date']:
            raise forms.ValidationError('Start date us before end date')


class InvoiceItemForm(ModelForm):
    class Meta:
        model = InvoiceItem
        fields = ['item_type', 'item_date', 'description', 'amount']
        widgets = {'item_date': DatePicker(options={'format': 'DD/MM/YYYY'})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_tag = False
        self.title = "Invoice item"

    def clean(self):
        cleaned_data = super().clean()
        item_type = cleaned_data.get('item_type')
        amount = cleaned_data.get('amount', 0)
        if amount == 0:
            raise forms.ValidationError("Amount cannot be 0")
        if item_type.credit:
            if amount > 0:
                raise forms.ValidationError("This is a credit. The amount must be negative")


class InvoiceSelectForm(Form):
    CHOICES = [(1, 'Invoice reference number'),
               (2, 'Person reference number')]

    ref = forms.IntegerField(label='Reference number')
    choice = forms.ChoiceField(choices=CHOICES, widget=forms.RadioSelect(), label='Select')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-lg-2'
        self.helper.field_class = 'col-lg-6'
        self.helper.form_method = 'post'
        self.helper.add_input(SubmitButton('submit', 'GO', css_class='btn-primary'))
        self.initial['choice'] = 1

    def clean(self):
        cleaned_data = super().clean()
        choice = int(cleaned_data.get('choice'))
        ref = int(cleaned_data.get('ref'))
        if choice == 1:
            try:
                inv = Invoice.objects.get(pk=ref)
            except Invoice.DoesNotExist:
                raise forms.ValidationError("Invoice with id {} not found".format(ref))
        elif choice == 2:
            try:
                p = Person.objects.get(pk=ref)
            except:
                raise forms.ValidationError("Person with id {} not found".format(ref))


class SettingsForm(Form):
    membership_year = forms.IntegerField(max_value=2100, min_value=0)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-sm-2'
        self.helper.field_class = 'col-sm-2'
        self.helper.form_method = 'post'
        self.helper.add_input(SubmitButton('cancel', 'Cancel', css_class='btn-default'))
        self.helper.add_input(SubmitButton('submit', 'Save', css_class='btn-primary'))


class GroupForm(ModelForm):
    class Meta:
        model = Group
        fields = ['name', 'description']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.title = 'Group'


class GroupAddPersonForm(Form):
    group = forms.ModelChoiceField(queryset=Group.objects.all(), empty_label=None)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False


class EmailTextForm(forms.Form):
    intro = forms.ChoiceField()
    notes = forms.ChoiceField()
    closing = forms.ChoiceField()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        text_choices = [(-1, 'None')] + [(x.id, x.name) for x in TextBlock.objects.filter(
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
    from_email = forms.EmailField(required=True, widget=ListTextWidget(
        name='email',
        data_list=((getattr(settings, 'SUBS_EMAIL'), getattr(settings, 'INFO_EMAIL')))
    ))
    to = forms.CharField(required=False, disabled=True)
    subject = forms.CharField(required=True)
    text = forms.CharField(required=True, widget=Textarea)
    mailtype = forms.ModelMultipleChoiceField(queryset=MailType.objects.all(),
                                              widget=CheckboxSelectMultiple,
                                              required=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()


class MailTypeForm(ModelForm):
    class Meta:
        model = MailType
        fields = ['name', 'description', 'can_unsubscribe', 'sequence']
        widgets = {'description': forms.Textarea}

    def __init__(self, *args, **kwargs):
        with_delete = kwargs.pop('with_delete', None)
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-lg-2'
        self.helper.field_class = 'col-lg-6'
        self.helper.add_input(SubmitButton('cancel', 'Cancel', css_class='btn-default'))
        self.helper.add_input(SubmitButton('submit', 'Save', css_class='btn-primary'))
        if with_delete:
            self.helper.add_input(SubmitButton('delete', 'Delete', css_class='btn-danger'))


class PaymentForm(ModelForm):

    def __init__(self, *args, **kwargs):
        """ optional kwarg amount sets the default amount """
        amount = kwargs.pop('amount', None)
        super().__init__(*args, **kwargs)
        if amount:
            self.fields['amount'].initial = amount
        self.helper = FormHelper(self)
        self.helper.form_error_title = 'Errors'
        self.helper.add_input(SubmitButton('submit', 'Save', css_class='btn-primary'))

        self.fields['banked_date'].input_formats = settings.DATE_INPUT_FORMATS

    class Meta:
        model = Payment
        fields = ['membership_year', 'type', 'reference', 'amount', 'banked', 'banked_date', ]
        widgets = {'banked_date': DatePicker(),
                   'membership_year': forms.Select(choices=year_choices()),
                   }


class PaymentFilterForm(Form):
    membership_year = forms.IntegerField(min_value=2015, max_value=2100,
                                         initial=Settings.current_year(), required=False)
    start_date = forms.DateTimeField(input_formats=settings.DATE_INPUT_FORMATS,
                                     initial=date(Settings.current_year(), 4, 1), required=False)
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
    class Meta:
        model = CreditNote
        fields = ['membership_year', 'amount', 'reference']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-sm-2'
        self.helper.field_class = 'col-sm-4'
        self.helper.form_error_title = 'Errors'
        self.helper.add_input(SubmitButton('submit', 'Save', css_class='btn-primary'))

    def clean_membership_year(self):
        if self.cleaned_data['membership_year'] < 2017:
            raise forms.ValidationError('Invalid year')
        return self.cleaned_data['membership_year']

    # def clean_amount(self):
    #     if self.cleaned_data['amount'] < 0:
    #         raise forms.ValidationError('Amount should not be negative')
    #     return self.cleaned_data['amount']


class TextBlockForm(ModelForm):
    class Meta:
        model = TextBlock
        fields = ['name', 'type', 'text']
        widgets = {
            'text': Textarea(attrs={'cols': 1, 'rows': 1
                                    })}

    def __init__(self, *args, **kwargs):
        no_delete = kwargs.pop('no_delete', False)
        super().__init__(*args, **kwargs)
        self.fields['text'].required = False  # get round bug in tinymce
        self.helper = FormHelper(self)
        self.helper.form_tag = True
        self.helper.field_class = 'input-xlarge'
        self.helper.form_method = 'post'
        self.helper.form_show_errors = True
        self.helper.form_error_title = 'Errors'
        self.helper.error_text_inline = True
        self.helper.add_input(SubmitButton('save', 'Save', css_class='btn-primary'))
        self.helper.add_input(SubmitButton('cancel', 'Cancel', css_class='btn-default'))
        if not no_delete:
            self.helper.add_input(SubmitButton('delete', 'Delete', css_class='btn-danger'))


class MailCampaignForm(ModelForm):
    def __init__(self, *args, **kwargs):
        with_delete = kwargs.pop('with_delete', None)
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.field_class = 'input-xlarge'
        self.helper.error_text_inline = True
        self.helper.add_input(SubmitButton('next', 'Next', css_class='btn-primary'))
        self.helper.add_input(SubmitButton('cancel', 'Cancel', css_class='btn-default'))
        if with_delete:
            self.helper.add_input(SubmitButton('delete', 'Delete', css_class='btn-danger'))

    class Meta:
        model = MailCampaign
        fields = ['name', 'mail_template', 'json']
        widgets = {'json': forms.HiddenInput()}


class XlsInputForm(Form):
    IMPORT_FILE_TYPES = ['.xls', ]
    # BASE = 0
    # MEMBERS = 1
    # ITEMS = 2
    # BACKUP = 3
    # CHOICES=[(BASE, 'Basic tables'),
    #         (MEMBERS, 'Members file'),
    #         (ITEMS, 'Invoice items'),
    #         (BACKUP, 'Backup file')
    #        ]

    input_excel = forms.FileField(required=True, label=u"Select the Excel file")

    # sheet_type = forms.ChoiceField(choices=CHOICES, widget=forms.RadioSelect())
    # batch_size = forms.IntegerField(label=u"Batch size")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-lg-2'
        self.helper.field_class = 'col-lg-6'
        self.helper.form_method = 'post'
        self.helper.add_input(SubmitButton('submit', 'Open file', css_class='btn-primary'))
        # self.initial['sheet_type'] = XlsInputForm.MEMBERS
        # self.initial['batch_size'] = 100

    def clean_input_excel(self):
        input_excel = self.cleaned_data['input_excel']
        extension = os.path.splitext(input_excel.name)[1]
        if not (extension in XlsInputForm.IMPORT_FILE_TYPES):
            raise forms.ValidationError(u'%s is not a valid excel file' % extension)
        else:
            return input_excel


class XlsMoreForm(Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_class = 'form-horizontal'
        self.helper.form_method = 'post'
        self.helper.add_input(SubmitButton('submit', 'Next', css_class='btn-primary'))


class GenericMoreForm(Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
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
                                   'placeholder': 'Password'}))


class SelectSheetsForm(Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_class = 'form-horizontal'
        self.helper.form_method = 'post'
        self.helper.add_input(SubmitButton('check', 'Check data', css_class='btn-primary'))
        self.helper.add_input(SubmitButton('import', 'Import data', css_class='btn-primary'))

        my_book = ExcelBook.objects.all()[0]
        with open_excel_workbook(my_book.file) as book:
            for sheet_name in book.sheet_names():
                self.fields[sheet_name] = forms.BooleanField(required=False)
