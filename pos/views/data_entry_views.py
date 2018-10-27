import logging
from datetime import datetime
from decimal import Decimal
from django.views.generic import FormView
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from braces.views import GroupRequiredMixin
from pos.forms import PosDataEntryForm, VisitorsDataEntryForm
from pos.models import ItemType, Transaction, Visitor, VisitorBook
from pos.views import VisitorCreateView
from members.models import Person, VisitorFees, Settings


stdlogger = logging.getLogger(__name__)


class PosDataEntryView(LoginRequiredMixin, GroupRequiredMixin, FormView):
    """ Admin data entry of a Teas or Bar transaction """
    group_required = 'Pos'
    form_class = PosDataEntryForm
    template_name = 'pos/data_entry.html'

    def get_initial(self):
        initial = super().get_initial()
        initial['item_type'] = ItemType.TEAS
        initial['total'] = 60
        initial['date'] = self.request.session.get('pos_date', datetime.now())
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'POS admin - create entry'
        return context

    def post(self, request, *args, **kwargs):
        if 'exit' in request.POST:
            return redirect('pos_admin')
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        person = Person.objects.get(id=form.cleaned_data['person_id'])
        total = (Decimal(int(form.cleaned_data['total'])) / 100).quantize(Decimal('.01'))
        item_type = ItemType.objects.get(id=form.cleaned_data['item_type'])
        trans = Transaction(
            creation_date=form.cleaned_data['date'],
            creator=self.request.user,
            person=person,
            terminal=0,
            item_type=item_type,
            total=total,
            billed=False,
            cash=False,
            complimentary=False,
            split=False,
            attended=True,
        )
        trans.save()
        self.request.session['pos_date'] = form.cleaned_data['date']
        messages.success(self.request, f"{total} charged to {person.fullname}'s {item_type.description}")
        return redirect(self.request.path)


class VisitorsDataEntryView(LoginRequiredMixin, GroupRequiredMixin, FormView):
    """ Admin data entry of a visitor """
    group_required = 'Pos'
    form_class = VisitorsDataEntryForm
    template_name = 'pos/data_entry.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['admin'] = True
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Visitors admin - create entry'
        return context

    def post(self, request, *args, **kwargs):
        if 'exit' in request.POST:
            return redirect('pos_admin')
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        member = Person.objects.get(id=form.cleaned_data['person_id'])
        result = VisitorCreateView.process_form(form, member.id)
        messages.success(self.request, f"Member: {member.fullname} " + result)
        return redirect(self.request.path)