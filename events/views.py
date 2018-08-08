import logging
from django.views.generic import DetailView, CreateView, UpdateView, ListView, TemplateView, View, FormView
from django.urls import reverse, reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render
from django.contrib import messages
from django.http import Http404
from braces.views import StaffuserRequiredMixin
from mysite.common import Button, LinkButton
from club.views import person_from_user
from members.views import SingleTableView
from members.models import Person, ItemType
from events.models import Event, Participant, Tournament
from events.forms import SocialEventForm, TournamentEventForm, TournamentForm, RegisterForm
from events.download import export_event, export_tournament
from events.tables import EventTable, TournamentTable

stdlogger = logging.getLogger(__name__)

# todo sort permissions fro events and tournament

class EventAdminTableView(StaffuserRequiredMixin, SingleTableView):
    """ Show events in a table """
    model = Event
    template_name = 'events/table.html'
    table_class = EventTable
    id = None

    def get_table_data(self, **kwargs):
        self.id = self.kwargs.get('tournament_id', None)
        if self.id:
            return Event.objects.filter(tournament_id=self.id).order_by('id')
        else:
            return Event.objects.all().order_by('id')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Events'
        if self.id:
            tournament = Tournament.objects.get(id=self.id)
            context['title'] += f' linked to {tournament.name}'
        else:
            context['buttons'] = [LinkButton('Create social event', reverse('events:create_social'))]
        return context


class EventHelpView(LoginRequiredMixin, TemplateView):
    """ Just shows help screen """
    template_name = 'events/event_help.html'


class EventCreateView(StaffuserRequiredMixin, CreateView):
    """ Creates a social or tournament event """
    model = Event
    template_name = 'events/event_form.html'
    success_url = reverse_lazy('events:admin')
    social = False

    def get_form_class(self):
        if self.social:
            return SocialEventForm
        else:
            return TournamentEventForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form_title'] = f'Create new {"social " if self.social else ""}event'
        context['buttons'] = [Button('Save', css_class='btn-success')]
        return context

    def form_valid(self, form):
        form.instance.item_type_id = ItemType.SOCIAL if self.social else ItemType.TOURNAMENT
        return super().form_valid(form)


class EventUpdateView(StaffuserRequiredMixin, UpdateView):
    """ Update event details - date etc"""
    model = Event
    form_class = TournamentEventForm
    template_name = 'events/event_form.html'
    success_url = reverse_lazy('events:admin')

    def get_form_class(self):
        if self.object.item_type_id == ItemType.SOCIAL:
            return SocialEventForm
        else:
            return TournamentEventForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form_title'] = 'Update event'
        context['buttons'] = [Button('Save', css_class='btn-success'),
                              Button('Delete', css_class='btn-danger')]
        if not self.object.active and not self.object.billed:
            context['buttons'].append(Button('Create invoice items', css_class='btn-success'))
        if self.object.participant_set.all().count():
            context['link_buttons'] = [LinkButton('Participants',
                                                  href=reverse('events:participant_list',
                                                               kwargs={'pk': self.object.id}))]
        return context

    def post(self, request, *args, **kwargs):
        event = self.get_object()
        if 'delete' in request.POST:
            event.delete()
            return redirect('events:admin')
        elif 'create-invoice-items' in request.POST:
            count = event.billing_data().process()
            messages.success(request, f'{count} invoice items created')
            return redirect('events:admin')
        return super().post(request, *args, **kwargs)


class EventListView(LoginRequiredMixin, ListView):
    """ List active events"""
    model = Event
    template_name = 'events/event_list.html'


    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        events = Event.objects.filter(item_type_id=ItemType.SOCIAL,
                                      active=True, online_entry=True).order_by(
            'end_date').prefetch_related('participant_set__person')
        for event in events:
            event.tickets = event.ticket_count(person_from_user(self.request))
        context['social'] = events
        context['tournaments'] = Tournament.active_objects.all()
        return context


class EventDetailView(LoginRequiredMixin, DetailView):
    """ Shows participants and allows user to enter or cancel"""
    model = Event
    template_name = 'events/event_detail.html'
    person = None

    def dispatch(self, request, *args, **kwargs):
        self.person = person_from_user(request)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        event = self.object
        participants = Participant.objects.filter(event=self.object).order_by(
            'person__first_name', 'person__last_name').select_related('person')
        participant = participants.filter(person=self.person)
        partner = participants.filter(partner=self.person)
        entered = (participant.exists() or partner.exists()) and event.online_entry
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


class EventRegisterView(LoginRequiredMixin, FormView):
    """ User can register for a social event
    """

    form_class = RegisterForm
    template_name = 'events/event_register.html'
    person = None
    event = None
    success_url = 'events:list'

    def dispatch(self, request, *args, **kwargs):
        self.person = person_from_user(request)
        self.event = Event.objects.get(pk=self.kwargs['pk'])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        participants = Participant.objects.filter(event=self.event)
        context['event'] = self.event
        context['participants'] = participants
        if self.event.cost > 0:
            context['buttons'] = [Button('Buy tickets')]
            context['form_title'] = 'Buy tickets now'
        else:
            context['buttons'] = [Button('Sign up')]
            context['form_title'] = 'Sign up now'
        registered = participants.filter(person=self.person)
        if registered:
            context['tickets'] = registered[0].tickets
            context['buttons'].append(Button('Cancel', css_class='btn-danger',
                                             no_validate=True))
        return context

    def post(self, request, *args, **kwargs):
        if 'cancel' in request.POST:
            Participant.objects.filter(person=self.person).delete()
            messages.warning(self.request, f'Your tickets have been cancelled')
            return redirect(self.success_url)
        else:
            return super().post(request, *args, **kwargs)


    def form_valid(self, form):
        participants = Participant.objects.filter(event=self.event, person=self.person)
        if len(participants) == 1:
            part = participants[0]
            part.tickets += form.cleaned_data['number_of_tickets']
        else:
            part = Participant(event=self.event, person=self.person,
                               text=form.cleaned_data['special_diet'],
                               tickets=form.cleaned_data['number_of_tickets'])
        part.save()
        messages.success(self.request, f'Thanks for buying tickets')
        return redirect(self.success_url)


class ParticipantListView(LoginRequiredMixin, DetailView):
    """
    Admin view: List participants in an event
    Template has buttons to add or edit
    """
    model = Event
    template_name = 'events/participant_list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        participants = Participant.objects.filter(event=self.object).order_by(
            'person__first_name').select_related('person')
        context['with_partner'] = self.object.with_partner()
        context['participants'] = participants
        return context


class ParticipantDownloadView(LoginRequiredMixin, View):

    def get(self, request, *args, **kwargs):
        id = kwargs.get('pk', None)
        try:
            event = Event.objects.get(pk=id)
        except Event.DoesNotExist:
            return Http404
        return export_event(event)


class ParticipantAddView(LoginRequiredMixin, DetailView):
    """ Admin view: Add a participant or doubles pair to an event """
    model = Event
    template_name = 'events/participant_edit.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['event'] = self.object
        context['with_partner'] = self.object.with_partner()
        context['can_delete'] = False
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        participant = Participant(event=self.object)
        error = handle_participant_post(request, participant)
        if error:
            context = self.get_context_data(**kwargs)
            context['error'] = error
            return render(request, self.template_name, context)
        else:
            return redirect('events:participant_list', pk=self.object.id)


class ParticipantEditView(LoginRequiredMixin, DetailView):
    """ Admin view: Edit or delete a participant in an event """
    model = Participant
    template_name = 'events/participant_edit.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        participant = self.object
        context['event'] = participant.event.name
        context['player1'] = participant.person
        context['player2'] = participant.partner
        context['with_partner'] = participant.event.with_partner()
        context['can_delete'] = True
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        error = handle_participant_post(request, self.object)
        if error:
            context = self.get_context_data(**kwargs)
            context['error'] = error
            return render(request, self.template_name, context)
        else:
            return redirect('events:participant_list', pk=self.object.event.id)


def handle_participant_post(request, participant):
    """ Common handler for create and edit participants in admin mode
        Allows normally ineligible people to be saved with a warning so new
        members can be included
        return None or error message """
    event = participant.event
    person = None
    partner = None
    person_id = request.POST.get('player1', None)
    if person_id:
        person = Person.objects.get(pk=person_id)
    partner_id = request.POST.get('player2', None)
    if partner_id:
        partner = Person.objects.get(pk=partner_id)
    if 'save' in request.POST:
        if person:
            error = event.validate_entrants(person, partner)
            if error:
                error2 = event.validate_entrants(person, partner, skip_eligibility=True)
                if error2:
                    return error2
                else:
                    messages.warning(request, f'Warning - Record saved but validation failed: {error}')
            if person.gender == 'M' and partner and partner.gender == 'F':
                person, partner = partner, person
            participant.person = person
            participant.partner = partner
            participant.save()
        else:
            return "Player 1 is not defined"
    elif 'delete' in request.POST:
        if participant.id:
            participant.delete()
    return None


class TournamentCreateView(StaffuserRequiredMixin, CreateView):
    """ Create a standard club tournament set of events"""
    model = Tournament
    form_class = TournamentForm
    template_name = 'events/event_form.html'
    success_url = reverse_lazy('events:tournaments_table')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form_title'] = 'Create tournament'
        context['buttons'] = [Button('Save', css_class='btn-success')]
        return context

    def form_valid(self, form):
        tournament = form.save()
        tournament.add_standard_events()
        return redirect('events:tournament_admin')


class TournamentUpdateView(StaffuserRequiredMixin, UpdateView):
    model = Tournament
    form_class = TournamentForm
    template_name = 'events/event_form.html'
    success_url = reverse_lazy('events:tournament_admin')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        actives = self.object.event_count(active=True)
        inactives = self.object.event_count(active=False)
        context['form_title'] = 'Update tournament'
        context['tournament'] = True
        context['active_events'] = actives
        context['inactive_events'] = inactives
        context['link_buttons'] = [LinkButton('Events',
                                              href=reverse('events:admin_tournament',
                                                           kwargs={'tournament_id': self.object.id})),
                                   LinkButton('Download participants',
                                              href=reverse('events:tournament_download',
                                                           kwargs={'pk': self.object.id})),
                                   ]
        context['buttons'] = [Button('Save', css_class='btn-success'),
                              Button('Delete', css_class='btn-danger'),
                              ]
        if not self.object.billed:
            if actives:
                context['buttons'].append(Button('Make inactive'))
            else:
                context['buttons'].append(Button('Make active'))
                context['buttons'].append(Button('Create invoice items', css_class='btn-success'))
        return context

    def form_valid(self, form):
        request = self.request
        if 'delete' in request.POST:
            self.object.delete()
            return redirect('events:tournament_admin')
        elif 'create-invoice-items' in request.POST:
            count = self.object.generate_bills()
            messages.success(self.request, f'{count} invoice items created')
            return redirect('events:tournament_admin')
        elif 'make-active' in request.POST:
            self.object.make_active()
            return redirect(self.request.path)
        elif 'make-inactive' in request.POST:
            self.object.make_active(False)
            return redirect(self.request.path)
        else:
            return super().form_valid(form)


class TournamentDetailView(LoginRequiredMixin, DetailView):
    model = Tournament
    template_name = 'events/tournament_detail.html'
    success_url = reverse_lazy('events:tournament_admin')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['event_list'] = self.object.event_set.filter(active=True).order_by('id')
        return context


class TournamentAdminView(StaffuserRequiredMixin, SingleTableView):
    model = Tournament
    template_name = 'events/table.html'
    table_class = TournamentTable

    def get_table_data(self, **kwargs):
        return Tournament.objects.all().order_by('id')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Tournaments'
        context['buttons'] = [LinkButton('Create tournament', reverse('events:tournament_create'))]
        return context


class TournamentDownloadView(StaffuserRequiredMixin, View):

    def get(self, request, **kwargs):
        id = kwargs.get('pk', None)
        try:
            tournament = Tournament.objects.get(pk=id)
        except Tournament.DoesNotExist:
            return Http404
        return export_tournament(tournament)


class TournamentPlayersView(ListView):
    model = Person
    template_name = 'events/people_list.html'
    context_object_name = 'person_list'

    def get_queryset(self):
        tournament = Tournament.objects.get(pk=self.kwargs['pk'])
        return tournament.players_list()

