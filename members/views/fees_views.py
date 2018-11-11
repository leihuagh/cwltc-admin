import logging
from django.views.generic import ListView, CreateView, UpdateView
from django.contrib import messages
from django.shortcuts import redirect, reverse
from braces.views import StaffuserRequiredMixin
from django_tables2 import SingleTableView
from mysite.common import Button
from members.models import Membership, Fees, VisitorFees
from members.forms import FeesForm, VisitorFeesForm

stdlogger = logging.getLogger(__name__)


class FeesCreateView(StaffuserRequiredMixin, CreateView):
    model = Fees
    form_class = FeesForm
    template_name = 'members/generic_crispy_form.html'

    def get_success_url(self):
        return reverse('fees-list')


class FeesUpdateView(StaffuserRequiredMixin, UpdateView):
    model = Fees
    form_class = FeesForm
    template_name = 'members/generic_crispy_form.html'
    title = 'Update fees'

    def get_context_data(self, **kwargs):
        context = super(FeesUpdateView, self).get_context_data(**kwargs)
        context['title'] = 'Fees for {}'.format(self.get_object().sub_year)
        return context

    def form_invalid(self, form):
        if 'cancel' in form.data:
            return redirect('fees-list-year', year=self.get_object().sub_year)
        return super(FeesUpdateView, self).form_invalid(form)

    def form_valid(self, form):
        if 'cancel' in form.data:
            return redirect('fees-list-year', year=self.get_object().sub_year)

        if 'submit' in form.data:
            return super(FeesUpdateView, self).form_valid(form)

    def get_success_url(self):
        return reverse('fees-list-year', kwargs={'year': self.get_object().sub_year})


class FeesListView(StaffuserRequiredMixin, ListView):
    model = Fees
    template_name = 'members/fees_list.html'
    year = 0
    latest_year = 0
    title = 'List fees'

    def get_queryset(self):
        self.year = int(self.kwargs.get('year', 0))
        self.latest_year = Fees.objects.all().order_by('-sub_year')[0].sub_year
        if self.year == 0:
            self.year = self.latest_year
        return Fees.objects.filter(sub_year=self.year).order_by('membership')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['year'] = self.year
        context['latest'] = (self.latest_year == self.year)
        context['forward'] = self.year + 1
        context['back'] = self.year - 1
        if not VisitorFees.objects.filter(year=self.year).exists():
            messages.warning(self.request, f'Warning: No visitors fees exist for {self.year}')
        return context

    def post(self, request, *args, **kwargs):
        year = int(request.POST['year'])
        if 'back' in request.POST:
            return redirect('fees-list-year', year - 1)
        elif 'forward' in request.POST:
            return redirect('fees-list-year', year + 1)
        elif 'copy' in request.POST:
            for cat in Membership.objects.all():
                fee = Fees.objects.filter(sub_year=year, membership_id=cat.id)[0]
                if not fee:
                    fee = Fees(annual_sub=0, monthly_sub=0, joining_fee=0, Membership_id=cat.id)
                fee.sub_year = year + 1
                fee.id = None
                fee.save()
            messages.success(self.request, "Records for {} created".format(year + 1))
            return redirect('fees-list-year', year + 1)
        elif 'delete' in request.POST:
            for fee in Fees.objects.filter(sub_year=year):
                fee.delete()
            messages.success(self.request, "All records for {} deleted".format(year))
            return redirect('fees-list-year', year - 1)


class VisitorFeesUpdateView(StaffuserRequiredMixin, UpdateView):
    model = VisitorFees
    form_class = VisitorFeesForm
    template_name = 'members/generic_crispy_form_well.html'
    title = 'Update visitor fees'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Visitor fees'
        context['buttons'] = [
            Button('Save', name='save', css_class='btn-default'),
            Button('Delete', name='delete', css_class='btn-danger'), ]
        return context

    def get_success_url(self):
        return reverse('visitor-fees-list')

    def post(self, request, *args, **kwargs):
        if 'delete' in request.POST:
            self.get_object().delete()
            return redirect(self.get_success_url())
        return super().post(request, *args, **kwargs)


class VisitorFeesListView(StaffuserRequiredMixin, SingleTableView):
    model = VisitorFees
    template_name = 'members/visitors_fees_list.html'
    title = 'Visitor fees'

    def get_queryset(self):
        return VisitorFees.objects.all().order_by('-year')

    def post(self, request):
        if 'create' in request.POST:
            records = self.get_queryset()
            if records:
                record = records[0]
                VisitorFees.objects.create(year=record.year + 1,
                                           adult_fee=record.adult_fee,
                                           junior_fee=record.junior_fee)
            else:
                VisitorFees.objects.create(year=2017, adult_fee=6, junior_fee=3)
        return redirect('visitor-fees-list')
