from django import forms
from django.forms import Form, ModelForm
from django.contrib.auth.models import User
from crispy_forms.helper import FormHelper, Layout
from crispy_forms.layout import Layout, Div, Submit, HTML, Button, Row, Field, Fieldset, ButtonHolder, BaseInput 
from members.forms import SubmitButton
from members.models import AdultApplication, Person, Address

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

class RegisterForm(Form):
    '''
    Register an existing member with the auth system
    '''
    first_name = forms.CharField(max_length=30)
    last_name = forms.CharField(max_length=30)
    email = forms.EmailField(max_length=75)
    post_code = forms.CharField(max_length=10)

    def __init__(self, *args, **kwargs):
        super(RegisterForm, self).__init__(*args, **kwargs)    
        self.helper = FormHelper()
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-sm-2'
        self.helper.field_class = 'col-sm-4 '
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            Fieldset('Enter the following information to identify yourself',
            'first_name', 'last_name', 'email', 'post_code'),
            Div(
                ButtonHolder(
                    SubmitButton('submit', 'Next', css_class='btn-success'),
                    HTML('<a href="{% url "public-home" %}" class="btn btn-default">Cancel</a>')
                    ),
                css_class = 'col-sm-offset-2')
            )

    def clean(self):
        cleaned_data = super(RegisterForm, self).clean()
        first_name = cleaned_data.get('first_name')
        last_name = cleaned_data.get('last_name')
        email = cleaned_data.get('email')
        post_code= cleaned_data.get('post_code').replace(' ','').lower()
        people = Person.objects.filter(first_name=first_name,
                                    last_name=last_name,
                                    email=email)
        if len(people) == 0:
            raise forms.ValidationError("No matching person")
        if len(people) == 1:
            self.person = people[0]
        else:
            for p in people:
                if p.sub:
                    if p.sub.membership.isadult:
                        self.person = p
                        break
        
        if not self.person:
            raise forms.ValidationError('No matching member found', code='invalid')
        if not self.person.address.post_code.replace(" ","").lower() == post_code:
            raise forms.ValidationError('Post code is wrong', code='invalid')
        if self.person.state == Person.RESIGNED:
            raise forms.ValidationError('You cannot register because you have resigned from the club', code='invalid')
        if self.person.state != Person.ACTIVE:
            raise forms.ValidationError('You must be an active member to register', code='invalid')
        sub = self.person.sub
        if not sub:
            raise forms.ValidationError('You must be a subscribed member to register', code='invalid')
        if not sub.paid:
            raise forms.ValidationError('You must have a current paid subscription to register', code='invalid')
        if not sub.membership.is_adult:
            raise forms.ValidationError('Only adult members can register', code='invalid')
        self.cleaned_data['person'] = self.person
        return self.cleaned_data
            
    
class RegisterTokenForm(Form):
    '''
    Stage 2 - user defines a username and password
    '''
    username = forms.CharField(max_length=30)
    password = forms.CharField(max_length=30, widget=forms.PasswordInput)
    password_again = forms.CharField(max_length=30, widget=forms.PasswordInput)
    pin = forms.CharField(max_length=8, widget=forms.NumberInput, required=False)

    def __init__(self, *args, **kwargs):
        super(RegisterTokenForm, self).__init__(*args, **kwargs)    
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            Fieldset('Choose a username and password',
            'username', 'password', 'password_again',  HTML('The PIN is optional - it will give you fast access to the bar system')),
            'pin',
            ButtonHolder(
                SubmitButton('submit', 'Register', css_class='btn-primary'),
                HTML('<a href="{% url "public-home" %}" class="btn btn-primary">Cancel</a>')
                )
            )

    def clean(self):
        cleaned_data = super(RegisterTokenForm, self).clean()
        username = cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError('Sorry, that user name is already taken', code='invalid_user')
        if len(username) < 8:
            raise forms.ValidationError('User name must be at least 8 characters long', code='invalid_user')
        password = cleaned_data.get('password')       
        if len(password) < 8:
            raise forms.ValidationError("Password must be at least 8 characters long", code='invalid_password')
        if password != cleaned_data.get('password_again'):
            raise forms.ValidationError('Passwords do not match', code='invalid_password')
       
       # Pasword must contain at least 1 character and 1 number and be at least 8 characters
        # https://djangosnippets.org/snippets/2551/       
      
        # Setup Our Lists of Characters and Numbers
        characters = list(ascii_letters)
        numbers = [str(i) for i in range(10)]
        
        # Assume False until Proven Otherwise
        numCheck = False
        charCheck = False

        # Loop until we Match        
        for char in password: 
            if not charCheck:
                if char in characters:
                    charCheck = True
            if not numCheck:
                if char in numbers:
                    numCheck = True
            if numCheck and charCheck:
                break
        
        if not numCheck or not charCheck:
            raise forms.ValidationError(u'Your password must include at least \
                                          one letter and at least one number.', code='invalid_password')
        
        return self.cleaned_data

