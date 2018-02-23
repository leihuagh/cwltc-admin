import logging
from datetime import datetime
from django.shortcuts import render, redirect
from django.views.generic import TemplateView, CreateView, View, UpdateView
from django.core.mail import send_mail
from django.conf import settings
from django.core.urlresolvers import reverse
from django.http import HttpResponse
from django.views.generic.edit import FormView
from django.db import transaction
from mysite.common import Button
from members.models import Person, AdultApplication, Membership
from members.services import membership_from_dob
from public.forms import (NameForm, AddressForm, AdultProfileForm, ChildProfileForm, FamilyMemberForm,
                          ApplyNextActionForm, AdultContactForm, CampFindRecordForm)
from public.session_management import *

logger = logging.getLogger(__name__)


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
            self.name_form = NameForm(posted, adult=request.session['adult'])
            self.address_form = AddressForm(posted)
        else:
            self.name_form = NameForm(adult=request.session['adult'])
            self.address_form = AddressForm()
        return render(request, self.template_name, self.get_context_data(**kwargs))

    def get_context_data(self, **kwargs):
        kwargs['name_form'] = self.name_form
        kwargs['address_form'] = self.address_form
        kwargs['form_title'] = "Adult Application Form" if self.request.session['adult'] else\
            "Details of parent or guardian"
        kwargs['buttons'] = [Button('Next', css_class='btn-success')]
        return super(ApplyMain, self).get_context_data(**kwargs)

    def post(self, request, *args, **kwargs):
        self.name_form = NameForm(request.POST, adult=request.session['adult'])
        self.address_form = AddressForm(request.POST)
       
        if self.name_form.is_valid() and self.address_form.is_valid():
            if not (self.name_form.cleaned_data['mobile_phone'] or self.address_form.cleaned_data['home_phone']):
                err_text = 'At least one of mobile phone or home phone must be entered'
                self.name_form.add_error('mobile_phone', err_text)
                self.address_form.add_error('home_phone', err_text)
            else:
                request.session['person'] = self.name_form.save(commit=False)
                request.session['address'] = self.address_form.save(commit=False)
                # update POST data with cleaned data before we save it
                # so it is visible if we go back and when we eventually save
                request.POST._mutable = True
                request.POST['mobile_phone'] = self.name_form.cleaned_data['mobile_phone']
                request.POST['home_phone'] = self.address_form.cleaned_data['home_phone']
                request.POST['post_code'] = self.address_form.cleaned_data['post_code']
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
                        return redirect('public-apply-adult-profile', index=next_index, membership_id=0)
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
        return redirect('public-apply-child-profile', index=index, membership_id=membership.id)


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
        return redirect('public-apply-adult-profile', index, self.kwargs['membership_id'])


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
        index = session_last_index(request) + 1
        if 'back' in request.POST:
            return redirect(session_back(index, request))

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
                    kid_form.full_clean()
                    if kid_form.is_valid():
                        kid = kid_form.save(commit=False)
                        kid.linked = person
                        kid.address = address
                        kid.state = Person.APPLIED
                        kid.date_joined = person.date_joined
                        kid.save()
                        i += 1
                        if posts[i]['form_type'][0] == "Adult":
                            contact_form = AdultContactForm(posts[i])
                            kid.email = contact_form.email
                            kid.mobile_phone = contact_form.mobile_phone
                            kid.save()
                            i += 1
                            profile_form = AdultProfileForm(posts[i])
                            if profile_form.is_valid():
                                profile = profile_form.save()
                                kid.membership_id = profile.membership_id
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
            return redirect('public-apply-thank-you')

        except ValueError as error:
            message = ("Sorry, an error occurred while processing the form. {0}").format(error)
            logger.error(message)
            return HttpResponse(message)
            
    def get_context_data(self, **kwargs):
        kwargs['family'] = build_family(self.request)
        kwargs['children'] = build_children(self.request)
        kwargs['adult'] = self.request.session['adult']
        return super(ApplySubmitView, self).get_context_data(**kwargs)


class ApplyThankYouView(TemplateView):
    template_name = 'public/apply_thank-you.html'


class PrivacyPolicyView(TemplateView):
    template_name = 'public/privacy_policy.html'


class AdultProfileView(UpdateView):
    template_name = 'public/crispy_card.html'
    form_class = AdultProfileForm
    edit = False

    def get_form_kwargs(self):
        kwargs = super(AdultProfileView, self).get_form_kwargs()
        kwargs['disabled'] = not self.edit
        return kwargs

    def get_object(self, queryset=None):
        return AdultApplication.objects.get(person_id=self.kwargs['pk'])

    def get_context_data(self, **kwargs):
        person = Person.objects.get(pk=self.kwargs['pk'])
        kwargs['form_title'] = "Adult profile for " + person.fullname
        if not self.edit:
            kwargs['buttons'] = [Button("Edit", "edit")]
        else:
            kwargs['buttons'] = [Button("Save", "save")]
        return super(AdultProfileView, self).get_context_data(**kwargs)

    def post(self, request, *args, **kwargs):
        if 'edit' in request.POST:
            return redirect('person-profile-edit', pk=self.kwargs['pk'])
        return super(AdultProfileView, self).post(request, *args, *kwargs)

    def get_success_url(self):
        return reverse('person-detail', kwargs={'pk': self.kwargs['pk']})


class CampHomeView(TemplateView):
    template_name='public/camp_home.html'


class CampRegisterView(FormView):
    template_name='public/camp_register.html'
    form_class = CampFindRecordForm

class CampRegisterNewView(TemplateView):
    template_name = 'public/crispy_card.html'
    form_class = CampFindRecordForm


class CampRegisterOldView(FormView):
    template_name='public/camp_register_old.html'

