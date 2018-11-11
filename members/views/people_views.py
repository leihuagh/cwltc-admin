import logging
from django.shortcuts import redirect, get_object_or_404, render
from django_tables2 import SingleTableView
from django.contrib import messages
from django.views.generic import TemplateView
from braces.views import StaffuserRequiredMixin
from members.models import Person, Subscription, Settings, Group
from members.excel import export_people
from members.filters import SubsFilter, JuniorFilter
from members.tables import SubsTable, PersonTable, ApplicantTable
from members.services import person_resign
from mysite.common import Button

stdlogger = logging.getLogger(__name__)


def permission_denied(view, request):
    """
    Redirect to login with error message when user has not got staff permission
    """
    messages.error(request, "You are logged in as {} but don't have permission to access {}.\
    Would you like to login as a different user?".format(request.user, request.path))
    return redirect('login')


class PeopleTableView(StaffuserRequiredMixin, SingleTableView):
    # http://stackoverflow.com/questions/13611741/django-tables-column-filtering/15129259#15129259
    raise_exception = permission_denied
    filter_class = None
    juniors = False
    parents = False
    members = False
    group = None
    title = ''
    filter = None
    template_name = 'members/person_table.html'
    table_pagination = {"per_page": 10000}

    # TODO make loader work with tests

    # def dispatch(self, request, *args, **kwargs):
    #     if request.session.get('slow_url', '') == request.path:
    #         request.session['slow_url'] = ''
    #         return super().dispatch(request, *args, **kwargs)
    #     else:
    #         request.session['slow_url'] = request.path
    #         return render(request, 'members/loading.html', {'url':request.build_absolute_uri()})

    def get_table_data(self):
        """
        Perform the query and do the filtering
        """
        if self.group:
            return self.group.person_set.all().select_related('sub__membership').orderby('last_name')
        if not self.filter_class:
            return Person.objects.all().select_related('sub__membership').order_by('last_name')
        year = Settings.current_year()
        qs = Subscription.objects.filter(
            active=True
        ).select_related('membership').select_related('person_member')

        if self.juniors or self.parents:
            qs = qs.exclude(membership__is_adult=True).filter(person_member__state=Person.ACTIVE)

        # set defaults for first time
        data = self.request.GET.copy()
        if len(data) == 0:
            data['paid'] = True
            data['year'] = year
            data['state'] = Person.ACTIVE
        self.filter = self.filter_class(data, qs, request=self.request)

        if self.parents:
            kids = self.filter.qs.values_list('person_member__linked_id')
            return Person.objects.filter(id__in=kids)
        return self.filter.qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter'] = self.filter
        context['members'] = self.members
        context['juniors'] = self.juniors
        context['parents'] = self.parents
        context['table_title'] = self.title
        context['actions'] = Actions.default_actions()
        return context

    def post(self, request, *args, **kwargs):
        return Actions.execute_action(request, self.group)


class MembersTableView(PeopleTableView):
    table_class = SubsTable
    model = Subscription
    members = True
    filter_class = SubsFilter
    title = 'Members'


class JuniorsTableView(PeopleTableView):
    table_class = SubsTable
    model = Subscription
    juniors = True
    filter_class = JuniorFilter
    title = 'Juniors'


class ParentsTableView(PeopleTableView):
    table_class = PersonTable
    model = Person
    parents = True
    filter_class = JuniorFilter
    title = 'Parents'


class AllPeopleTableView(PeopleTableView):
    table_class = PersonTable
    model = Person
    title = 'All people'


class GroupPeopleTableView(PeopleTableView):
    table_class = PersonTable
    model = Person
    group_id = ''

    def dispatch(self, request, *args, **kwargs):
        self.group_id = self.kwargs.pop('pk', '')
        return super().dispatch(request, *args, **kwargs)

    def get_table_data(self):
        group = get_object_or_404(Group, pk=self.group_id)
        self.title = group.description or 'Group'
        return group.person_set.all().select_related('sub__membership').order_by('last_name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['actions'].extend(Actions.group_actions())
        context['buttons'] = Actions.group_buttons()
        return context

    def post(self, request, *args, **kwargs):
        self.group = get_object_or_404(Group, id=self.group_id)
        return super().post(request, *args, **kwargs)


class AppliedTableView(StaffuserRequiredMixin, SingleTableView):
    """
    List of people who have applied to join
    """
    template_name = 'members/generic_table.html'
    table_pagination = {"per_page": 10000}
    table_class = ApplicantTable

    def get_queryset(self):
        return Person.objects.filter(state=Person.APPLIED).order_by('date_joined')

    def get_context_data(self, **kwargs):
        context = super(AppliedTableView, self).get_context_data(**kwargs)
        context['title'] = 'Applicants'
        return context


class ResignView(StaffuserRequiredMixin, TemplateView):
    """ Confirm  a list of people to resign """
    template_name = 'members/people_resign.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['people'] = self.get_people(self.request)
        return context

    def get_people(self, request):
        id_list = request.session.get('selected_people_ids', [])
        return Person.objects.filter(pk__in=id_list).order_by('first_name', 'last_name')

    def post(self, request, **kwargs):
        people = self.get_people(request)
        if 'resign' in request.POST:
            count = 0
            for person in people:
                try:
                    person_resign(person)
                    count += 1
                except:
                    pass
            messages.success(self.request, f'{count} of {len(people)} people marked as resigned')
        else:
            messages.success(self.request, f'Resignation of {len(people)} cancelled')
        return redirect('home')


class Actions:
    """
    Handle actions that apply to a list of selected people
    Actions that start with x_ are functions that get called.
    Others are views to redirect to
    """

    @staticmethod
    def default_actions():
        return [('No action', 'none'),
                ('Send mail', 'email-selection'),
                ('Add to group', 'group-add-list'),
                ('Export', 'x_export'),
                ('Invoice', 'x_invoice-generate')]

    @staticmethod
    def group_actions():
        return [('Add selected people', 'x_group_add_people'),
                ('Remove selected people', 'x_group_remove_people'), ]

    @staticmethod
    def group_buttons():
        return [Button('Delete group', 'x_group_delete'),
                Button('Clear group', 'x_group_clear'), ]

    @staticmethod
    def execute_action(request, group=None):
        request.session['source_path'] = request.META['HTTP_REFERER']
        id_list = request.POST.getlist('selection')
        action = request.POST.get('action', 'none')
        if action is 'none':
            for key in request.POST:
                if key[:2] == 'x_':
                    action = key
                    break
            else:
                return redirect(request.session['source_path'])
        if action[:2] == 'x_':
            method = getattr(Actions, action[2:])
            people = Person.objects.filter(pk__in=id_list)
            if group:
                return method(group, people) if 'people' in action else method(group)
            else:
                return method(people)
        request.session['selected_people_ids'] = id_list
        return redirect(action)

    @staticmethod
    def export(people):
        people.select_related('sub').select_related('sub__membership')
        sheet_name = 'People'
        return export_people(sheet_name, people)

    @staticmethod
    def group_delete(group):
        group.delete()
        return redirect('group-list')

    @staticmethod
    def group_clear(group):
        group.person_set.clear()
        return redirect('group-list')

    @staticmethod
    def group_add_people(group, people):
        for person in people:
            person.groups.add(group)
            person.save()
        return redirect('group-detail', pk=group.id)

    @staticmethod
    def group_remove_people(group, people):
        for person in people:
            person.groups.remove(group)
        return redirect('group-detail', pk=group.id)
