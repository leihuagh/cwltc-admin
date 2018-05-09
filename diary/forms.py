from django import forms
from crispy_forms.helper import FormHelper
from django.forms import ModelForm
from diary.models import Booking

class BookingForm(ModelForm):

    class Meta:
        model = Booking
        fields = ['note']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_tag = False
