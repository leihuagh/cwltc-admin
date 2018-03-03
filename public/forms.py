import string
import re
import requests
import json
from django import forms
from django.forms import Form, ModelForm, HiddenInput, RadioSelect
from django.contrib.auth.models import User
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Div, HTML, Field
from crispy_forms.bootstrap import FormActions
from members.forms import SubmitButton
from members.models import AdultApplication, Person, Address, Membership, JuniorProfile


class ContactForm(Form):
    """ Contact form to notify resignation """
    message = forms.CharField(max_length=2000, required=True, widget=forms.Textarea)
    email = forms.EmailField(required=True)

    def __init__(self, *args, **kwargs):
        resigned = kwargs.pop('resigned', False)
        super(ContactForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        post_text = 'submit'
        if resigned:
            post_text = 'resign'
        self.helper.add_input(SubmitButton(post_text, 'Send', css_class='btn-success'))


class RegisterForm(Form):
    """
    Register an existing member with the auth system
    """
    first_name = forms.CharField(max_length=30)
    last_name = forms.CharField(max_length=30)
    email = forms.EmailField(max_length=75, help_text="This must be the email you registered with the club")
    post_code = forms.CharField(max_length=10)

    def __init__(self, *args, **kwargs):
        hide_name = kwargs.pop('hide_name', None)
        super().__init__(*args, **kwargs)
        if hide_name:
            self.fields['first_name'].widget = HiddenInput()
            self.fields['last_name'].widget = HiddenInput()
        self.helper = FormHelper()
        self.helper.form_class = 'form'
        self.helper.form_tag = False
        self.helper.help_text_inline = True
        self.person = None

    def clean(self):
        cleaned_data = super(RegisterForm, self).clean()
        first_name = cleaned_data.get('first_name')
        last_name = cleaned_data.get('last_name')
        email = cleaned_data.get('email')
        post_code = cleaned_data.get('post_code')
        if post_code:
            post_code = post_code.replace(' ', '').lower()
        people = Person.objects.filter(first_name__iexact=first_name,
                                       last_name__iexact=last_name,
                                       email__iexact=email)
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
            raise forms.ValidationError('No matching person found', code='invalid')
        if not self.person.address.post_code.replace(' ', '').lower() == post_code:
            raise forms.ValidationError('Post code is wrong', code='invalid')
        if self.person.state == Person.RESIGNED:
            raise forms.ValidationError('You cannot register because you have resigned from the club', code='invalid')
        if self.person.state != Person.ACTIVE:
            raise forms.ValidationError('You must be an active member to register', code='invalid')
        sub = self.person.sub
        if not sub:
            raise forms.ValidationError('You must have a membership subscription to register', code='invalid')
        if not sub.paid:
            raise forms.ValidationError('You must have a current paid subscription to register', code='invalid')
        if not sub.membership.is_adult:
            raise forms.ValidationError('Only adult members can register', code='invalid')
        self.cleaned_data['person'] = self.person
        return self.cleaned_data
            
    
class RegisterTokenForm(Form):
    """
    Stage 2 - user defines a username and password
    """
    username = forms.CharField(max_length=30, min_length=8,
                               help_text="We have made your username your email address."
                                         " You can change it but it must contain at least 8 characters.")
    password = forms.CharField(max_length=30, min_length=8, widget=forms.PasswordInput,
                               help_text="Your password must be 8 characters or more and contain"
                                         " at least 1 letter and 1 number.")
    password_again = forms.CharField(max_length=30, min_length=8, widget=forms.PasswordInput)
    pin = forms.CharField(max_length=8, min_length=4, widget=forms.PasswordInput,
                          required=False, label="PIN",
                          help_text="The PIN is optional and is 4 to 8 digits long.")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_tag = False
        self.helper.help_text_inline = True

    def clean(self):
        cleaned_data = super(RegisterTokenForm, self).clean()
        username = cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError('Sorry, that user name is already taken', code='invalid_user')
        if len(username) < 8:
            raise forms.ValidationError('Your user name must be at least 8 characters long', code='invalid_user')
        password = cleaned_data.get('password')       
        if len(password) < 8:
            raise forms.ValidationError("Your password must be at least 8 characters long", code='invalid_password')
        if password != cleaned_data.get('password_again'):
            raise forms.ValidationError('Passwords do not match', code='invalid_password')
       
        # Password must have at least 1 character and 1 number     
        num_check = False
        char_check = False     
        for char in password: 
            if not char_check:
                if char in string.ascii_letters:
                    char_check = True
            if not num_check:
                if char in string.digits:
                    num_check = True
            if num_check and char_check:
                break
        
        if not num_check or not char_check:
            raise forms.ValidationError('Your password must include at least \
                                         one letter and at least one number.', code='invalid_password')
        return self.cleaned_data


# class ConsentForm(ModelForm):
#     """ Get consent flags """
#     class Meta:
#         model = Person
#         fields = ['allow_email', 'allow_phone', 'allow_marketing', ]
#
#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         self.helper = FormHelper(self)
#         self.helper.field_template ='public/field.html'
#         self.helper.form_tag = False


# Forms for the application process


class NameForm(ModelForm):
    """
    Capture name but with no form tag because
    may be combined with address form
    """   
    class Meta:
        model = Person
        fields = [
                'first_name',
                'last_name',
                'gender',
                'dob',
                'email',
                'mobile_phone'
                ]
        widgets = {'dob': forms.DateInput(attrs={'placeholder': 'DD/MM/YYYY'})}
    
    form_type = forms.CharField(initial='Name', widget=HiddenInput, required=False)

    def __init__(self, *args, **kwargs):
        adult = kwargs.pop('adult', True)
        super().__init__(*args, **kwargs)
        if not adult:
            del self.fields['dob']
            del self.fields['gender']
        self.helper = FormHelper(self)
        self.helper.form_class = 'form-horizontal'
        self.helper.form_tag = False
        self.helper.disable_csrf = True

    def clean_first_name(self):
        return self.cleaned_data['first_name'].title()

    def clean_last_name(self):
        return self.cleaned_data['last_name'].title()

    def clean_mobile_phone(self):
        return clean_mobile(self.cleaned_data['mobile_phone'])


class AddressForm(ModelForm):
    """
    Capture address but with no form tag
    because may be combined with name form
    """   
    class Meta:
        model = Address
        fields = ['address1', 'address2', 'town', 'post_code', 'home_phone']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_tag = False
        self.helper.disable_csrf = True

    def clean_address1(self):
        return self.cleaned_data['address1'].title()

    def clean_address2(self):
        return self.cleaned_data['address2'].title()

    def clean_town(self):
        return self.cleaned_data['town'].title()

    def clean_post_code(self):
        url = 'https://api.postcodes.io/postcodes/' + self.cleaned_data['post_code']
        r = requests.get(url)
        if r.status_code == 200:
            content = json.loads(r.text)
            return content['result']['postcode']
        raise forms.ValidationError('Post code is invalid')

    def clean_home_phone(self):
        return clean_phone(self.cleaned_data['home_phone'])


class AdultProfileForm(ModelForm):
    """
    Capture adult profile
    """   
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
        disabled = kwargs.pop('disabled', False)
        super().__init__(*args, **kwargs)
        self.fields['membership_id'].choices = choices
        if disabled:
            for key in self.fields:
                self.fields[key].disabled = True
        self.helper = FormHelper(self)
        self.helper.field_template ='public/field.html'
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Div(
                Div('form_type', 'membership_id',
                    HTML("""{% load members_extras %}
                    {% for mem in memberships %}
                    <strong>{{ mem|index:0 }} membership</strong><br/>
                    Annual fee: &pound;{{ mem|index:1 }}
                    {% if mem|index:2 %} + Joining fee: &pound;{{ mem|index:2 }} {% endif %}<br/>
                    {{ mem|index:3 }}<br/><br/>
                    {% endfor %}"""),
                    css_class="col-lg-6"),
                Div('club', 'ability', HTML("Tick all activities that interest you:"),
                    'singles', 'doubles', 'coaching1', 'coaching2', 'daytime',
                    'family', 'social', 'competitions', 'teams',
                    css_class="col-lg-6"),
                css_class="row")
        )


class AdultContactForm(Form):
    """ Contact details for additional adult family member """
    form_type = forms.CharField(initial='Contact', widget=HiddenInput, required=False)
    mobile_phone = forms.CharField(max_length=20)
    email = forms.EmailField(max_length=75)
    confirmation = forms.BooleanField(label="Confirm you have this person's permission to enter their details")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.field_template ='public/field.html'
        self.helper.form_tag = False
        self.helper.render_required_fields = False


class FamilyMemberForm(NameForm):
    """
    Capture family member name and dob
    """  
    def __init__(self, *args, **kwargs):
        dob_needed = kwargs.pop('dob_needed', False)
        super().__init__(*args, **kwargs)
        if dob_needed:
             self.fields['dob'].required = True
        del self.fields['email']
        del self.fields['mobile_phone']
        self.helper = FormHelper(self)
        self.helper.form_tag = False
        self.helper.render_required_fields = False


class JuniorProfileForm(ModelForm):
    class Meta:
        model = JuniorProfile
        fields = [
            'needs',
            'contact0',
            'phone0',
            'relationship0',
            'contact1',
            'phone1',
            'relationship1',
            'contact2',
            'phone2',
            'relationship2',
            'coaching1',
            'coaching2'
            ]

    # these fields are represented by radio buttons that update a boolean
    # '0' = not set, '1' = False, '2' = True
    rad_has_needs = forms.CharField()
    rad_photo_consent = forms.CharField()
    #test = forms.BooleanField(widget=RadioSelect(choices = ((None, 'Not selected'),(True, 'yes is do'),(False, 'No I dont'))))

    form_type = forms.CharField(initial='Child', widget=HiddenInput, required=False)
    membership_id = forms.CharField(required=False, widget=HiddenInput)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_tag = False
        for field_name, field in self.fields.items():
            if field_name not in ['needs','contact0', 'phone0', 'relationship0', 'coaching1', 'coaching2']:
                field.widget.attrs = {'placeholder': field.label}
                field.label = ""


class ApplyNextActionForm(Form):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_tag = False


# class ConsentForm(Form):
#     PHOTO_CHOICES = ((True, 'I give consent to photographs being taken of my child'),
#                      (False, 'I do not give consent to photographs being taken of my child')
#                      )
#     EMAIL_CHOICES = ((True, 'Yes, send me marketing emails'),
#                      (False, 'No, do not send me marketing emails')
#                      )
#     DATABASE_CHOICES = ((True, 'Yes, include my email and phone number in the members database'),
#                         (False, 'No, do not include me')
#                        )
#     photo_consent = forms.BooleanField(required=True, widget=RadioSelect(choices=PHOTO_CHOICES))
#     email_consent = forms.BooleanField(required=True, widget=RadioSelect(choices=EMAIL_CHOICES))
#     database_consent = forms.BooleanField(required=True, widget=RadioSelect(choices=CONTACT_CHOICES))
#     rules = forms.BooleanField(required=True, label="I agree to be bound by the club rules")
#
#     def __init__(self, *args, **kwargs):
#         kwargs.pop('delete', False)
#         children = kwargs.pop('children', None)
#         super(ApplySubmitForm, self).__init__(*args, **kwargs)
#         if not children:
#             del self.fields['photo_consent']


class CampFindRecordForm(Form):
    email = forms.EmailField(max_length=75, required=True)
    last_name = forms.CharField(max_length=30, required=True)
    post_code = forms.CharField(max_length=15, required=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.field_template='public/field.html'
        self.helper.form_tag = False


def clean_mobile(input):
    """ Clean format a mobile number"""
    input = input.replace(" ", "")
    if input:
        rule1 = re.compile(r'^07\d{9}$')
        if rule1.match(input):
            return input[0:5] + ' ' + input[5:]
        else:
            rule2 = re.compile(r'^(?:\+?\d{1,2})?[07]\d{9,13}$')
            if rule2.match(input):
                return input[0:3] + ' ' + input[3:8] + ' ' + input[8:]
            else:
                raise forms.ValidationError("Bad mobile number")
    return ""

def clean_phone(input):
    """ Clean format a phone number """
    input = input.replace(" ", "")
    if input:
        rule = re.compile(r'^0\d{10,13}$')
        if rule.match(input):
            if input[0:3] == '020':
                return input[0:3] + ' ' + input[3:7] + ' ' + input[7:]
            else:
                return input[0:5] + ' ' + input[5:]
        else:
            raise forms.ValidationError("Bad phone number")
    return ""