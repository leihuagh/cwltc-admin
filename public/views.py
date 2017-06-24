from django.shortcuts import render, render_to_response, redirect, get_object_or_404
from django.views.generic import DetailView, TemplateView, CreateView
from django.core.signing import Signer
from django.core.urlresolvers import reverse
from django.contrib import messages
from django.contrib.auth.models import User
from django.views.generic.edit import FormView, ProcessFormView
from django.forms import Form, inlineformset_factory

from members.models import Group, Invoice, Person, MailType, AdultApplication
from members import mail
from members.services import group_get_or_create
from members.forms import JuniorForm, PersonForm
from gc_app.views import gc_create_bill_url
from .forms import ContactForm, AdultApplicationFormHelper, RegisterForm, RegisterTokenForm

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
    template_name = 'public/contact.html'
    resigned = False

    def get_context_data(self, **kwargs):
        context = super(ContactView, self).get_context_data(**kwargs)
        if self.resigned:
            context['message'] = "Please tell us briefly why you have resigned"
        else:
            context['message'] = "Please enter your query"
        return context

    def form_valid(self, form):
        if self.kwargs['person_id']:
            person = Person.objects.get(pk=self.kwargs['person_id'])
            message = "From {} id {} >".format(person.email, person.id)
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
    template_name = 'public/start.html'


class ApplyJuniorView(FormView):
    model = Person
    template_name = 'members/junior_form.html'
    success_msg = "Junior and parent created"
    form_class = JuniorForm

    def form_invalid(self, form):
        if 'cancel' in form.data:
            return HttpResponseRedirect(reverse('home'))
        return super(JuniorCreateView, self).form_invalid(form)

    def form_valid(self, form):
        self.form = form
        if 'cancel' in form.data:
            return HttpResponseRedirect(reverse('home'))
        return super(JuniorCreateView, self).form_valid(form)

    def get_success_url(self):
        return reverse('sub-create', kwargs={'person_id': self.form.junior.id})


class ApplyAdultView(CreateView):
    model = Person
    template_name = 'public/adult_application.html'
    form_class = PersonForm

    def get_form_kwargs(self):
        kwargs = super(ApplyAdultView, self).get_form_kwargs()
        kwargs.update({'public': True})
        #kwargs.update({'link': self.kwargs['link']})
        return kwargs

    def get(self, request, *args, **kwargs):
        '''
        Handles GET requests and instantiates blank versions of the form
        and its inline formsets.
        '''
        self.object = None
        form_class = self.get_form_class()
        form = self.get_form(form_class)
        formset = inlineformset_factory(Person, AdultApplication,
                                        fields = ['ability',                                          
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
                                                  'source',
                                                  'membership',
                                                  'rules'],
                                        extra=1
                                        )
        helper = AdultApplicationFormHelper()
        return self.render_to_response(
            self.get_context_data(form=form, formset=formset, helper=helper)
            )

    def post(self, request, *args, **kwargs):
        """
        Handles POST requests, instantiating a form instance and its inline
        formsets with the passed POST variables and then checking them for
        validity.
        """
        self.object = None
        form_class = self.get_form_class()
        form = self.get_form(form_class)
        formset = AdultApplicationtFormSet(self.request.POST)
        if form.is_valid() and formset.is_valid():
            return self.form_valid(form, formset)
        else:
            return self.form_invalid(form, formset)

    def form_invalid(self, form):
        if 'cancel' in form.data:
            return redirect('home')
        return self.render_to_response(
            self.get_context_data(form=form, formset=apply_form)
            )

    def form_valid(self, form):
        '''
        Called when all forms are valid
        Creates a person with linked profle
        '''
        if 'cancel' in form.data:
            return redirect('home')
        self.object = form.save()
        apply_form.instance = self.object
        apply_form.save()
        return HttpResponseRedirect(self.get_success_url())


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

