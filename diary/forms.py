from django import forms
from crispy_forms.helper import FormHelper, Layout
from django.forms import ModelForm
from diary.models import Booking
from events.models import Tournament

class BookingForm(ModelForm):

    class Meta:
        model = Booking
        fields = ['note']

    player_2_id = forms.ChoiceField(required=False, label="Player 2")
    doubles = forms.BooleanField(required=False, label="Doubles match")
    player_3_id = forms.ChoiceField(required=False, label="Player 3")
    player_4_id = forms.ChoiceField(required=False, label="Player 4")
    blocked = forms.BooleanField(required=False)

    def __init__(self, *args, **kwargs):
        admin = kwargs.pop('admin', False)
        super().__init__(*args, **kwargs)
        players = Tournament.objects.get(pk=1).players_list(for_choice_field=True)
        self.fields['player_2_id'].choices = players
        self.fields['player_3_id'].choices = players
        self.fields['player_4_id'].choices = players
        self.helper = FormHelper(self)
        self.helper.form_tag = False
        self.helper.layout = Layout(
            'player_2_id', 'doubles', 'player_3_id', 'player_4_id', 'note'
        )
        if admin:
            self.helper.layout.append('blocked')

    def clean(self):
        super().clean()
        message='Please select a player'
        if self.cleaned_data['blocked']:
            self.cleaned_data['player_2_id'] = None
            self.cleaned_data['player_3_id'] = None
            self.cleaned_data['player_4_id'] = None
            return

        if not self.cleaned_data['player_2_id']:
            self.add_error('player_2_id', message)
        if self.cleaned_data['doubles']:
            if not self.cleaned_data['player_3_id']:
                self.add_error('player_3_id', message)
            if not self.cleaned_data['player_4_id']:
                self.add_error('player_4_id', message)
        else:
            self.cleaned_data['player_3_id'] = None
            self.cleaned_data['player_4_id'] = None