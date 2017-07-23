from datetime import datetime
from django.shortcuts import render, render_to_response, redirect, get_object_or_404
from django.views.generic import DetailView, TemplateView, CreateView, View
from django.core.signing import Signer
from django.core.mail import send_mail
from django.core.urlresolvers import reverse, reverse_lazy
from django.contrib import messages
from django.contrib.auth.models import User
from django.http import HttpResponse
from formtools.wizard.views import SessionWizardView
from django.views.generic.edit import FormView, ProcessFormView
from django.forms import Form, inlineformset_factory

from members.models import Group, Invoice, Person, MailType, AdultApplication, Settings, Subscription
from members import mail
from members.services import group_get_or_create
from members.forms import JuniorForm, PersonForm
from gc_app.views import gc_create_bill_url
#from .forms import ContactForm, AdultApplicationFormHelper, RegisterForm, RegisterTokenForm
from .forms import *
from members.services import membership_from_dob

# ================= Public Views accessed through a token

class MailTypeSubscribeView(TemplateView):
    '''
    Displays a form with checkboxes that allows a user to unsubscribe
    '''
    template_name = 'public/mailtype_manage.html'

    def get_context_data(self, **kwargs):
        context = super(MailTypeSubscribeView, self).get_context_data(**kwargs)
        self.get_person()
        context['person'] = self.person
        if self.person:
            mailtypes = MailType.objects.all().order_by('can_unsubscribe')
            for m in mailtypes:
                if m.person_set.filter(id=self.person.id).exists():
                    m.subscribed = False
                else:
                    m.subscribed = True
            context['mailtypes'] = mailtypes
        return context

    def get_person(self):
        self.person = None
        person_id = None
        self.token = self.kwargs.pop('token', None)
        if self.token:
            try:
                signer = Signer()
                person_id = signer.unsign(self.token)
            except:
                pass
        else:
            if self.request.user.is_authenticated:
                person_id = self.kwargs.pop('person', None)
        if person_id:
            self.person = Person.objects.get(pk=person_id)

    def post(self, request, *args, **kwargs):
        self.get_person()
        checklist = request.POST.getlist('checks')
        mailtypes = MailType.objects.all()
        for m in mailtypes:
            if str(m.id) in checklist:
                m.person_set.remove(self.person)
            else:
                m.person_set.add(self.person)
        if self.token:
            return render_to_response('public/mailtype_done.html')
        else:
            messages.info(request, "Your mail choices have been saved")
            return redirect(self.person)

class InvoicePublicView(DetailView):
    model = Invoice
    template_name = 'public/invoice_public.html'

    def get_object(self, querset=None):
        signer = Signer()
        try:
            invoice_id = signer.unsign(self.kwargs['token'])
            self.invoice = Invoice.objects.get(pk = invoice_id)
        except:
            self.invoice = None
        return self.invoice

    def get_context_data(self, **kwargs):
        context = super(InvoicePublicView, self).get_context_data(**kwargs)
        if self.invoice:
            self.invoice.add_context(context)
            context['token'] = self.kwargs['token']
        return context

    def post(self, request, *args, **kwargs):
        invoice = self.get_object()
        if 'pay' in request.POST:
            return redirect(gc_create_bill_url(invoice))
        if 'query' in request.POST:
            group = group_get_or_create("2017Query")
            invoice.person.groups.add(group)
            return redirect(reverse('contact-person', kwargs={'person_id': invoice.person.id}))
        elif 'resign' in request.POST:
            group = group_get_or_create("2017Resign")
            invoice.person.groups.add(group)
            return redirect(reverse('contact-resigned', kwargs={'person_id': invoice.person.id}))

class ContactView(FormView):
    form_class = ContactForm
    template_name = 'public/crispy_form.html'
    resigned = False

    def get_context_data(self, **kwargs):
        context = super(ContactView, self).get_context_data(**kwargs)
        if self.resigned:
            context['title'] = "Resignation"
            context['message'] = "Please tell us briefly why you have resigned"
        else:
            context['title'] = "Send message to club management"
        return context

    def form_valid(self, form):
        id = self.kwargs.get('person_id')
        if id:
            try:
                person = Person.objects.get(pk=id)
                message = "From {} id {} >".format(person.email, person.id)
            except Person.DoesNotExist:
                message = "From bad person id {} >".format(id)         
        else:
            message = ""
        message += form.cleaned_data['email']
        message += '  '
        if self.resigned:
            message += 'Resignation:  '
        else:
            message += 'Query:  '
        message += form.cleaned_data['message']
        send_mail(subject='CWLTC contact',
                  from_email='contact@coombewoodltc.co.uk',
                  message=message,
                  recipient_list=["subs.cwltc@gmail.com","is@ktconsultants.co.uk"]
                  )
        if self.resigned:
            return redirect('public-resigned')
        else:
            return redirect('public-thankyou')
        
    def form_invalid(self, form):
        return super(ContactView, self).form_invalid(form)  


class ResignedView(TemplateView):
    template_name = 'public/resigned.html'


class ThankyouView(TemplateView):
    template_name = 'public/thankyou.html'


class PublicHomeView(TemplateView):
    template_name = 'public/home.html'


class RegisterView(FormView):
    '''
    Capture details of an existing member so they
    can register for the system
    '''
    template_name = 'public/crispy_form.html'
    form_class = RegisterForm

    def form_valid(self, form):
        person = form.cleaned_data['person']
        if person.auth_id:
            user = User.objects.filter(pk=person.auth_id)
            if len(user) == 1:
                messages.error(self.request, 'You area already registered wwth username {}'.format(user[0].username))
                return redirect('public-login')
        signer = Signer()
        token = signer.sign(person.id)
        return redirect('public-register2', token=token)
   

class RegisterTokenView(FormView):
    '''
    Register a member identified in a token
    Creates a link from Person to User in auth system
    '''
    template_name = 'public/crispy_form.html'
    form_class = RegisterTokenForm

    def form_valid(self, form):
        username = form.cleaned_data['username']
        password  = form.cleaned_data['password']
        signer = Signer()
        person_id = signer.unsign(self.kwargs['token'])
        try:
            person = Person.objects.get(pk=person_id)
            person.auth = User.objects.create_user(username, person.email, password,
                                                   first_name=person.first_name,
                                                   last_name=person.last_name)
            person.save()
        except DoesNotExist:
            messages.error('Invalid token')
        return redirect('public-home')


class LoginView(FormView):
    template_name = 'public/start.html'

#========== APPLICATION FORM HANDLING ============

def add_profile(object, request):
    '''
    Add an object to the session's profile list
    '''
    profiles = request.session['profiles']
    profiles.append(object)
    request.session['profiles'] = profiles

def add_session_context(context, request):
    '''
    Add all session variables to context
    '''
    context['person'] = request.session['person']
    context['address'] = request.session['address']
    context['family'] = request.session['family']
    context['profiles'] = request.session['profiles']
    return context

def clear_session(request):
    '''
    Clear session variables
    '''
    request.session['person'] = None
    request.session['address'] = None
    request.session['post'] = None
    request.session['family'] = []
    request.session['profiles'] = []

def add_family(member, request):
    '''
    Add a family member to the session
    '''
    family_list = request.session['family']
    family_list.append(member)
    request.session['family'] = family_list


class Apply(View):
    '''
    Start the application process by initialising session variables
    '''
    def get(self, request, *args, **kwargs):
        clear_session(request)
        return redirect('public-apply-main')       


class ApplyMain(TemplateView):
    '''
    Get name and address of main applicant
    '''
    template_name = 'public/application.html'

    def get(self, request, *args, **kwargs):
        #if request.session.get('person', None):
        #    return redirect('public-apply')
        self.name_form = NameForm()
        self.address_form = AddressForm()
        posted = request.session.get('post', None)
        if posted:
            self.name_form = NameForm(posted)
            self.address_form = AddressForm(posted)
        return render(request, self.template_name, self.get_context_data(**kwargs))

    def post(self, request, *args, **kwargs):
        """
        Handle completed name and address form
        """
        self.name_form = NameForm(request.POST)
        self.address_form = AddressForm(request.POST)
        
        if self.name_form.is_valid() and self.address_form.is_valid():
            if not (self.name_form.cleaned_data['mobile_phone'] or self.address_form.cleaned_data['home_phone']):
                errtext = 'At least one of mobile phone or home phone must be entered'
                self.name_form.add_error('mobile_phone', errtext)
                self.address_form.add_error('home_phone', errtext)
            else:
                request.session['person'] = self.name_form.save(commit=False)
                request.session['address'] = self.address_form.save(commit=False)
                request.session['post'] = request.POST
                if not 'dob' in request.POST:
                    add_profile(None, request)
                    return redirect('public-apply-junior')
                else:
                    dob = self.name_form.cleaned_data['dob']
                    membership_id = membership_from_dob(dob)
                    if membership_id == Membership.FULL:
                        # for now membership.FULL covers all adults
                        # actual adult membership will be determined in profile
                        request.session['person'].membership_id = membership_id
                        return redirect('public-apply-adult')
                self.name_form.add_error(None,"Please enter adult information on this form")
                self.name_form.add_error('dob', "Not an adult's date of birth")
        return render(request, self.template_name, self.get_context_data(**kwargs))

    def get_context_data(self, **kwargs):  
        kwargs['name_form'] = self.name_form
        kwargs['address_form'] = self.address_form
        kwargs['form_title'] = "Adult Application Form"
        return super(ApplyMain, self).get_context_data(**kwargs)


class ApplyAdultView(CreateView):
    '''
    Get adult membership type and profile
    '''
    template_name = 'public/application.html'
    form_class = AdultApplicationForm
    
    def form_valid(self, form):
        add_profile(form.save(commit=False), self.request)
        if 'add' in self.request.POST:
            return redirect('public-apply-add')
        return redirect('public-apply-submit')

    def get_context_data(self, **kwargs):
        kwargs['form_title'] = "Adult Application: " + self.request.session['person'].first_name
        return add_session_context(super(ApplyAdultView, self).get_context_data(**kwargs), self.request)


class ApplyAddView(CreateView):
    '''
    Get name and dob of next family member
    '''
    template_name = 'public/application.html'
    form_class = FamilyMemberForm
    model = Person

    def form_valid(self, form):
        add_family(form.save(commit=False), self.request)

        dob = form.cleaned_data['dob']
        membership_id = membership_from_dob(dob)
        if membership_id == Membership.FULL:
            return redirect('public-apply-adult')
        return redirect('public-apply-junior', membership_id=membership_id )  

    def get_context_data(self, **kwargs):  
        kwargs['form_title'] = "Add family member"
        return add_session_context(super(ApplyAddView, self).get_context_data(**kwargs), self.request)


class ApplyJuniorView(FormView):
    '''
    Just confirm junior or cadet and get next action
    '''
    template_name = 'public/application.html'
    form_class = ApplyJuniorForm

    def form_valid(self, form):
        family = self.request.session['family']
        family[-1].membership_id = self.kwargs['membership_id']
        self.request.session['family'] = family

        add_profile(None, self.request)

        if 'add' in self.request.POST:
            return redirect('public-apply-add')
        return redirect('public-apply-submit')
    
    def get_context_data(self, **kwargs):
        membership = Membership.objects.get(pk=self.kwargs['membership_id']).description
        person = self.request.session['family'][-1]
        kwargs['form_title'] = membership + ': ' + person.first_name + ' ' + person.last_name
        return add_session_context(super(ApplyJuniorView, self).get_context_data(**kwargs), self.request)


class ApplySubmitView(FormView):
    '''
    Confirm everything and get acceptance
    Add all to database
    '''
    template_name='public/application.html'
    form_class = ApplySubmitForm

    def form_valid(self, form):
        person = self.request.session['person']
        address = self.request.session['address']
        family = self.request.session['family']
        profiles = self.request.session['profiles']
        index = 0
        if person:
            address.save()
            person.address = address
            person.state = Person.APPLIED
            person.date_joined = datetime.today()
        
            if profiles[index]:
                person.membership_id = profiles[index].membership_id
                person.save()
                profiles[index].person = person
                profiles[index].save()
            else:
                person.membership_id = Membership.NON_MEMBER
                person.save()
            index += 1   
            for kid in family:
                kid.linked = person
                kid.address = address
                kid.state = Person.APPLIED
                kid.date_joined = person.date_joined
                kid.save()
                if profiles[index]:
                    profiles[index].person = kid
                    profiles[index].save()
                index += 1            
            clear_session(self.request)
            return redirect('public-apply-thankyou')
        else:
            form.add_error(None, "This form has already been submitted.",)
            return render(self.request, self.template_name, self.get_context_data(form=form))

    def get_context_data(self, **kwargs):
        return add_session_context(super(ApplySubmitView, self).get_context_data(**kwargs), self.request)


class ApplyThankyouView(TemplateView):
    template_name = 'public/apply_thankyou.html'
