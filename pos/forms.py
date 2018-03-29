from django import forms
from django.forms import ModelForm, ModelChoiceField
from django.forms.widgets import TextInput
from django.contrib.auth.models import User
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout as CrispyLayout, Div
from crispy_forms.bootstrap import FormActions
from .models import *
from members.forms import SubmitButton


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
        super(ItemForm, self).__init__(*args, **kwargs)
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
        fields = ['name']

    def __init__(self, *args, **kwargs):
        delete = kwargs.pop('delete', None)
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.layout = CrispyLayout(
            Div(
            'name',
            'invoice_itemtype',
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
