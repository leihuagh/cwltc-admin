import logging
from django.urls import reverse
from django.views.generic import ListView, CreateView, FormView
from django_tables2 import SingleTableView
from braces.views import StaffuserRequiredMixin
from members.models import Group, Person
from members.tables import GroupTable
from members.forms import GroupForm, GroupAddPersonForm

stdlogger = logging.getLogger(__name__)


class GroupCreateView(StaffuserRequiredMixin, CreateView):
    model = Group
    form_class = GroupForm
    template_name = 'members/generic_crispy_form.html'

    def get_success_url(self):
        return reverse('group-list')


class GroupTableView(StaffuserRequiredMixin, SingleTableView):
    template_name = 'members/generic_table.html'
    table_pagination = {"per_page": 10000}
    table_class = GroupTable

    def get_queryset(self):
        return Group.objects.all().order_by('slug')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['table_title'] = 'Groups'
        return context


class GroupAddPersonView(StaffuserRequiredMixin, FormView):
    form_class = GroupAddPersonForm
    template_name = 'members/crispy_tile.html'
    person = None
    group = None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        self.person = Person.objects.get(pk=self.kwargs['person_id'])
        context['person'] = self.person
        context['app_title'] = 'Add person to group'
        return context

    def form_valid(self, form):
        person = Person.objects.get(pk=self.kwargs['person_id'])
        self.group = form.cleaned_data['group']
        person.groups.add(self.group)
        return super().form_valid(form)

    def get_success_url(self):
        if self.group:
            return reverse('group-detail', kwargs={'pk': self.group.id})
        return reverse('person-detail', kwargs={'pk': self.person.id})

