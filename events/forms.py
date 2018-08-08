from django import forms
from crispy_forms.helper import FormHelper
from django.forms import Form, ModelForm, ModelMultipleChoiceField, HiddenInput, inlineformset_factory
from events.models import Event, Tournament
from tempus_dominus.widgets import DatePicker, TimePicker, DateTimePicker

class TournamentEventForm(ModelForm):

    class Meta:
        model = Event
        fields = [
            'name',
            'description',
            'event_type',
            'end_date',
            'cost',
            'active',
            'online_entry'
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_tag = False

dateOptions ={'minDate': '2018-01-01',
              'maxDate': '2040-01-01',
              'format': 'DD/MM/YYYY'}

class SocialEventForm(ModelForm):

    class Meta:
        model = Event
        fields = [
            'name',
            'strap_line',
            'description',
            'end_date',
            'cutoff_date',
            'time',
            'cost',
            'image',
            'active',
            'online_entry'
        ]
        widgets = {'end_date': DatePicker(options=dateOptions),
                   'cutoff_date': DatePicker(options=dateOptions),
                   'time': TimePicker()
                   }


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


class RegisterForm(Form):

    number_of_tickets = forms.IntegerField(min_value=1, max_value=10, initial=1, required=True)
    special_diet = forms.CharField(max_length=100, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_tag = False