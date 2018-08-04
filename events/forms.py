from django import forms
from crispy_forms.helper import FormHelper
from django.forms import Form, ModelForm, ModelMultipleChoiceField, HiddenInput, inlineformset_factory
from events.models import Event, Tournament

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
            'item_type',
            'active',
            'online_entry'
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_tag = False


class TournamentForm(ModelForm):

    class Meta:
        model = Tournament
        fields = ['name', 'description', 'draw_date', 'finals_date', 'event_cost']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_tag = False