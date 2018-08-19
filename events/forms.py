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
            'date',
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
            'slogan',
            'description',
            'date',
            'time',
            'cutoff_date',
            'cost',
            'image',
            'active',
        ]
        # widgets = {'date': DatePicker(options=dateOptions),
        #            'cutoff_date': DatePicker(options=dateOptions),
        #            'description': forms.Textarea(),
        #            }
        widgets = {'description': forms.Textarea()}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['date'].required = True
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


class AdminRegisterForm(RegisterForm):

    person_id = forms.IntegerField(widget=forms.HiddenInput)