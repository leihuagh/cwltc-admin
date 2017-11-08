from django import forms
from django.forms import Form, ModelForm, HiddenInput, RadioSelect
from django.contrib.auth.models import User
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Div, Submit, HTML, Fieldset, ButtonHolder
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
        ]

    def __init__(self, *args, **kwargs):
        delete = kwargs.pop('delete', None)
        super(ItemForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.layout = Layout(
            Div(
            'description',
            'button_text',
            'sale_price',
            'cost_price',
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
        fields = [
            'name',
            'invoice_itemtype',
        ]

    def __init__(self, *args, **kwargs):
        delete = kwargs.pop('delete', None)
        super(LayoutForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.layout = Layout(
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

