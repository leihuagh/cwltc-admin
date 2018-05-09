import logging
from psycopg2.extras import DateRange
from datetime import date, time, timedelta, datetime
from django.shortcuts import redirect
from django.utils.dateparse import parse_date, parse_time

from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import DetailView, CreateView, UpdateView, ListView, TemplateView, View
from django.urls import reverse_lazy

from django.contrib import messages
from braces.views import StaffuserRequiredMixin
from mysite.common import Button
from club.views import person_from_user
from members.models import Person
from .models import Booking
from .forms import BookingForm

stdlogger = logging.getLogger(__name__)


class WeekNowView(View):

    def get(self, request):
        return redirect('diary:week', date=datetime.now().date())


class WeekView(TemplateView):
    template_name = 'diary/week_view.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        date_list = []
        start_date = parse_date(self.kwargs['date'])
        while start_date.weekday() != 0:
            start_date -= timedelta(days=1)
        end_date = start_date + timedelta(days=7)
        booked_list = list(Booking.objects.all().select_related('person').order_by('date'))
        dat = start_date
        while dat < end_date:
            row = [dat]
            for tim in [time(19, 0, 0), time(20, 30, 0)]:
                times = [tim]
                courts = []
                for court in [1, 4]:
                    booked = search(booked_list, dat, tim, court)
                    if booked:
                        courts.append([court, booked])
                    else:
                        courts.append([court, ''])
                times.append(courts)
                row.append(times)
            date_list.append(row)
            dat += timedelta(days=1)
        context['date_list'] = date_list
        context['week_back'] = str(start_date - timedelta(days=7))
        context['week_forward'] = str(start_date + timedelta(days=7))
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

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        context['date'] = parse_date(self.kwargs['date'])
        context['time'] = parse_time(self.kwargs['time'])
        context['court'] = self.kwargs['court']
        context['person'] = person_from_user(self.request)
        context['buttons'] = [Button('Save'), Button('Back')]
        return context

    def post(self, request, *args, **kwargs):
        if 'back' in request.POST:
            return redirect('diary:week', date=self.kwargs['date'])
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        booking = Booking(date=parse_date(self.kwargs['date']),
                          time=parse_time(self.kwargs['time']),
                          court=self.kwargs['court'],
                          person = person_from_user(self.request),
                          note=form.cleaned_data['note']
                          )
        booking.save()
        return redirect('diary:week', date=self.kwargs['date'])


class BookingUpdateView(LoginRequiredMixin, UpdateView):
    model = Booking
    form_class = BookingForm
    template_name = 'diary/booking_form.html'
    booking = None

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        context['date'] = self.object.date
        context['time'] = self.object.time
        context['court'] = self.object.court
        context['person'] = person_from_user(self.request)
        context['buttons'] = [Button('Save'), Button('Back'), Button('Delete') ]
        return context

    def post(self, request, *args, **kwargs):
        self.booking = self.get_object()
        if 'save' in request.POST:
            return super().post(request, *args, **kwargs)
        if 'delete' in request.POST:
            self.booking.delete()
        return redirect('diary:week', date=self.booking.date)


    def form_valid(self, form):
        self.booking.note = form.cleaned_data['note']
        self.booking.save()
        return redirect('diary:week', date=self.booking.date)


class BookingListView(LoginRequiredMixin, ListView):
    model = Booking
    template_name = 'diary/booking_list.html'
    context_object_name = 'bookings'