import string
from django import forms
from django.forms import Form, ModelForm, HiddenInput, RadioSelect
from django.contrib.auth.models import User
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Div, Submit, HTML, Fieldset
from crispy_forms.bootstrap import FormActions
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
        super(RegisterForm, self).__init__(*args, **kwargs)    
        self.helper = FormHelper()
        self.helper.form_class = 'form'
        self.helper.help_text_inline = True
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            HTML("<p>You must already be a club member to use this form.</p>"),
            Div(
                Div('first_name', 'last_name', 'email', 'post_code', css_class='card-body green'),
                Div(
                    SubmitButton('submit', 'Next', css_class='btn-success'),
                    HTML('<a href="{% url "public-home" %}" class="btn btn-default">Cancel</a>'),
                    css_class='card-footer'),
                css_class='card')
            )
        self.person = None

    def clean(self):
        cleaned_data = super(RegisterForm, self).clean()
        first_name = cleaned_data.get('first_name')
        last_name = cleaned_data.get('last_name')
        email = cleaned_data.get('email')
        post_code = cleaned_data.get('post_code').replace(' ', '').lower()
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
            raise forms.ValidationError('No matching member found', code='invalid')
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
    username = forms.CharField(max_length=30,
                               help_text="Your user name must contain at least 8 characters.")
    password = forms.CharField(max_length=30, widget=forms.PasswordInput,
                               help_text="Your password must be 8 characters or more and contain at least 1 number.")
    password_again = forms.CharField(max_length=30, widget=forms.PasswordInput)
    pin = forms.CharField(max_length=8, widget=forms.NumberInput, required=False, label="PIN",
                          help_text="The PIN is optional and is 4 to 8 digits long. It is used for fast log in to the bar system.")

    def __init__(self, *args, **kwargs):
        super(RegisterTokenForm, self).__init__(*args, **kwargs)    
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.help_text_inline = True
        self.helper.layout = Layout(
            Div('username', 'password', 'password_again', 'pin', css_class="well"),
            FormActions(
                SubmitButton('submit', 'Register', css_class='btn-success'),
                HTML('<a href="{% url "public-home" %}" class="btn btn-default">Cancel</a>')
                )
            )

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

    # Forms for the application process

    def as_ul(self):
        return super().as_ul()


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
                'mobile_phone',
                'british_tennis',
                'pays_own_bill',
                'notes',
                'state'
                ]
        widgets = {'dob': forms.DateInput(attrs={'placeholder': 'DD/MM/YYYY'})}
    
    form_type = forms.CharField(initial='Name', widget=HiddenInput, required=False)

    def __init__(self, *args, **kwargs):
        adult = kwargs.pop('adult', True)
        restricted_fields = kwargs.pop('restricted_fields', False)
        super(NameForm, self).__init__(*args, **kwargs)
        if restricted_fields:
            del self.fields['state']
            del self.fields['british_tennis']
            del self.fields['pays_own_bill']
            del self.fields['notes']
        if not adult:
            del self.fields['dob']
            del self.fields['gender']
        self.helper = FormHelper(self)
        self.helper.form_class = 'form-horizontal'
        self.helper.form_tag = False
        self.helper.disable_csrf = True


class AddressForm(ModelForm):
    """
    Capture address but with no form tag
    because may be combined with name form
    """   
    class Meta:
        model = Address
        fields = ['address1', 'address2', 'town', 'post_code', 'home_phone']

    def __init__(self, *args, **kwargs):
        super(AddressForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_tag = False
        self.helper.disable_csrf = True


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
        super(AdultProfileForm, self).__init__(*args, **kwargs)
        self.fields['membership_id'].choices = choices
        self.helper = FormHelper(self)
        self.helper.field_template='public/field.html'
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
    confirmation = forms.BooleanField()

    def __init__(self, *args, **kwargs):
        super(AdultContactForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.field_template='public/field.html'
        self.helper.form_tag = False
        self.helper.render_required_fields = False


class FamilyMemberForm(NameForm):
    """
    Capture family member name and dob
    """  
    def __init__(self, *args, **kwargs):
        dob_needed = kwargs.pop('dob_needed', False)
        super(FamilyMemberForm, self).__init__(*args, **kwargs)
        if dob_needed:
             self.fields['dob'].required = True
        del self.fields['email']
        del self.fields['mobile_phone']
        self.helper = FormHelper(self)
        self.helper.form_tag = False
        self.helper.render_required_fields = False


class ChildProfileForm(Form):
    form_type = forms.CharField(initial='Child', widget=HiddenInput, required=False)
    membership_id = forms.CharField(required=False, widget=HiddenInput)
    notes = forms.CharField(max_length=100, required=False,
                            widget=forms.Textarea,
                            label=("Use the box below to describe any special care needs, "
                                   "dietary requirements, allergies or medical conditions:")
                            )
    
    def __init__(self, *args, **kwargs):
        super(ChildProfileForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Div(
                Div(
                    Div('form_type', 'membership_id', 'notes',
                        HTML("In the event of injury, illness or other medical need, "
                             "all reasonable steps will be taken to contact you, "
                             "and to deal with the situation appropriately.")),
                    ),
                ),
            )


class ApplyNextActionForm(Form):

    def __init__(self, *args, **kwargs):
        super(ApplyNextActionForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_tag = False


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
        kwargs.pop('delete', False)
        children = kwargs.pop('children', None)
        super(ApplySubmitForm, self).__init__(*args, **kwargs)
        if not children:
            del self.fields['photo_consent']
