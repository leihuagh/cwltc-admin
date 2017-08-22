from django import forms
from django.forms import Form, ModelForm, HiddenInput, RadioSelect
from django.contrib.auth.models import User
from django.conf import settings
from crispy_forms.helper import FormHelper, Layout
from crispy_forms.layout import Layout, Div, Submit, HTML, Button, Row, Field, Fieldset, ButtonHolder, BaseInput 
from members.forms import SubmitButton
from members.models import AdultApplication, Person, Address, Membership


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
        self.helper.add_input(SubmitButton(postText, 'Send', css_class='btn-success'))


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


    # Forms for the application process

class NameForm(ModelForm):
    '''
    Capture name but with no form tag because
    may be combined with address form
    '''   
    class Meta:
        model = Person
        fields = [
                'first_name',
                'last_name',
                'gender',
                'dob',
                #'state',
                'email',
                'mobile_phone',
                #'british_tennis',
                #'pays_own_bill',
                #'notes']
                ]
        widgets = {'dob': forms.DateInput(attrs={'placeholder':'DD/MM/YYYY'})}
    
    form_type = forms.CharField(initial='Name', widget=HiddenInput, required=False)

    def __init__(self, *args, **kwargs):
        adult = kwargs.pop('adult', True)
        back = kwargs.pop('back', False)
        next = kwargs.pop('next', False)
        super(NameForm, self).__init__(*args, **kwargs)
        if not adult:
            del self.fields['dob']
            del self.fields['gender']
        self.helper = FormHelper(self)
        self.helper.form_tag = False
        self.helper.disable_csrf = True

class AddressForm(ModelForm):
    '''
    Capture address but with no form tag
    because may be combined with name form
    '''   
    class Meta:
        model = Address
        fields = ['address1', 'address2','town','post_code','home_phone']

    def __init__(self, *args, **kwargs):
        super(AddressForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_tag = False
        self.helper.disable_csrf = True


class AdultProfileForm(ModelForm):
    '''
    Capture adult profile
    '''   
    class Meta:
        model = AdultApplication
        fields = [
            'membership_id',
            'ability',                                          
            'singles',
            'doubles',
            'coaching1',
            'coaching2',
            'daytime',
            'family',
            'social',
            'competitions',
            'teams',
            'club',
            ]
    form_type = forms.CharField(initial='Adult', widget=HiddenInput, required=False)

    def __init__(self, *args, **kwargs):
        choices = kwargs.pop('choices', Membership.adult_choices())
        delete = kwargs.pop('delete', False)
        super(AdultProfileForm, self).__init__(*args, **kwargs)
        self.fields['membership_id'].choices = choices
        self.helper = FormHelper(self)
        self.helper.layout = Layout(
            Div(
                    Div(
                        Div('form_type', 'membership_id',
                            HTML("""{% load members_extras %}
                            {% for mem in memberships %}
                            <strong>{{ mem|index:0 }} membership</strong><br/>
                            Annual fee: &pound{{ mem|index:1 }}
                            {% if mem|index:2 %} + Joining fee: &pound{{ mem|index:2 }} {% endif %}<br/>
                            {{ mem|index:3 }}<br/><br/>
                            {% endfor%}"""),   
                            'club',
                            css_class = "well"),    
                        css_class = "col-md-4"),  
                    Div(
                        Div('ability', HTML("<strong>Tick all activities that interest you:</strong>"),
                                 'singles', 'doubles', 'coaching1', 'coaching2', 'daytime', 'family', 'social', 'competitions', 'teams',
                                css_class = "well"),
                    css_class = "col-md-4"),
                css_class = "row"),
            Submit('back', '< Back', css_class='btn btn-success', formnovalidate='formnovalidate'),
            Submit('next', 'Next >', css_class='btn btn-success')
            )
 


class FamilyMemberForm(NameForm):
    '''
    Capture family member name and dob
    '''  
    def __init__(self, *args, **kwargs):
        delete = kwargs.pop('delete', False)
        super(FamilyMemberForm, self).__init__(*args, **kwargs)
        del self.fields['email']
        del self.fields['mobile_phone']
        self.helper = FormHelper(self)
        self.helper.render_required_fields = False
        self.helper.layout = Layout(
            Div(
                Div(
                    Div('form_type', 'first_name', 'last_name', 'gender', 'dob',
                        css_class="well"
                        ),
                    css_class="col-md-4"
                    ),
                css_class="row"
                ),
            Submit('back', '< Back', css_class='btn btn-success', formnovalidate='formnovalidate'),
            Submit('next', 'Next >', css_class='btn-success')
            )
        if delete:
            self.helper.layout.append(Submit('delete', 'Delete applicant', css_class='btn-danger'))


class ChildProfileForm(Form):
    form_type = forms.CharField(initial='Child', widget=HiddenInput, required=False)
    membership_id = forms.CharField(required=False, widget=HiddenInput)
    notes = forms.CharField(max_length=100, required = False,
                           widget=forms.Textarea,
                           label = "Use the box below to describe any special care needs, dietary requirements, allergies or medical conditions:")
    
    def __init__(self, *args, **kwargs):
        delete = kwargs.pop('delete', False)
        super(ChildProfileForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.layout = Layout(
            Div(
                Div(
                    Div('form_type', 'membership_id', 'notes', HTML("In the event of injury, illness or other medical need, all reasonable steps will be taken to contact you, and to deal with the situation appropriately."), css_class="well"),
                    css_class="col-md-6"),
                css_class="row"),
            Submit('back', '< Back', css_class='btn btn-success', formnovalidate='formnovalidate'),
            Submit('next', 'Next >', css_class='btn btn-success')
            )


class ApplyNextActionForm(Form):

    def __init__(self, *args, **kwargs):
        delete = kwargs.pop('delete', False)
        super(ApplyNextActionForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.layout = Layout(
            Submit('back', '< Back', css_class='btn btn-success', formnovalidate='formnovalidate'),
            SubmitButton('add', 'Add a family member', css_class='btn-success'),
            SubmitButton('submit', 'Complete application', css_class='btn-success')
            )

class ApplySubmitForm(Form):
    PHOTO_CHOICES = ((True, 'I give consent to photographs being taken of my child'),
                     (False, 'I do not give consent to photographs being taken of my child')
                     )
    CONTACT_CHOICES = ((True, 'I agree to my email mail and phone number being visible'),
                      (False, 'I do not agree to my mail and phone number being visible')
                      )     
    photo_consent = forms.BooleanField(required=True, widget=RadioSelect(choices=PHOTO_CHOICES))
    contact_consent = forms.BooleanField(required=True, widget=RadioSelect(choices=CONTACT_CHOICES))
    test = forms.TypedChoiceField(widget=RadioSelect(choices=CONTACT_CHOICES))
    rules = forms.BooleanField(required=True, label="I agree to be bound by the club rules")

    def __init__(self, *args, **kwargs):
        delete = kwargs.pop('delete', False)
        children = kwargs.pop('children' , None)
        super(ApplySubmitForm, self).__init__(*args, **kwargs)
        if not children:
            del self.fields['photo_consent']

