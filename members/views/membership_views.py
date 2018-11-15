import logging
from django.views.generic import CreateView, UpdateView

from django.urls import reverse_lazy
from braces.views import StaffuserRequiredMixin
from django_tables2 import SingleTableView

from members.models import Membership
from members.tables import MembershipTable
from members.forms import MembershipForm


stdlogger = logging.getLogger(__name__)


class MembershipTableView(StaffuserRequiredMixin, SingleTableView):
    model = Membership
    table_class = MembershipTable
    template_name = 'members/generic_table.html'
    table_pagination = {"per_page": 10000}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Membership categories'
        return context


class MembershipCreateView(StaffuserRequiredMixin, CreateView):
    model = Membership
    template_name = 'members/generic_crispy_form_well.html'
    form_class = MembershipForm
    success_url = reverse_lazy('membership-list')


class MembershipUpdateView(StaffuserRequiredMixin, UpdateView):
    model = Membership
    template_name = 'members/generic_crispy_form.html'
    form_class = MembershipForm
    success_url = reverse_lazy('membership-list')
