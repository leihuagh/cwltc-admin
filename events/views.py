from django.views.generic import DetailView, CreateView, UpdateView, ListView, TemplateView, View
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, reverse
from django_tables2 import SingleTableView
from events.models import Event, Participant
from club.views import person_from_user
from events.forms import *
from mysite.common import Button


class EventCreateView(LoginRequiredMixin, CreateView):
    model = Event
    form_class = EventForm
    template_name = 'events/event_form.html'
    success_url = reverse_lazy('events:list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form_title'] = 'Create new event'
        context['buttons'] = [Button('Save', css_class='btn-success')]
        return context


class EventUpdateView(LoginRequiredMixin, UpdateView):
    model = Event
    form_class = EventForm
    template_name = 'events/event_form.html'
    success_url = reverse_lazy('events:list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form_title'] = 'Update event'
        context['buttons'] = [Button('Save', css_class='btn-success')]
        return context


class EventDetailView(LoginRequiredMixin, DetailView):
    model = Event
    template_name = 'events/event_detail.html'

    def dispatch(self, request, *args, **kwargs):
        self.person = person_from_user(request)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        participants = Participant.objects.filter(event=self.object).select_related('person')
        entered = participants.filter(person=self.person).exists()
        buttons = [Button('Back')]
        if entered:
            buttons.append(Button('Remove'))
        else:
            buttons.append(Button('Add'))


        context['buttons'] = buttons
        context['participants'] = participants
        context['entered'] = entered
        context['with_partner'] = self.object.with_partner()
        return context

    def post(self, request, **kwargs):
        if self.person:
            event = self.get_object()
            if 'remove' in request.POST:
                Participant.objects.filter(event=event, person=self.person).delete()
            if 'add' in request.POST:
                Participant.objects.create(person=self.person,event=event)
        return redirect('events:list')


class EventListView(ListView):
    model = Event
    template_name = 'events/event_list.html'

