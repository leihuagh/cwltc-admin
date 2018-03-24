import logging
from datetime import datetime
from django.shortcuts import render, redirect
from django.views.generic import TemplateView, CreateView, View, UpdateView
from django.core.mail import send_mail
from django.conf import settings
from django.core.urlresolvers import reverse
from django.http import HttpResponse, Http404
from django.views.generic.edit import FormView
from django.db import transaction
from mysite.common import Button
from members.models import Person, AdultApplication, JuniorProfile, Membership, Settings, Fees
from members.services import membership_from_dob
from public.forms import (NameForm, AddressForm, AdultMembershipForm, AdultProfileForm, JuniorProfileForm, FamilyMemberForm,
                          ApplyNextActionForm, AdultContactForm, ApplySubmitForm, CampFindRecordForm)
import public.session as session

logger = logging.getLogger(__name__)


class ApplyAdult(View):
    """
    Start the application process for adult or family
    """
    def get(self, request):
        session.start_adult_application(request)
        return redirect('public-apply-main')


class ApplyChild(View):
    """
    Start the application process for children only
    """
    def get(self, request):
        session.start_child_application(request)
        return redirect('public-apply-main')


class ApplyNonMember(View):
    """
    Start the application process for non member
    """
    def get(self, request):
        session.start_non_member_application(request)
        return redirect('public-apply-main')


class ApplyMain(TemplateView):
    """
    Get name and address of main applicant
    """
    template_name = 'public/application.html'

    def get(self, request, *args, **kwargs):
        if not session.exists(request):
            raise Http404
        posted = session.get_data(0, request)
        if posted:
            self.name_form = NameForm(posted, adult=session.is_adult_application(request))
            self.address_form = AddressForm(posted)
        else:
            self.name_form = NameForm(adult=session.is_adult_application(request))
            self.address_form = AddressForm()
        return render(request, self.template_name, self.get_context_data(**kwargs))

    def get_context_data(self, **kwargs):
        kwargs['name_form'] = self.name_form
        kwargs['address_form'] = self.address_form
        kwargs['form_title'] = "Adult Application Form" if session.is_adult_application(self.request) else\
            "Details of parent or guardian"
        kwargs['buttons'] = [Button('Next', css_class='btn-success')]
        return super(ApplyMain, self).get_context_data(**kwargs)

    def post(self, request, *args, **kwargs):
        self.name_form = NameForm(request.POST, adult=session.is_adult_application(request))
        self.address_form = AddressForm(request.POST)
       
        if self.name_form.is_valid() and self.address_form.is_valid():
            if not (self.name_form.cleaned_data['mobile_phone'] or self.address_form.cleaned_data['home_phone']):
                err_text = 'At least one of mobile phone or home phone must be entered'
                self.name_form.add_error('mobile_phone', err_text)
                self.address_form.add_error('home_phone', err_text)
            else:
                request.session['person'] = self.name_form.save(commit=False)
                request.session['address'] = self.address_form.save(commit=False)
                session.update_data(0, request, self.name_form, self.address_form)
                next_index = session.next_index(0, request)
                if not session.is_adult_application(request):
                    return redirect('public-apply-add', index=next_index)
                else:
                    membership = membership_from_dob(self.name_form.cleaned_data['dob'])
                    if membership.is_adult:
                        # if membership.cutoff_age:
                        #     request.session['person'].membership_id = membership.id
                        #     return redirect('public-apply-adult-profile', index=next_index, membership_id=0)
                        # else:
                        # actual adult membership will be determined in profile
                        request.session['person'].membership_id = membership.id
                        return redirect('public-apply-membership', index=next_index, membership_id=membership.id)
                self.name_form.add_error(None,"Please enter adult information on this form")
                self.name_form.add_error('dob', "Not an adult's date of birth")
        return render(request, self.template_name, self.get_context_data(**kwargs))


class DispatchMixin():
    """ Mixin to add session variables to class """

    def dispatch(self, request, *args, **kwargs):
        if not session.exists(request):
            raise Http404
        self.membership_id = int(kwargs.get('membership_id', 0))
        self.index = int(kwargs['index'])
        self.full_name = session.last_fullname(self.index, request)
        posted = session.get_data(self.index, request)
        if posted:
            self.initial = posted
        else:
            self.initial = {'last_name': request.session['person'].last_name,
                            'membership_id': self.membership_id}
        return super(DispatchMixin, self).dispatch(request, *args, **kwargs)


class ApplyAdultMembershipView(DispatchMixin, FormView):
    """ Select adult membership category"""
    template_name = 'public/adult_membership.html'
    form_class = AdultMembershipForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        self.membership = Membership.objects.get(pk=self.membership_id)
        if self.membership.cutoff_age:
            kwargs['initial'].update({'membership_id': self.membership_id})
            kwargs['choices'] = Membership.adult_choices(self.membership.id)
        else:
            kwargs['choices'] = Membership.adult_choices()
        return session.update_kwargs(self, kwargs)

    def get_context_data(self, **kwargs):
        self.membership = Membership.objects.get(pk=self.membership_id)
        if self.membership.cutoff_age:
            kwargs['form_title'] = f'{self.full_name}: {self.membership.description} membership'
            kwargs['memberships'] = Membership.adult_choices(membership_id=self.membership.id, description=True)
        else:
            kwargs['form_title'] = f'Select adult membership for {self.full_name}'
            kwargs['memberships'] = Membership.adult_choices(description=True)
        kwargs['buttons'] = [Button('Back', css_class='btn-success'),
                             Button('Next', css_class='btn-success')]
        return super().get_context_data(**kwargs)

    def post(self, request, *args, **kwargs):
        if 'back' in request.POST:
            return redirect(session.back(self.index, request))
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        if not 'membership_id' in self.request.POST:
            form.cleaned_data['membership_id'] = self.membership_id
        session.update_data(self.index, self.request, form)
        index = session.next_index(self.index, self.request)
        return redirect('public-apply-adult-profile', index, self.kwargs['membership_id'])


class ApplyAddView(DispatchMixin, CreateView):
    """
    Get name and dob of next family member
    Also handles deletion of member when page revisited
    """
    template_name = 'public/crispy_card.html'
    form_class = FamilyMemberForm
    model = Person
    index = -1

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['dob_needed'] = True
        return session.update_kwargs(self, kwargs)


    def get_context_data(self, **kwargs):
        kwargs['buttons'] = [Button('Back', css_class='btn-success', no_validate=True),
                             Button('Next', css_class='btn-success')]
        if session.post_data(self):
            kwargs['buttons'].append(Button('Delete', css_class='btn-danger', no_validate=True))
        action_text = ' to applicants'
        if session.is_adult_application(self.request):
            title = 'family member'
        else:
            title = 'child'
            if session.is_non_member_application(self.request):
                action_text = ' attending camp'
        if self.index > session.last_index(self.request):
            kwargs['form_title'] = "Add " + title + action_text
        else:
            kwargs['form_title'] = "Edit " + title + ' details'
        return super().get_context_data(**kwargs)

    def post(self, request, *args, **kwargs):
        if 'back' in request.POST:
            return redirect(session.back(self.index, request))
        if 'delete' in self.request.POST:
            session.delete_data(self.index, self.request)
            return redirect(session.back(self.index, self.request))
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        session.update_data(self.index, self.request, form)
        dob = form.cleaned_data['dob']
        membership = membership_from_dob(dob)
        index = session.next_index(self.index, self.request)

        # if next record is a profile, invalidate it if it is the wrong type
        next_post = session.get_data(index, self.request)
        if next_post:
            if (session.is_junior_profile(next_post) and membership.is_adult) or \
                    (session.is_membership_form(next_post) and not membership.is_adult):
                session.invalidate_data(index, self.request)

        if membership.is_adult:
            if not session.is_adult_application(self.request):
                form.add_error('dob', 'You can only add children to this form')
                return super().form_invalid(form)

            return redirect('public-apply-contact', index=index, membership_id=membership.id)
        return redirect('public-apply-child-profile', index=index, membership_id=membership.id)


class ApplyAdultContactView(ApplyAdultMembershipView):
    """ Get adult contact details """

    form_class = AdultContactForm


class ApplyAdultProfileView(DispatchMixin, CreateView):
    """
    Get adult membership type and profile
    """
    template_name = 'public/crispy_card.html'
    form_class = AdultProfileForm

    # def get_form_kwargs(self):
    #     kwargs = super().get_form_kwargs()
    #     kwargs['choices'] = Membership.adult_choices(self.membership_id)
    #     return session.update_kwargs(self, kwargs)

    def get_context_data(self, **kwargs):
        kwargs['form_title'] = "Adult profile: " + self.full_name
        kwargs['memberships'] = Membership.adult_choices(self.membership_id, description=True)
        kwargs['buttons'] = [Button('Back', css_class='btn-success'),
                             Button('Next', css_class='btn-success')]
        return super().get_context_data(**kwargs)

    def post(self, request, *args, **kwargs):
        if 'back' in request.POST:
            return redirect(session.back(self.index, request))
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        session.update_data(self.index, self.request, form)
        return session.redirect_next(self.index, self.request)


class ApplyJuniorProfileView(DispatchMixin, FormView):
    """
    Get junior profile
    """
    template_name = 'public/junior_profile.html'
    form_class = JuniorProfileForm
   
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        return session.update_kwargs(self, kwargs)

    def get_initial(self):
        self.initial = super().get_initial()
        profile = session.first_child_profile(self.index, self.request)
        if profile:
            self.initial.update({'contact0': profile['contact0'],
                                 'phone0': profile['phone0'],
                                 'relationship0': profile['relationship0'],
                                 'contact1': profile['contact1'],
                                 'phone1': profile['phone1'],
                                 'relationship1': profile['relationship1'],
                                 'contact2': profile['contact2'],
                                 'phone2': profile['phone2'],
                                 'relationship2': profile['relationship2']
                                 })
        else:
            contact = self.request.session['person']
            if contact.mobile_phone:
                phone = contact.mobile_phone
            else:
                phone = self.request.session['address'].home_phone
            self.initial.update({'contact0': contact.fullname,
                                 'phone0': phone,
                                 'relationship0': ''
                                })
        return self.initial


    def get_context_data(self, **kwargs):
        mem_id = self.kwargs['membership_id']
        membership = Membership.objects.get(pk=mem_id)
        fee = Fees.objects.filter(membership_id=mem_id, sub_year=Settings.current_year())[0]
        kwargs['form_title'] ="Profile for " + self.full_name
        kwargs['membership'] = membership
        kwargs['sub'] = fee.annual_sub
        kwargs['year'] = fee.sub_year
        kwargs['end_year'] = int(fee.sub_year) + 1
        kwargs['buttons'] = [Button('Back', css_class='btn-success'),
                             Button('Next', css_class='btn-success')]
        return super().get_context_data(**kwargs)

    def post(self, request, *args, **kwargs):
        if 'back' in request.POST:
            return redirect(session.back(self.index, request))
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        session.update_data(self.index, self.request, form)
        return session.redirect_next(self.index, self.request)

    def form_invalid(self, form):
        result = super().form_invalid(form)
        return result


class ApplyNextActionView(FormView):
    """
    Decide to Add another member or submit
    """
    template_name = 'public/crispy_card.html'
    form_class = ApplyNextActionForm

    def get_context_data(self, **kwargs):
        if session.exists(self.request):
            kwargs['form_title'] = "Applicants"
            kwargs['family'] = session.get_family(self.request)
            kwargs['buttons'] = [Button("Back", "back"),
                                 Button("Add family member", "add"),
                                 Button("Complete application", "submit")]
        else:
            kwargs['form_title'] = "Invalid application"
        return super().get_context_data(**kwargs)

    def post(self, request, *args, **kwargs):
        index = session.last_index(request) + 1
        if 'back' in request.POST:
            return redirect(session.back(index, request))
        if 'submit' in request.POST:
            return redirect('public-apply-submit')
        return redirect('public-apply-add', index)
    

class ApplySubmitView(FormView):
    """
    Confirm everything and get acceptance
    Add all to database
    """
    template_name = 'public/submit_application.html'
    form_class = ApplySubmitForm


    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({'children': session.get_children(self.request)})
        return kwargs

    def get_context_data(self, **kwargs):
        kwargs['membership'] = session.is_adult_application(self.request) or session.is_child_application(self.request)
        kwargs['family'] = session.get_family(self.request)
        kwargs['children'] = session.get_children(self.request)
        kwargs['adult'] = session.is_adult_application(self.request)
        return super().get_context_data(**kwargs)

    def get(self, request, *args, **kwargs):
        if session.exists(request):
            return render(request, self.template_name, self.get_context_data(**kwargs))
        return HttpResponse("Your application form has been processed and cannot be resubmitted")

    def post(self, request, *args, **kwargs):
        if not session.exists(request):
            return Http404
        index = session.last_index(request) + 1
        if 'back' in request.POST:
            return redirect(session.back(index, request))
        return super().post(self, request, *args, **kwargs)

    @transaction.atomic
    def form_valid(self, form):
        try:
            person = self.request.session['person']
            address = self.request.session['address']
            address.save()
            person.address = address
            person.state = Person.APPLIED
            person.date_joined = datetime.today()
            person.allow_marketing = self.request.POST['marketing'] == 'yes'
            person.consent_date = datetime.today()
            person.save()
        
            posts = self.request.session['posts']
            i = 1
            if session.is_adult_application(self.request):
                person.membership_id = posts[i]['membership_id']
                person.allow_phone = posts[i]['database'] == 'yes'
                person.allow_email = posts[i]['database'] == 'yes'
                i += 1
                profile_form = AdultProfileForm(posts[i])
                if profile_form.is_valid():
                    profile = profile_form.save()
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
                    fam_form = FamilyMemberForm(posts[i])
                    if not fam_form.is_valid():
                        raise ValueError("Invalid family member form")
                    fam_member = fam_form.save(commit=False)
                    fam_member.linked = person
                    fam_member.address = address
                    fam_member.state = Person.APPLIED
                    fam_member.date_joined = person.date_joined
                    fam_member.save()
                    i += 1
                    child = False
                    if posts[i]['form_class'] == AdultContactForm.__name__:
                        fam_member.membership_id = posts[i]['membership_id']
                        fam_member.email = posts[i]['email']
                        fam_member.mobile_phone = posts[i]['mobile_phone']
                        fam_member.save()
                        i += 1
                        profile_form = AdultProfileForm(posts[i])
                    else:
                        profile_form = JuniorProfileForm(posts[i])
                        child = True
                    if not profile_form.is_valid():
                        raise ValueError("Invalid profile form")
                    profile = profile_form.save(commit=False)
                    if child:
                        profile.has_needs = profile_form.cleaned_data['rad_has_needs'] == '2'
                        profile.photo_consent = profile_form.cleaned_data['photo'] == 'yes'
                        fam_member.membership_id = profile_form.cleaned_data['membership_id']
                        fam_member.save()
                    profile.person = fam_member
                    profile.save()
                i += 1
            session.clear(self.request)
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


class ApplyThankYouView(TemplateView):
    template_name = 'public/apply_thanks.html'


class PrivacyPolicyView(TemplateView):
    template_name = 'public/privacy_policy.html'


class AdultProfileView(UpdateView):
    template_name = 'public/crispy_card.html'
    form_class = AdultProfileForm
    edit = False

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
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
        return super().get_context_data(**kwargs)

    def post(self, request, *args, **kwargs):
        if 'edit' in request.POST:
            self.edit = True
            return redirect('person-profile-edit', pk=self.kwargs['pk'])
        return super().post(request, *args, *kwargs)

    def get_success_url(self):
        return reverse('person-detail', kwargs={'pk': self.kwargs['pk']})


class JuniorProfileView(UpdateView):
    template_name = 'public/crispy_card.html'
    form_class = JuniorProfileForm
    edit = False

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['disabled'] = not self.edit
        return kwargs

    def get_object(self, queryset=None):
        return JuniorProfile.objects.get(person_id=self.kwargs['pk'])

    def get_context_data(self, **kwargs):
        person = Person.objects.get(pk=self.kwargs['pk'])
        kwargs['form_title'] = "Junior profile for " + person.fullname
        if not self.edit:
            kwargs['buttons'] = [Button("Edit", "edit")]
        else:
            kwargs['buttons'] = [Button("Save", "save")]
        return super().get_context_data(**kwargs)

    def post(self, request, *args, **kwargs):
        if 'edit' in request.POST:
            return redirect('junior-profile-edit', pk=self.kwargs['pk'])
        return super().post(request, *args, *kwargs)

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

