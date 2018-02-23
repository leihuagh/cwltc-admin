from django.shortcuts import render
from django.views.generic import DetailView, TemplateView, CreateView
from django.core.exceptions import ObjectDoesNotExist
from django.http import Http404
from braces.views import LoginRequiredMixin
from members.models import Person

# Club Members views

class ClubHomeView(LoginRequiredMixin, TemplateView):
    template_name = 'club/home.html'


class ClubPersonalView(LoginRequiredMixin, DetailView):
    '''
    Display personal data for the logged in user
    '''
    model = Person
    template_name = 'members/person_detail.html'

    def get_object(self, queryset = None):
        try:
            obj = Person.objects.get(auth_id = self.request.user.id)
        except ObjectDoesNotExist:
            raise Http404                    
        return obj
    
      

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