import logging
from django.views.generic import DetailView, CreateView, UpdateView, ListView, TemplateView, View
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render
from django.contrib import messages
from django.http import HttpResponse
from django.template import RequestContext, loader
from django_tables2 import SingleTableView
from events.models import Event, Participant
from club.views import person_from_user
from members.models import Person
from events.forms import *
from mysite.common import Button

stdlogger = logging.getLogger(__name__)

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
    """ Shows participants and allows entry or cancellation """
    model = Event
    template_name = 'events/event_detail.html'

    def dispatch(self, request, *args, **kwargs):
        self.person = person_from_user(request)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        participants = Participant.objects.filter(event=self.object).select_related('person')
        participant = participants.filter(person=self.person)
        entered = participant.exists()
        if entered and len(participant) == 1:
            context['partner_name'] = participant[0].partner.fullname
        context['participants'] = participants
        context['entered'] = entered
        context['with_partner'] = self.object.with_partner()
        return context


    def post(self, request, **kwargs):
        if self.person:
            partner = None
            event = self.get_object()
            partner_id = request.POST.get('partner_id', None)
            if partner_id:
                partner = Person.objects.get(id=partner_id)
            if 'remove' in request.POST:
                message = f'You have been removed from {event.name}'
                part = Participant.objects.filter(event=event, person=self.person)
                if len(part) == 1:
                    part[0].delete()
                    messages.success(request, message)
                else:
                    part = Participant.objects.filter(event=event, partner=partner)
                    if len(part) == 1:
                        part[0].delete()
                        messages.success(request, message)
            if 'add' in request.POST:
                error = event.validate_entrants(self.person, partner)
                if error:
                    self.object = event
                    context = self.get_context_data( **kwargs)
                    context['error'] = error
                    return render(request, self.template_name, context)
                else:
                    Participant.objects.create(event=event, person=self.person, partner=partner)
        return redirect('events:list')


class EventListView(ListView):
    model = Event
    template_name = 'events/event_list.html'

