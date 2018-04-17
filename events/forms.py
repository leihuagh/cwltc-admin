from django import forms
from crispy_forms.helper import FormHelper
from django.forms import Form, ModelForm, ModelMultipleChoiceField, HiddenInput, inlineformset_factory
from events.models import Event

class EventForm(ModelForm):

    class Meta:
        model = Event
        fields = [
            'name',
            'description',
            'event_type',
            'start_date',
            'end_date',
            'cost',
            'item_type'
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_tag = False

