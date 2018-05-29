import logging
from psycopg2.extras import DateRange
from datetime import date, time, timedelta, datetime
from django.shortcuts import redirect
from django.db.models import Q
from django.utils.dateparse import parse_date, parse_time

from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import DetailView, CreateView, UpdateView, ListView, TemplateView, View
from braces.views import StaffuserRequiredMixin
from mysite.common import Button
from club.views import person_from_user
from .models import Booking
from .forms import BookingForm

stdlogger = logging.getLogger(__name__)


class WeekNowView(LoginRequiredMixin, View):

    def get(self, request):
        return redirect('diary:week', date=datetime.now().date())


class WeekView(LoginRequiredMixin, TemplateView):
    template_name = 'diary/week_view.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        date_list = []
        start_date = parse_date(self.kwargs['date'])

        while start_date.weekday() != 0:
            start_date -= timedelta(days=1)
        end_date = start_date + timedelta(days=7)
        my_id = person_from_user(self.request).id
        booked_list = list(Booking.objects.filter(date__range=[start_date, end_date]).select_related('person').order_by('date'))
        owned = Booking.objects.filter(person_id=my_id).select_related('person').order_by('date')
        included = Booking.objects.filter(Q(player_2_id=my_id) | Q(player_3_id=my_id) | Q(player_4_id=my_id)).select_related('person').order_by('date')

        if start_date < date(2018, 7, 14):
            dat = start_date
            while dat < end_date:
                row = [dat]
                times = []
                slots = [time(10), time(12), time(14), time(16), time(18, 30), time(20, 15)]
                if dat.weekday() == 5:
                    slots = [time(12), time(18), time(20)]
                if dat.weekday() == 6:
                    slots = [time(14), time(16), time(18), time(20)]
                for tim in slots:
                    bookings = [tim.strftime('%H:%M')]
                    for court in [1, 4]:
                        if dat < datetime.now().date():
                            bookings.append(0)
                        else:
                            booked = search(booked_list, dat, tim, court)
                            if booked:
                                bookings.append(booked)
                            else:
                                bookings.append(court)
                    times.append(bookings)
                row.append(times)
                date_list.append(row)
                dat += timedelta(days=1)
        context['date_list'] = date_list
        context['week_back'] = str(start_date - timedelta(days=7))
        context['week_forward'] = str(start_date + timedelta(days=7))
        context['owned'] = owned
        context['included'] = included
        return context

def search(booked_list, date, time, court):
    for b in booked_list:
        if date == b.date:
            if time == b.time:
                if court == b.court:
                    return b
        if b.date > date:
            return None
    return None


class BookingCreateView(LoginRequiredMixin, CreateView):
    model = Booking
    form_class = BookingForm
    template_name = 'diary/booking_form.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        if self.request.user.is_staff:
            kwargs['admin'] = True
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        context['date'] = parse_date(self.kwargs['date'])
        context['time'] = parse_time(self.kwargs['time'])
        context['court'] = self.kwargs['court']
        context['person'] = person_from_user(self.request)
        context['can_edit'] = True
        context['buttons'] = [Button('Save'), Button('Back')]
        return context

    def post(self, request, *args, **kwargs):
        if 'back' in request.POST:
            return redirect('diary:week', date=self.kwargs['date'])
        form = self.get_form()
        self.object = None
        if form.is_valid():
            booking = Booking(date=parse_date(self.kwargs['date']),
                              time=parse_time(self.kwargs['time']),
                              court=self.kwargs['court'],
                              person=person_from_user(self.request),
                              player_2_id=form.cleaned_data['player_2_id'],
                              player_3_id=form.cleaned_data['player_3_id'],
                              player_4_id=form.cleaned_data['player_4_id'],
                              note=form.cleaned_data['note'],
                              blocked=form.cleaned_data['blocked']
                              )
            booking.save()
            if not booking.blocked:
                booking.mail_players()
            return redirect('diary:week', date=self.kwargs['date'])
        else:
            return self.form_invalid(form)


class BookingUpdateView(LoginRequiredMixin, UpdateView):
    model = Booking
    form_class = BookingForm
    template_name = 'diary/booking_form.html'
    booking = None

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        if self.request.user.is_staff:
            kwargs['admin'] = True
        return kwargs

    def get_initial(self):
        data = super().get_initial()
        data['player_2_id'] = self.object.player_2_id
        data['player_3_id'] = self.object.player_3_id
        data['player_4_id'] = self.object.player_4_id
        data['doubles'] = self.object.player_3_id or self.object.player_4_id
        data['blocked'] = self.object.blocked
        return data

    def get_object(self, queryset=None):
        object =  super().get_object(queryset=None)
        return object

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        person = person_from_user(self.request)
        can_edit = person == self.object.person
        context['date'] = self.object.date
        context['time'] = self.object.time
        context['court'] = self.object.court
        context['person'] = self.object.person
        context['can_edit'] = can_edit
        context['buttons'] = [Button('Back')]
        if can_edit:
            context['buttons'] += [Button('Save'), Button('Delete')]
        return context

    def post(self, request, *args, **kwargs):
        self.booking = self.get_object()
        if 'save' in request.POST:
            return super().post(request, *args, **kwargs)
        if 'delete' in request.POST:
            if self.booking.player_2:
                self.booking.mail_players(delete=True)
            self.booking.delete()
        return redirect('diary:week', date=self.booking.date)

    def form_valid(self, form):
        self.booking = form.save(commit=False)
        self.booking.player_2_id = form.cleaned_data['player_2_id']
        self.booking.player_3_id = form.cleaned_data['player_3_id']
        self.booking.player_4_id = form.cleaned_data['player_4_id']
        # self.booking.note = form.cleaned_data['note']
        self.booking.save()
        self.booking.mail_players(update=True)
        return redirect('diary:week', date=self.booking.date)


class BookingListView(LoginRequiredMixin, ListView):
    model = Booking
    template_name = 'diary/booking_list.html'
    context_object_name = 'bookings'

    def post(self, request):
        if 'delete' in request.POST:
            Booking.delete_expired()
        return redirect('diary:list')
