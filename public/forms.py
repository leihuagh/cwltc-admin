from django import forms
from django.forms import Form, ModelForm
from crispy_forms.helper import FormHelper, Layout
from crispy_forms.layout import Layout, Div, Submit, HTML, Button, Row, Field, Fieldset, ButtonHolder, BaseInput 
from members.forms import SubmitButton
from members.models import AdultApplication

class ContactForm(Form):
    message = forms.CharField(max_length=2000, required=True, widget=forms.Textarea)
    email = forms.EmailField(required=True)

    def __init__(self, *args, **kwargs):
        resigned = kwargs.pop('resigned', False)
        super(ContactForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        postText = 'submit'
        if resigned:
            postText = 'resign'
        self.helper.add_input(SubmitButton(postText, 'Send', css_class='btn-primary'))

class AdultApplicationForm(ModelForm):
    class Meta:
        model = AdultApplication
        fields = ['ability',
                  'singles', 'doubles', 'coaching1', 'coaching2', 'daytime', 'family', 'social', 'competitions', 'teams',
                  'club', 'source', 'membership', 'rules']
        

class AdultApplicationFormHelper(FormHelper):

    def __init__(self, *args, **kwargs):
        super(AdultApplicationFormHelper, self).__init__(*args, **kwargs)      
        self.form_class = 'form-horizontal'
        self.label_class = 'col-sm-4 '
        self.field_class = 'col-sm-8 '
        self.form_method = 'post'
        self.layout = Layout(
            Fieldset('Please judge your tennis level:', 'ability'),
            Fieldset("Tick all activities that interest you",
                     'singles', 'doubles', 'coaching1', 'coaching2', 'daytime', 'family', 'social', 'competitions', 'teams',
                    ), 
            Fieldset('Name of previous tennis club (if any)', 'club'),
            Fieldset('How did you hear about Coombe Wood?', 'source'),
            Fieldset('Select the membership category', 'membership'),
            Fieldset('I agree to obey the rules of the club', 'rules'), 
            ButtonHolder(
                SubmitButton('submit', 'Save', css_class='btn-primary'),
                SubmitButton('cancel', 'Cancel', css_class='btn-default')
                )
            )