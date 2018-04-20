import logging
from django.views.generic import DetailView, CreateView, UpdateView, ListView, TemplateView, View
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render
from django.contrib import messages
from braces.views import StaffuserRequiredMixin
from events.models import Event, Participant, Tournament
from club.views import person_from_user
from members.models import Person
from events.forms import EventForm, TournamentForm
from mysite.common import Button

stdlogger = logging.getLogger(__name__)


class EventHelpView(LoginRequiredMixin, TemplateView):
    template_name = 'events/event_help.html'


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
        context['buttons'] = [Button('Save', css_class='btn-success'),
                              Button('Delete', css_class='btn-danger')]
        return context

    def post(self, request, *args, **kwargs):
        if 'delete' in request.POST:
            event = self.get_object(request)
            event.delete()
            return redirect('events:list')
        return super().post(request, *args, **kwargs)


class EventDetailView(LoginRequiredMixin, DetailView):
    """ Shows participants and allows entry or cancellation """
    model = Event
    template_name = 'events/event_detail.html'
    person = None

    def dispatch(self, request, *args, **kwargs):
        self.person = person_from_user(request)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        event = self.object
        participants = Participant.objects.filter(event=self.object).select_related('person')
        participant = participants.filter(person=self.person)
        partner = participants.filter(partner=self.person)
        entered = participant.exists() or partner.exists()
        if entered:
            if len(participant) and participant[0].partner:
                context['partner_name'] = participant[0].partner.fullname
            elif len(partner) and partner[0].person:
                context['partner_name'] = partner[0].person.fullname
        else:
            context['can_enter'] = ((event.is_male_only() and self.person.gender == 'M') or (
                event.is_female_only() and self.person.gender == 'F') or event.is_mixed()) and event.online_entry
        context['participants'] = participants
        context['entered'] = entered
        context['with_partner'] = self.object.with_partner()
        return context

    def post(self, request, **kwargs):
        event = self.get_object()
        if self.person:
            partner = None
            partner_id = request.POST.get('partner_id', None)
            if partner_id:
                partner = Person.objects.get(id=partner_id)
            if 'remove' in request.POST:
                part = event.participant_from_person(self.person)
                if part:
                    part.delete()
                    messages.success(request, f'You have been removed from {event.name}.')
            if 'add' in request.POST:
                error = event.validate_entrants(self.person, partner)
                if not error:
                    if partner:
                        participant = event.participant_from_person(partner)
                        if participant:
                            if participant.partner is None:
                                # assign a single to us
                                participant.delete()
                            else:
                                error = 'Your partner has already entered with someone else'
                        if not error:
                            # get mixed doubles in a consistent form
                            if self.person.gender == 'M' and partner.gender == 'F':
                                self.person, partner = partner, self.person
                if error:
                    self.object = event
                    context = self.get_context_data(**kwargs)
                    context['error'] = error
                    return render(request, self.template_name, context)

                else:
                    Participant.objects.create(event=event, person=self.person, partner=partner)
                    messages.success(request, f'You have been entered in the {event.name}.')
            if 'single' in request.POST:
                Participant.objects.create(event=event, person=self.person, partner=None)
                messages.success(request, f'You have been added to the list of people without a partner for {event.name}.')
        return redirect('events:tournament_detail', pk=event.tournament.id)


class EventListView(ListView):
    model = Event
    template_name = 'events/event_list.html'


class EventAdminView(ListView):
    model = Event
    template_name = 'events/event_admin.html'


class TournamentCreateView(StaffuserRequiredMixin, CreateView):
    model = Tournament
    form_class = TournamentForm
    template_name = 'events/event_form.html'
    success_url = reverse_lazy('events:tournaments_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form_title'] = 'Create tournament'
        context['buttons'] = [Button('Save', css_class='btn-success')]
        return context

    def form_valid(self, form):
        tournament = form.save()
        tournament.add_standard_events()
        return redirect('events:tournament_list')


class TournamentUpdateView(StaffuserRequiredMixin, UpdateView):
    model = Tournament
    form_class = TournamentForm
    template_name = 'events/event_form.html'
    success_url = reverse_lazy('events:tournament_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form_title'] = 'Update event'
        context['buttons'] = [Button('Save', css_class='btn-success'),
                              Button('Delete', css_class='btn-danger')]
        return context

    def form_valid(self, form):
        if 'delete' in self.request.POST:
            self.object.delete()
            return redirect('events:tournament_list')
        else:
            return super().form_valid(form)


class TournamentDetailView(LoginRequiredMixin, DetailView):
    model = Tournament
    template_name = 'events/tournament_detail.html'
    success_url = reverse_lazy('events:tournament_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['event_list'] = self.object.event_set.filter(active=True).order_by('id')
        return context


class TournamentListView(LoginRequiredMixin, ListView):
    model = Tournament
    template_name = 'events/tournament_list.html'


class TournamentAdminView(StaffuserRequiredMixin, ListView):
    model = Tournament
    template_name = 'events/tournament_admin.html'


class TournamentActiveView(View):

    def get(self, request):
        tours = Tournament.objects.filter(active=True)
        if len(tours) == 1:
            return redirect('events:tournament_detail', pk=tours[0].pk)
        else:
            return redirect('events:tournament_list')


