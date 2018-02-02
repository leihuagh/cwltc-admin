import logging
from datetime import datetime
from django.shortcuts import render, render_to_response, redirect
from django.views.generic import DetailView, TemplateView, CreateView, View, UpdateView
from django.core.signing import Signer
from django.core.mail import send_mail
from django.conf import settings
from django.core.urlresolvers import reverse
from django.contrib import messages
from django.http import HttpResponse
from django.views.generic.edit import FormView
from django.utils.text import slugify
from django.db import transaction
from members.models import Group, Invoice, Person, MailType, AdultApplication, Settings, Subscription
from members.services import group_get_or_create
from .forms import *
from members.services import membership_from_dob
from cardless.services import detokenise, invoice_payments_list, active_mandate

logger = logging.getLogger(__name__)


class Button(object):
    name = ''
    value = ''
    no_validate = False
    css_class = 'btn'

    def __init__(self, value="submit", name="", css_class='btn-primary', no_validate=False):
        self.value = value
        self.name = slugify(value) if name == "" else name
        self.css_class = 'btn '+ css_class
        self.novalidate = no_validate


# ================= Public Views accessed through a token

class MailTypeSubscribeView(TemplateView):
    """
    Displays a form with checkboxes that allows a user to unsubscribe
    """
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
        mail_types = MailType.objects.all()
        for m in mail_types:
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

    def get_object(self, queryset=None):
        self.invoice = detokenise(self.kwargs['token'], Invoice)
        return self.invoice

    def get_context_data(self, **kwargs):
        context = super(InvoicePublicView, self).get_context_data(**kwargs)
        if self.invoice:
            self.invoice.add_context(context)
            context['token'] = self.kwargs['token']
            context['payments_pending'] = invoice_payments_list(self.invoice, pending=True)
            context['payments_paid'] = invoice_payments_list(self.invoice, paid=True)
        return context

    def post(self, request, *args, **kwargs):
        invoice = self.get_object()
        if 'pay' in request.POST:
            return redirect('cardless_payment_create', kwargs['token'])
        if 'query' in request.POST:
            group = group_get_or_create("2017Query")
            invoice.person.groups.add(group)
            return redirect('public-contact-person', person_id=invoice.person.id)
        elif 'resign' in request.POST:
            group = group_get_or_create("2017Resign")
            invoice.person.groups.add(group)
            return redirect('public-resigned')


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
    """
    Capture details of an existing member so they
    can register for the system
    """
    template_name = 'public/crispy_card.html'
    form_class = RegisterForm

    def get_context_data(self, **kwargs):
        context = super(RegisterView, self).get_context_data(**kwargs)
        context['class'] = 'col-md-4 col-md-push-4'
        context['title'] = 'Register for the club website and bar system'
        return context

    def form_valid(self, form):
        person = form.cleaned_data['person']
        if person.auth_id:
            user = User.objects.filter(pk=person.auth_id)
            if len(user) == 1:
                messages.error(self.request, 'You are already registered with username {}'.format(user[0].username))
            return redirect(self.get_success_url())

        if person.membership and person.membership.is_adult:
            signer = Signer()
            token = signer.sign(person.id)
            return redirect(self.kwargs['next'], token=token)

        messages.error(self.request, 'Sorry, only adult members can register on the site')
        return redirect(self.get_success_url())
   
    def get_success_url(self, **kwargs):
        return reverse('public-home')


class RegisterTokenView(FormView):
    """
    Register a member identified in a token
    Creates a link from Person to User in auth system
    POS overrides this view
    """
    template_name = 'public/crispy_form.html'
    form_class = RegisterTokenForm

    def get_context_data(self, **kwargs):
        context = super(RegisterTokenView, self).get_context_data(**kwargs)
        context['class'] = 'col-md-4 col-md-push-4'
        context['title'] = 'Choose your username and password'
        return context

    def form_valid(self, form):
        signer = Signer()
        person_id = signer.unsign(self.kwargs['token'])
        try:
            person = Person.objects.get(pk=person_id)
            person.create_user(username=form.cleaned_data['username'],
                               password=form.cleaned_data['password'],
                               pin=form.cleaned_data['pin'])
            return redirect(self.get_success_url())
        except Person.DoesNotExist:
            # invalid token cannot occur when using POS
            # so we can safely redirect to public home
            messages.error('Invalid token')
            return redirect('public-home')

    def get_success_url(self, **kwargs):
        return reverse('club_home')


class LoginView(FormView):
    template_name = 'public/start.html'

# ========== APPLICATION FORM HANDLING ============

def add_session_context(context, request):
    """
    Add all session variables to context
    """
    context['person'] = request.session['person']
    context['address'] = request.session['address']
    return context


def clear_session(request):
    """
    Clear session variables
    """
    request.session['person'] = None
    request.session['address'] = None
    request.session['family'] = []
    request.session['posts'] = []


def session_update_post(index, request):
    """
    Save request.POST data in session at index
    """
    posts = request.session['posts']
    request.POST._mutable = True
    request.POST['path'] = request.path
    if index >= len(posts):
        posts.append(request.POST)
    else:
        posts[index] = request.POST
    request.session['posts'] = posts


def session_get_post(index, request):
    """
    Return post data for index else None
    """
    posts = request.session.get('posts', None)
    if posts:
        if index >= 0 and index < len(posts):
            if not (posts[index].get('invalid', False) or posts[index].get('deleted', False)):
                return posts[index]
    return None


def session_last_fullname(index, request):
    """ Return the full name of the last applicant """
    while True:
        index -= 1
        data = session_get_post(index, request)
        if data:
            if data['form_type'] == 'Name':
                return data['first_name'] + " " + data['last_name']
        if index <=0:
            return 'Name error'


def session_delete_post(index, request):
    """
    Delete post data for index
    If it is not the last one in the list,
    delete the next 1 or 2 record ( contact(adults) and profile) too
    """
    posts = request.session['posts']
    if index < len(posts):
        posts[index]['deleted'] = True
        index += 1
        if index < len(posts):
            if posts[index]['form_type'] == 'Contact':
                posts[index]['deleted'] = True
                index += 1
            if index < len(posts):
                posts[index]['deleted'] = True
        request.session.modified = True

def session_invalidate_post(index, request):
    """
    Invalidate post data for index
    Used when child profile is changed to adult profile or vice versa
    """
    posts = request.session['posts']
    if index < len(posts):
        posts[index]['invalid'] = True
        request.session.modified = True


def session_next_index(index, request):
    """
    Return next index, skipping deleted records
    """
    posts = request.session['posts']
    i = index
    while i + 1 < len(posts):
        i += 1
        if not posts[i].get('deleted', False):
            return i
    return len(posts)


def session_back(index, request):
    """
    Return previous path, skipping deleted records
    """
    posts = request.session['posts']
    while index > 0:
        index -= 1
        if not posts[index].get('deleted', False):
            return posts[index]['path']
    return posts[0]['path']


def session_update_kwargs(view, kwargs):
    """
    Update the forms kwargs with stored POST data if it exists
    """
    data = session_post_data(view)
    if data:
        kwargs.update({'data': data})
    return kwargs


def session_last_index(request):
    """
    return the next free index
    """
    return len(request.session['posts']) - 1


def session_post_data(view):
    """ Return POST data if it exists for a view"""
    if view.request.method == 'GET':
        return session_get_post(view.index, view.request)
    return None


def redirect_next(index, request):
    """ Redirect to form if data exists else to next action form """
    posts = request.session['posts']
    i = index
    while i < len(posts) - 1:
        i += 1
        if not (posts[i].get('deleted', False) or posts[i].get('invalid', False)):
            break
    if i < len(posts) - 1:
        form_type = posts[i]['form_type']
        if form_type =='Name':
            return redirect('public-apply-add', index=i)
    else:
        return redirect('public-apply-next')


def build_family(request):
    """
    Return a list of name and membership for each family member
    """
    posts = request.session['posts']
    i = 0
    family = []
    while i < len(posts) - 1:
        if not posts[i].get('deleted', False):
            form_type = posts[i]['form_type']
            if form_type == "Name":
                name = posts[i]['first_name'] + " " + posts[i]['last_name']
                i += 1
                form_type =  posts[i]['form_type']
            if form_type == 'Contact':
                i += 1
                form_type = posts[i]['form_type']
            if form_type in ['Adult', 'Child']:
                membership_id = posts[i]['membership_id']
                membership = Membership.objects.get(pk=membership_id).description
                family.append([name, membership])
                i += 1
            else:
                family.append([name, "Parent or guardian"  ])
        else:
            i += 1
    return family


def build_children(request):
    """
    Return a string of comma separated child names (if any)
    """
    posts = request.session['posts']
    i = 1
    children = ""
    while i < len(posts) - 1:
        if posts[i]['form_type'] == "Name":
            name = posts[i]['first_name'] + " " + posts[i]['last_name']
            i += 1
            if posts[i]['form_type'] == "Child":
                if children != "":
                    children += ", "
                children += name
            i += 1
        else:
            i += 1
    return children


class ApplyAdult(View):
    """
    Start the application process for adult or family
    """
    def get(self, request):
        clear_session(request)
        request.session['adult'] = True
        return redirect('public-apply-main')       


class ApplyChild(View):
    """
    Start the application process for children only
    """
    def get(self, request):
        clear_session(request)
        request.session['adult'] = False
        return redirect('public-apply-main') 


class ApplyMain(TemplateView):
    """
    Get name and address of main applicant
    """
    template_name = 'public/application.html'

    def get(self, request, *args, **kwargs):
        posted = session_get_post(0, request)
        if posted:
            self.name_form = NameForm(posted,
                                      adult=request.session['adult'],
                                      restricted_fields=True
                                      )
            self.address_form = AddressForm(posted)
        else:
            self.name_form = NameForm(adult=request.session['adult'],
                                      restricted_fields=True
                                      )
            self.address_form = AddressForm()
        return render(request, self.template_name, self.get_context_data(**kwargs))

    def get_context_data(self, **kwargs):
        kwargs['name_form'] = self.name_form
        kwargs['address_form'] = self.address_form
        kwargs['form_title'] = "Adult Application Form" if self.request.session['adult'] else "Details of parent or guardian"
        kwargs['buttons'] = [Button('Next', css_class='btn-success')]
        return super(ApplyMain, self).get_context_data(**kwargs)

    def post(self, request, *args, **kwargs):
        self.name_form = NameForm(request.POST,
                                  adult=request.session['adult'],
                                  restricted_fields=True
                                  )
        self.address_form = AddressForm(request.POST)
       
        if self.name_form.is_valid() and self.address_form.is_valid():
            if not (self.name_form.cleaned_data['mobile_phone'] or self.address_form.cleaned_data['home_phone']):
                errtext = 'At least one of mobile phone or home phone must be entered'
                self.name_form.add_error('mobile_phone', errtext)
                self.address_form.add_error('home_phone', errtext)
            else:
                request.session['person'] = self.name_form.save(commit=False)
                request.session['address'] = self.address_form.save(commit=False)
                session_update_post(0, request)
                next_index = session_next_index(0, request)
                if 'dob' not in request.POST:
                    return redirect('public-apply-add', index=next_index)
                else:
                    dob = self.name_form.cleaned_data['dob']
                    membership = membership_from_dob(dob)
                    if membership.is_adult:
                        # actual adult membership will be determined in profile
                        request.session['person'].membership_id = membership.id
                        return redirect('public-apply-addadult', index=next_index, membership_id=0)
                self.name_form.add_error(None,"Please enter adult information on this form")
                self.name_form.add_error('dob', "Not an adult's date of birth")
        return render(request, self.template_name, self.get_context_data(**kwargs))


class ApplyAddView(CreateView):
    """
    Get name and dob of next family member
    Also handles deletion of member when page revisited
    """
    template_name = 'public/crispy_card.html'
    form_class = FamilyMemberForm
    model = Person
    index = -1

    def dispatch(self, request, *args, **kwargs):
        self.index = int(self.kwargs['index'])
        posted = session_get_post(self.index, request)
        if posted:
            self.initial = posted
        else:
            self.initial = {'last_name': self.request.session['person'].last_name}
        return super(ApplyAddView, self).dispatch(request, *args, **kwargs)   

    def get_form_kwargs(self):      
        kwargs = super(ApplyAddView, self).get_form_kwargs()
        kwargs['restricted_fields'] = True
        kwargs['dob_needed'] = True
        return session_update_kwargs(self, kwargs)

    def get_context_data(self, **kwargs):
        kwargs['buttons'] = [Button('Back', css_class='btn-success', no_validate=True),
                             Button('Next', css_class='btn-success')]
        if session_post_data(self):
            kwargs['buttons'].append(Button('Delete', css_class='btn-danger', no_validate=True))
        if self.index == session_last_index(self.request):
            kwargs['form_title'] = "Add family member"
        else:
            kwargs['form_title'] = "Edit family member"
        return super(ApplyAddView, self).get_context_data(**kwargs)

    def post(self, request, *args, **kwargs):
        if 'back' in request.POST:
            return redirect(session_back(self.index, request))
        if 'delete' in self.request.POST:
            session_delete_post(self.index, self.request)
            return redirect(session_back(self.index, self.request))
        return super(ApplyAddView, self).post(request, *args, **kwargs)

    def form_valid(self, form):
        session_update_post(self.index, self.request)
        dob = form.cleaned_data['dob']
        membership = membership_from_dob(dob)
        index = session_next_index(self.index, self.request)
        # if next record is a profile, invalidate it if it is the wrong type
        next_post = session_get_post(index, self.request)
        if next_post and next_post['form_type'] == 'Contact' and not membership.is_adult:
            session_invalidate_post(index, self.request)
        if membership.is_adult:
            if not self.request.session['adult']:
                form.add_error('dob', 'You can only add children to this form')
                return super(ApplyAddView, self).form_invalid(form)

            if membership.cutoff_age:
                return redirect('public-apply-contact', index=index, membership_id=membership.id)
            else:
                return redirect('public-apply-contact', index=index, membership_id=0)
        return redirect('public-apply-addchild', index=index, membership_id=membership.id)


class ApplyContactView(FormView):
    """ Get adult contact details """
    template_name = 'public/crispy_card.html'
    form_class = AdultContactForm

    def dispatch(self, request, *args, **kwargs):
        self.index = int(self.kwargs['index'])
        self.membership_id = int(self.kwargs['membership_id'])
        self.full_name = session_last_fullname(self.index, request)
        posted = session_get_post(self.index, request)
        if posted:
            self.initial = posted
        return super(ApplyContactView, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):

        kwargs['form_title'] = "Contact details: " + self.full_name
        kwargs['buttons'] = [Button('Back', css_class='btn-success'),
                             Button('Next', css_class='btn-success')]
        return super(ApplyContactView, self).get_context_data(**kwargs)

    def post(self, request, *args, **kwargs):
        if 'back' in request.POST:
            return redirect(session_back(self.index, request))
        return super(ApplyContactView, self).post(request, *args, **kwargs)

    def form_valid(self, form):
        session_update_post(self.index, self.request)
        index = session_next_index(self.index, self.request)
        return redirect('public-apply-addadult', index, self.kwargs['membership_id'])


class ApplyAdultProfileView(CreateView):
    """
    Get adult membership type and profile
    """
    template_name = 'public/crispy_card.html'
    form_class = AdultProfileForm
    
    def dispatch(self, request, *args, **kwargs):
        self.index = int(self.kwargs['index'])
        self.membership_id = int(self.kwargs['membership_id'])
        self.full_name = session_last_fullname(self.index, request)
        posted = session_get_post(self.index, request)
        if posted:
            self.initial = posted
        return super(ApplyAdultProfileView, self).dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super(ApplyAdultProfileView, self).get_form_kwargs()
        kwargs['choices'] = Membership.adult_choices(self.membership_id)
        return session_update_kwargs(self, kwargs)

    def get_context_data(self, **kwargs):
        kwargs['form_title'] = "Adult profile: " + self.full_name
        kwargs['memberships'] = Membership.adult_choices(self.membership_id, description=True)
        kwargs['buttons'] = [Button('Back', css_class='btn-success'),
                             Button('Next', css_class='btn-success')]
        return super(ApplyAdultProfileView, self).get_context_data(**kwargs)

    def post(self, request, *args, **kwargs):
        if 'back' in request.POST:
            return redirect(session_back(self.index, request))
        return super(ApplyAdultProfileView, self).post(request, *args, **kwargs)

    def form_valid(self, form):
        membership = Membership.objects.get(pk=form.cleaned_data['membership_id']).description
        session_update_post(self.index, self.request)
        return redirect_next(self.index, self.request)


class ApplyChildProfileView(FormView):
    """
    Get child notes
    """
    template_name = 'public/crispy_card.html'
    form_class = ChildProfileForm
   
    def dispatch(self, request, *args, **kwargs):
        self.index = int(self.kwargs['index'])
        self.full_name = session_last_fullname(self.index, request)
        posted = session_get_post(self.index, request)
        if posted:
            self.initial = posted
        else:
            self.initial = {'membership_id': self.kwargs['membership_id']}
        return super(ApplyChildProfileView, self).dispatch(request, *args, **kwargs) 

    def get_form_kwargs(self):      
        kwargs = super(ApplyChildProfileView, self).get_form_kwargs()
        return session_update_kwargs(self, kwargs)

    def get_context_data(self, **kwargs):
        membership = Membership.objects.get(pk=self.kwargs['membership_id']).description
        kwargs['form_title'] = membership + ": " + self.full_name
        kwargs['buttons'] = [Button('Back', css_class='btn-success'),
                             Button('Next', css_class='btn-success')]
        return super(ApplyChildProfileView, self).get_context_data(**kwargs)

    def post(self, request, *args, **kwargs):
        if 'back' in request.POST:
            return redirect(session_back(self.index, request))
        return super(ApplyChildProfileView, self).post(request, *args, **kwargs)

    def form_valid(self, form):
        session_update_post(self.index, self.request)
        return redirect_next(self.index, self.request)
    

class ApplyNextActionView(FormView):
    """
    Decide to Add another member or submit
    """
    template_name = 'public/crispy_card.html'
    form_class = ApplyNextActionForm

    def get_context_data(self, **kwargs):
        kwargs['form_title'] = "Applicants"
        kwargs['family'] = build_family(self.request)
        kwargs['buttons'] = [Button("Back", "back"),
                             Button("Add family member", "add"),
                             Button("Complete application", "submit")]
        return super(ApplyNextActionView, self).get_context_data(**kwargs)

    def post(self, request, *args, **kwargs):
        index = session_last_index(request) + 1
        if 'back' in request.POST:
            return redirect(session_back(index, request))
        if 'submit' in request.POST:
            return redirect('public-apply-submit')
        return redirect('public-apply-add', index)
    

class ApplySubmitView(TemplateView):
    """
    Confirm everything and get acceptance
    Add all to database
    """
    template_name = 'public/submit_application.html'

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name, self.get_context_data(**kwargs))

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        if 'back' in request.POST:
            return redirect(session_back(0, request))

#       if not request.POST.get['rules', None]:
        try:
            person = self.request.session['person']
            address = self.request.session['address']
            address.save()
            person.address = address
            person.state = Person.APPLIED
            person.date_joined = datetime.today()
            person.save()
        
            posts = self.request.session['posts']
            i = 1
            if self.request.session['adult']:
                profile_form = AdultProfileForm(posts[i])
                if profile_form.is_valid():
                    profile = profile_form.save()
                    person.membership_id = profile.membership_id
                    profile.person = person
                    person.save()
                    profile.save()
                    i += 1
            else:
                person.membership_id = None
                person.save()
            # process family members
            while i < len(posts) - 1:
                if not posts[i].get('deleted', False):
                    kid_form = FamilyMemberForm(posts[i]) 
                    if kid_form.is_valid():
                        kid = kid_form.save(commit=False)
                        kid.linked = person
                        kid.address = address
                        kid.state = Person.APPLIED
                        kid.date_joined = person.date_joined
                        kid.save()
                        i += 1
                        if posts[i]['form_type'][0] == "Adult":
                            contact_form = ContactForm(posts[i])
                            kid.email = contact_form.email
                            kid.mobile_phone = contact_form.mobile_phone
                            kid.save()
                            i += 1
                            profile_form = AdultProfileForm(posts[i])
                            if profile_form.is_valid():
                                profile = profile_form.save()
                                kid.membership_id = profile.membership+id
                                profile.person = kid
                                kid.save()
                                profile.save()
                            else:
                                raise ValueError("Invalid adult profile form")
                        else:
                            profile_form = ChildProfileForm(posts[i])
                            if profile_form.is_valid():
                                kid.membership_id = profile_form.cleaned_data['membership_id']
                                kid.notes = profile_form.cleaned_data['notes']
                                kid.save()
                            else:
                                raise ValueError("Invalid child profile form")
                        i += 1
                    else:
                        raise ValueError("Invalid family member form")
                else:
                    i += 1
            clear_session(self.request)
            from_mail = getattr(settings, "INFO_EMAIL", None)
            admins = getattr(settings, "ADMINS", None)
            if admins:
                to_list = []
                for admin in admins:
                    to_list.append(admin[1])
                send_mail("New application received",
                          "Someone has applied to join the club.",
                          from_mail,
                          to_list,
                          )
            return redirect('public-apply-thankyou')

        except ValueError as error:
            message = "Sorry, an error occurred while processing the form."
            logger.error((message + "{0}").format(error))
            return HttpResponse(message)
            
    def get_context_data(self, **kwargs):
        kwargs['family'] = build_family(self.request)
        kwargs['children'] = build_children(self.request)
        kwargs['adult'] = self.request.session['adult']
        return super(ApplySubmitView, self).get_context_data(**kwargs)


class ApplyThankYouView(TemplateView):
    template_name = 'public/apply_thankyou.html'


class PrivacyPolicyView(TemplateView):
    template_name = 'public/privacy_policy.html'


class AdultProfileView(UpdateView):
    template_name = 'public/crispy_form.html'
    form_class = AdultProfileForm

    def get_form_kwargs(self):
        kwargs = super(AdultProfileView, self).get_form_kwargs()
        kwargs['buttons'] = False
        return kwargs


    def get_object(self, queryset=None):
        return AdultApplication.objects.get(person_id=self.kwargs['pk'])

    def get_context_data(self, **kwargs):
        kwargs['title'] = "Adult profile"
        kwargs['buttons'] = False
        return super(AdultProfileView, self).get_context_data(**kwargs)