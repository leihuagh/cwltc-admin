from django import forms
from django.forms import ModelForm, Form
from django.forms.widgets import TextInput
from django.contrib.auth.models import User
from django.urls import reverse
from django.urls.exceptions import NoReverseMatch
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout as CrispyLayout, Div, HTML
from crispy_forms.bootstrap import FormActions
from .models import *
from members.forms import SubmitButton


class TerminalForm(Form):

    terminal = forms.IntegerField(label="Terminal number")
    system = forms.ChoiceField(choices =(('bar', 'Bar system'),('main', 'Main system')))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.layout = CrispyLayout(
            Div('terminal', 'system'),
            HTML('<br><br>'),
                SubmitButton('start', 'Start terminal', css_class='btn-success btn-lg'),
                SubmitButton('disable', 'Disable terminal', css_class='btn-warning btn-lg', formnovalidate='formnovalidate'),
                SubmitButton('cancel', 'Cancel', css_class='btn-default btn-lg', formnovalidate='formnovalidate'),
            )


class ItemForm(ModelForm):
    class Meta:
        model = Item
        fields = [
            'description',
            'button_text',
            'sale_price',
            'cost_price',
            'item_type',
            'colour'
            ]

    colour = forms.ModelChoiceField(queryset=Colour.objects.all(), empty_label=None)

    def __init__(self, *args, **kwargs):
        delete = kwargs.pop('delete', None)
        super().__init__(*args, **kwargs)
        self.fields['item_type'].queryset = ItemType.objects.filter(pos=True)
        self.helper = FormHelper(self)
        self.helper.layout = CrispyLayout(
            Div(
                'description',
                'button_text',
                'sale_price',
                'cost_price',
                'item_type',
                'colour',
                css_class="well"
                ),
            FormActions(
                SubmitButton('save', 'Save', css_class='btn-primary'),
                SubmitButton('cancel', 'Cancel', css_class='btn-default', formnovalidate='formnovalidate')
                )
            )
        if delete:
            self.helper.layout[1].insert(
                1, SubmitButton('delete','Delete', css_class='btn-danger', formnovalidate='formnovalidate')
        )


class LayoutForm(ModelForm):

    class Meta:
        model = Layout
        fields = ['name', 'title', 'item_type']

    def __init__(self, *args, **kwargs):
        delete = kwargs.pop('delete', None)
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.layout = CrispyLayout(
            Div(
            'name', 'title',
            'item_type',
                css_class="well"
            ),
            FormActions(
                SubmitButton('save', 'Save', css_class='btn-primary'),
                SubmitButton('cancel', 'Cancel', css_class='btn-default', formnovalidate='formnovalidate')
            )
        )
        if delete:
            self.helper.layout[1].insert(
                1, SubmitButton('delete','Delete', css_class='btn-danger', formnovalidate='formnovalidate')
            )


class ColourForm(ModelForm):

    class Meta:
        model = Colour
        fields = ['name', 'fore_colour', 'back_colour']
        widgets = {'fore_colour': TextInput(attrs={'type': 'color'}),
                   'back_colour': TextInput(attrs={'type': 'color'})
                   }

    def __init__(self, *args, **kwargs):
        delete = kwargs.pop('delete', None)
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.layout = CrispyLayout(
            Div(
            'name', 'fore_colour', 'back_colour',
                css_class="well"
            ),
            FormActions(
                SubmitButton('save', 'Save', css_class='btn-primary'),
                SubmitButton('cancel', 'Cancel', css_class='btn-default', formnovalidate='formnovalidate')
            )
        )
        if delete:
            self.helper.layout[1].insert(
                1, SubmitButton('delete','Delete', css_class='btn-danger', formnovalidate='formnovalidate')
            )

class VisitorForm(ModelForm):

    class Meta:
        model = Visitor
        fields = ['first_name', 'last_name']

    visitors = forms.ChoiceField()
    person_id = forms.CharField(required=False)

    def __init__(self, *args, **kwargs):
        person_id = kwargs.pop('person_id', None)
        junior = kwargs.pop('junior', False)
        super().__init__(*args, **kwargs)
        if person_id:
            visitor_ids = VisitorBook.objects.filter(member_id=person_id, visitor__junior=junior).values('visitor_id').distinct()
        else:
            visitor_ids = VisitorBook.objects.filter(visitor__junior=junior).values('visitor_id').distinct()
        visitors = Visitor.objects.filter(pk__in=visitor_ids).order_by('first_name', 'last_name')
        self.fields['visitors'].choices = [('0', '-- Select a visitor --')] + [(v.id, v.fullname) for v in visitors]

    def clean(self):
        cleaned_data = super().clean()
        visitor_id = cleaned_data.get('visitors', '')
        # if user selected existing visitor, ensure no required errors from name fields
        if visitor_id != '0':
            self.errors.clear()
            self.cleaned_data['first_name'] = "x"
            self.cleaned_data['last_name'] = "x"
        return self.cleaned_data


    def clean_first_name(self):
        return self.cleaned_data['first_name'].title()

    def clean_last_name(self):
        return self.cleaned_data['last_name'].title()


class AppForm(ModelForm):

    class Meta:
        model = PosApp
        fields = ['name', 'description', 'layout', 'allow_juniors', 'view_name', 'bar_system', 'main_system',
                  'enabled', 'index', 'attended', 'event']

    layout = forms.ModelChoiceField(required=False, queryset=Layout.objects.all())
    event = forms.ModelChoiceField(required=False, queryset=Event.objects.filter(active=True, online_entry=True))

    def __init__(self, *args, **kwargs):
        delete = kwargs.pop('delete', None)
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.layout = CrispyLayout(
            Div(
                'name', 'description', 'layout', 'allow_juniors', 'view_name', 'bar_system', 'main_system',
                'enabled', 'index', 'attended', 'event',
            ),
            FormActions(
                SubmitButton('save', 'Save', css_class='btn-primary'),
                SubmitButton('cancel', 'Cancel', css_class='btn-default', formnovalidate='formnovalidate')
            )
        )
        if delete:
            self.helper.layout[1].insert(
                1, SubmitButton('delete','Delete', css_class='btn-danger', formnovalidate='formnovalidate')
            )

    def clean_view_name(self):
        view_name = self.cleaned_data['view_name']
        try:
            reverse(view_name)
        except NoReverseMatch:
            raise forms.ValidationError('Bad view name')
        return view_name


class DobForm(forms.Form):

    dob = forms.DateField(widget=forms.DateInput(attrs={'placeholder': 'DD/MM/YYYY'}))


class TickerForm(ModelForm):

    class Meta:
        model = Ticker
        fields = ['message', 'apps']

    def __init__(self, *args, **kwargs):
        delete = kwargs.pop('delete', None)
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.layout = CrispyLayout(
            Div(
                'message',
                'apps',
                css_class="well"
                ),
            FormActions(
                SubmitButton('save', 'Save', css_class='btn-primary'),
                SubmitButton('cancel', 'Cancel', css_class='btn-default', formnovalidate='formnovalidate')
            )
        )
        if delete:
            self.helper.layout[1].insert(
                1, SubmitButton('delete', 'Delete', css_class='btn-danger', formnovalidate='formnovalidate')
            )