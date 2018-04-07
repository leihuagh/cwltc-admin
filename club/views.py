from django.shortcuts import reverse, redirect
from django.views.generic import DetailView, TemplateView, UpdateView
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from django.http import Http404, HttpResponseRedirect
from braces.views import LoginRequiredMixin
from mysite.common import Button
from members.models import Person, Address
from members.views import set_person_context, add_membership_context
from public.forms import NameForm, AddressForm
from django.forms import modelform_factory
# Club Members views


class ClubHomeView(LoginRequiredMixin, TemplateView):
    template_name = 'club/home.html'


class PersonView(LoginRequiredMixin, DetailView):
    '''
    Display personal data for the logged in user
    '''
    model = Person
    form_class = NameForm
    template_name = 'club/person_detail.html'

    def get_object(self, queryset = None):
        if 'pk' in self.kwargs:
            obj = Person.objects.get(pk=self.kwargs['pk'])
        else:
            try:
                obj = Person.objects.get(auth_id=self.request.user.id)
            except ObjectDoesNotExist:
                raise PermissionDenied
        return obj

    def get_context_data(self, **kwargs):
        person = self.get_object()
        context = super().get_context_data()
        set_person_context(context, person)
        add_membership_context(context)
        return context


class PersonUpdateView(LoginRequiredMixin, UpdateView):
    """
    Update name and address
    """
    model = Person
    form_class = NameForm
    template_name = 'club/crispy_card.html'

    def get_context_data(self, **kwargs):
        kwargs['form_title'] = 'Edit personal details'
        kwargs['buttons'] = (Button('Save', css_class='btn-success'),
                             Button('Cancel', css_class='btn-default'))
        return super().get_context_data(**kwargs)

    def post(self, request, *args, **kwargs):
        if 'cancel' in request.POST:
            return redirect('club_person')
        return super().post(request, *args, **kwargs)

    def get_success_url(self):
        return reverse('club_person')


class AddressUpdateView(LoginRequiredMixin, UpdateView):
    """
    Update address
    """
    model = Address
    form_class = AddressForm
    template_name = 'club/crispy_card.html'

    def get_object(self, queryset=None):
        self.person = Person.objects.get(pk=self.kwargs['person_id'])
        return Address.objects.get(pk=self.person.address_id)


    def get_context_data(self, **kwargs):
        kwargs['form_title'] = 'Edit address details'
        kwargs['buttons'] = (Button('Save', css_class='btn-success'),
                             Button('Cancel', css_class='btn-default'))
        return super().get_context_data(**kwargs)

    def post(self, request, *args, **kwargs):
        if 'cancel' in request.POST:
            self.get_object()
            return redirect('club_person_pk', pk=self.person.id)
        return super().post(request, *args, **kwargs)


    def get_success_url(self):
        return reverse('club_person')


class ClubAccountView(LoginRequiredMixin, DetailView):
    model = Person
    template_name = 'members/person_detail.html'

    def get_object(self, queryset = None):
        try:
            obj = Person.objects.get(auth_id = self.request.user.id)
        except ObjectDoesNotExist:
            raise Http404                    
        return obj


class ClubSearchView(LoginRequiredMixin, TemplateView):
    template_name = 'club/search.html'


class ClubMagazineView(LoginRequiredMixin, TemplateView):
    template_name = 'club/magazine.html'

    def get_context_data(self, **kwargs):
        super().get_context_data(**kwargs)