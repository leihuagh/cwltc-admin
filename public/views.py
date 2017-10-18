from datetime import datetime
from django.shortcuts import render, render_to_response, redirect
from django.views.generic import DetailView, TemplateView, CreateView, View
from django.core.signing import Signer
from django.core.mail import send_mail
from django.core.urlresolvers import reverse
from django.contrib import messages
from django.http import HttpResponse
from django.views.generic.edit import FormView

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
        signer = Signer()
        try:
            invoice_id = signer.unsign(self.kwargs['token'])
            self.invoice = Invoice.objects.get(pk = invoice_id)
        except Invoice.DoesNotExist:
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
            mandate = invoice.person.mandates.all()[0]
            if mandate == None:
                return redirect('cardless_mandate_create', kwargs['token'])
            else:
                return redirect('cardless_payment_create', kwargs['token'] )

        if 'query' in request.POST:
            group = group_get_or_create("2017Query")
            invoice.person.groups.add(group)
            return redirect(reverse('public-contact-person', kwargs={'person_id': invoice.person.id}))
        elif 'resign' in request.POST:
            group = group_get_or_create("2017Resign")
            invoice.person.groups.add(group)
            return redirect(reverse('public-resigned'))


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
    """
    Register a member identified in a token
    Creates a link from Person to User in auth system
    """
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
            return posts[index]
    return None


def session_delete_post(index, request):
    """
    Delete post data for index
    If it is not the last one in the list,
    delete the next record (profile) too
    """
    posts = request.session['posts']
    if index < len(posts):
        posts[index]['deleted'] = True
        if index + 1< len(posts):
            posts[index + 1]['deleted'] = True
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
    if view.request.method == 'GET':
        post = session_get_post(view.index, view.request)
        if post:
            kwargs.update({'data': post})
            kwargs.update({'delete': True})
    return kwargs


def session_last_index(request):
    """
    return the next free index
    """
    return len(request.session['posts']) - 1


def build_family(request):
    """
    Return a list of name and membership for each family member
    """
    posts = request.session['posts']
    i = 0
    family = []
    while i < len(posts) - 1:
        if not posts[i].get('deleted', False):
            if posts[i]['form_type'] == "Name":
                name = posts[i]['first_name'] + " " + posts[i]['last_name']
                i += 1
                if posts[i]['form_type'] != "Name":
                    membership_id = posts[i]['membership_id']
                    membership = Membership.objects.get(pk=membership_id).description
                    i += 1
                else:
                    membership = "Parent or guardian"   
                family.append([name, membership])
            else:
                i += 1
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

                if 'dob' not in request.POST:
                    return redirect('public-apply-add', index=1)
                else:
                    dob = self.name_form.cleaned_data['dob']
                    membership = membership_from_dob(dob)
                    if membership.is_adult:
                        # actual adult membership will be determined in profile
                        request.session['person'].membership_id = membership.id
                        return redirect('public-apply-addadult', index=1, membership_id = 0)
                self.name_form.add_error(None,"Please enter adult information on this form")
                self.name_form.add_error('dob', "Not an adult's date of birth")
        return render(request, self.template_name, self.get_context_data(**kwargs))

    def get_context_data(self, **kwargs):  
        kwargs['name_form'] = self.name_form
        kwargs['address_form'] = self.address_form     
        kwargs['form_title'] = "Adult Application Form" if self.request.session['adult'] else "Details of parent or guardian"
        return super(ApplyMain, self).get_context_data(**kwargs)


class ApplyAddView(CreateView):
    """
    Get name and dob of next family member
    Also handles deletion of member when page revisited
    """
    template_name = 'public/application.html'
    form_class = FamilyMemberForm
    model = Person
    index = -1

    def dispatch(self, request, *args, **kwargs):
        self.index = int(self.kwargs['index'])
        return super(ApplyAddView, self).dispatch(request, *args, **kwargs)   

    def get_form_kwargs(self):      
        kwargs = super(ApplyAddView, self).get_form_kwargs()
        kwargs['initial']={'last_name': self.request.session['person'].last_name}
        return session_update_kwargs(self, kwargs)

    def post(self, request, *args, **kwargs):
        if 'back' in request.POST:
            return redirect(session_back(self.index, request))
        return super(ApplyAddView, self).post(request, *args, **kwargs)

    def form_valid(self, form):
        if 'delete' in self.request.POST:
            session_delete_post(self.index, self.request)
            return redirect(session_back(self.index, self.request))
        else:
            session_update_post(self.index, self.request)
            dob = form.cleaned_data['dob']
            membership = membership_from_dob(dob)
            index = session_next_index(self.index, self.request)
            if membership.is_adult:
                if not self.request.session['adult']:
                    form.add_error('dob', 'You can only add children to this form')
                    return render(self.request, self.template_name, self.get_context_data())
            
                if membership.cutoff_age:
                    return redirect('public-apply-addadult', index=index, membership_id=membership.id)
                else:
                    return redirect('public-apply-addadult', index=index, membership_id=0)
            return redirect('public-apply-addchild', index=index, membership_id=membership.id)  

    def get_context_data(self, **kwargs):
        if self.index == session_last_index(self.request):
            kwargs['form_title'] = "Add family member"
        else:
            kwargs['form_title'] = "Family member"
        return super(ApplyAddView, self).get_context_data(**kwargs)


class ApplyAdultProfileView(CreateView):
    """
    Get adult membership type and profile
    """
    template_name = 'public/application.html'
    form_class = AdultProfileForm
    
    def dispatch(self, request, *args, **kwargs):
        self.index = int(self.kwargs['index'])
        self.membership_id = int(self.kwargs['membership_id'])
        last_post = session_get_post(self.index - 1, self.request)
        self.full_name = last_post['first_name'] + " " + last_post['last_name']
        return super(ApplyAdultProfileView, self).dispatch(request, *args, **kwargs)
    
    def get_form_kwargs(self):      
        kwargs = super(ApplyAdultProfileView, self).get_form_kwargs()
        kwargs['choices'] = Membership.adult_choices(self.membership_id)
        return session_update_kwargs(self, kwargs)

    def post(self, request, *args, **kwargs):
        if 'back' in request.POST:
            return redirect(session_back(self.index, request))
        return super(ApplyAdultProfileView, self).post(request, *args, **kwargs)

    def form_valid(self, form):
        membership = Membership.objects.get(pk=form.cleaned_data['membership_id']).description
        session_update_post(self.index, self.request)
        return redirect('public-apply-next')

    def get_context_data(self, **kwargs):          
        #kwargs['family'] = build_family(self.request)
        kwargs['name'] = self.full_name
        kwargs['form_title'] = "Adult profile"
        kwargs['memberships'] = Membership.adult_choices(self.membership_id, description=True)
        return super(ApplyAdultProfileView, self).get_context_data(**kwargs)


class ApplyChildProfileView(FormView):
    """
    Get child notes
    """
    template_name = 'public/application.html'
    form_class = ChildProfileForm
   
    def dispatch(self, request, *args, **kwargs):
        self.index = int(self.kwargs['index'])
        last_post = session_get_post(self.index - 1, self.request)
        self.full_name = last_post['first_name'] + " " + last_post['last_name']
        return super(ApplyChildProfileView, self).dispatch(request, *args, **kwargs) 

    def get_form_kwargs(self):      
        kwargs = super(ApplyChildProfileView, self).get_form_kwargs()
        kwargs['initial'] = {'membership_id': self.kwargs['membership_id']}
        return session_update_kwargs(self, kwargs)

    #def get(self, request, *args, **kwargs):
    #    last_post = session_get_post(self.index - 1, self.request)
    #    if last_post:
    #        if last_post.get('first_name', None):
    #            self.full_name = last_post['first_name'] + " " + last_post['last_name']
    #            return super(ApplyChildProfileView, self).get(request, *args, **kwargs)
    #    return HttpResponse("This form is no longer valid")
    
    def post(self, request, *args, **kwargs):
        if 'back' in request.POST:
            return redirect(session_back(self.index, request))
        return super(ApplyChildProfileView, self).post(request, *args, **kwargs)

    def form_valid(self, form):
        session_update_post(self.index, self.request)
        return redirect('public-apply-next')
    
    def get_context_data(self, **kwargs):
        membership = Membership.objects.get(pk=self.kwargs['membership_id']).description
        kwargs['form_title'] = membership + ":"
        kwargs['name'] = self.full_name
        return super(ApplyChildProfileView, self).get_context_data(**kwargs)


class ApplyNextActionView(FormView):
    """
    Decide to Add another member or submit
    """
    template_name = 'public/application.html'
    form_class = ApplyNextActionForm

    def post(self, request, *args, **kwargs):
        index = session_last_index(request) + 1
        if 'back' in request.POST:
            return redirect(session_back(index, request))
        if 'submit' in request.POST:
            return redirect('public-apply-submit')
        return redirect('public-apply-add', index)
    
    def get_context_data(self, **kwargs):
        kwargs['family'] = build_family(self.request)
        return super(ApplyNextActionView, self).get_context_data(**kwargs)


class ApplySubmitView(TemplateView):
    """
    Confirm everything and get acceptance
    Add all to database
    """
    template_name = 'public/submit_application.html'

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name, self.get_context_data(**kwargs))

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
            return redirect('public-apply-thankyou')

        except ValueError as error:
            return HttpResponse("Sorry, an error occurred " + error)
            
    def get_context_data(self, **kwargs):
        kwargs['family'] = build_family(self.request)
        kwargs['children'] = build_children(self.request)
        kwargs['adult'] = self.request.session['adult']
        return super(ApplySubmitView, self).get_context_data(**kwargs)


class ApplyThankYouView(TemplateView):
    template_name = 'public/apply_thankyou.html'


class PrivacyPolicyView(TemplateView):
    template_name = 'public/privacy_policy.html'
