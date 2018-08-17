import json
import logging
from datetime import datetime
from django.core.serializers import serialize
from django.http import HttpResponse, JsonResponse, HttpResponseRedirect
from django.views.generic import TemplateView, FormView
from django.urls import reverse
from django.urls.exceptions import NoReverseMatch
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.hashers import check_password
from django.shortcuts import redirect, render
from django.utils import timezone
from django_tables2 import SingleTableView
from braces.views import GroupRequiredMixin
from public.views import RegisterView, RegisterTokenView, ConsentTokenView
from mysite.common import Button
from members.models import VisitorFees, Settings
from events.views import EventRegisterView
from pos.tables import *
from pos.forms import TerminalForm, VisitorForm, DobForm
from pos.services import create_transaction_from_receipt, build_pos_array, PosServicesError

LONG_TIMEOUT = 120000
SHORT_TIMEOUT = 30000
PING_TIMEOUT = 60000

stdlogger = logging.getLogger(__name__)


class SetTerminalView(LoginRequiredMixin, GroupRequiredMixin, FormView):
    template_name = 'pos/set_terminal.html'
    form_class = TerminalForm
    group_required = 'Pos'

    def get_initial(self):
        initial = super().get_initial()
        system, terminal = read_cookie(self.request)
        # code for smooth migration of cookie data from layout id to string
        if system and is_integer_string(system):
            system = 'bar'
        initial.update({'system': system,
                        'terminal': terminal})
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Start POS on this screen"
        return context

    def post(self, request, *args, **kwargs):
        if 'disable' in request.POST:
            response = HttpResponseRedirect(reverse('pos_admin'))
            response.delete_cookie('pos')
            return response
        if 'start' in request.POST:
            terminal = request.POST['terminal']
            system = request.POST['system']
            response = HttpResponseRedirect(reverse('pos_start'))
            max_age = 10 * 365 * 24 * 60 * 60
            response.set_cookie('pos', system + ';' + terminal, max_age=max_age)
            return response
        return redirect('pos_admin')


class DisabledView(LoginRequiredMixin, TemplateView):
    template_name = 'pos/disabled.html'


class StartView(LoginRequiredMixin, TemplateView):
    """ Member login or attended mode selection """
    template_name = 'pos/start.html'
    system = ''

    def get(self, request, *args, **kwargs):
        request.session['person_id'] = None
        request.session['app'] = None
        request.session['attended'] = False
        self.system, request.session['terminal'] = read_cookie(request)
        if self.system:
            return super().get(request, *args, **kwargs)
        return redirect('pos_disabled')

    def post(self, request, *args, **kwargs):
        if 'attended' in request.POST:
            #
            apps = PosApp.objects.filter(main_system=False, enabled=True,
                                         layout__item_type=ItemType.BAR)
            if len(apps) > 0:
                request.session['app'] = apps[0]
                request.session['attended'] = True
                return redirect('pos_run')
            return redirect('pos_start')

        for key, value in request.POST.items():
            if key[0:4] == 'app_':
                app = PosApp.objects.get(id=key[4:])
                request.session['app'] = PosApp.objects.get(id=key[4:])
                return redirect('pos_user')
            if key[0:6] == 'event_':
                parts = key[6:].split('.')
                request.session['app'] = PosApp.objects.filter(event_id=parts[0])[0]
                return redirect('pos_user')

        return redirect('pos_start')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        apps = PosApp.objects.filter(main_system=self.system == 'main', enabled=True).order_by('index')
        context['apps'] = apps
        if len(apps) == 1 and apps[0].is_bar_app():
            context['is_bar'] = True
            context['attended'] = apps[0].attended
        context['message'] = self.request.session.get('message', "")
        self.request.session['message'] = ""
        context['timeout'] = LONG_TIMEOUT
        context['ping_url'] = reverse('pos_ajax_ping')
        return context


class MemberSelectView(LoginRequiredMixin, TemplateView):
    """ Select member for transactions view"""
    template_name = 'pos/select_member.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter'] = 'members'
        return add_context(context, self.request)

    def post(self, request, *args, **kwargs):
        return redirect('pos_transactions_person', person_id=request.POST['person_id'])


class GetUserView(LoginRequiredMixin, TemplateView):
    """ User identification """
    template_name = 'pos/get_user.html'

    def post(self, request, *args, **kwargs):
        if request.POST['person_id']:
            request.session['person_id'] = request.POST['person_id']
            if int(request.POST['person_id']) > 0:
                person = Person.objects.get(pk=request.POST['person_id'])
                if person.auth_id:
                    return redirect('pos_password')
                else:
                    if person.dob:
                        age = person.age_for_membership()
                        if age <= 10:
                            return redirect('pos_start')
                        if age > 13:
                            return redirect('pos_register')
                        return redirect('pos_dob')
                return redirect('pos_register')
            else:
                # Complimentary sale, id = -1
                return redirect('pos_password')
        return redirect('pos_start')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter'] = 'members' if self.request.session['app'].allow_juniors else 'adults'
        return add_context(context, self.request)


class GetPasswordView(LoginRequiredMixin, TemplateView):
    """ User's password or PIN """
    template_name = 'pos/get_password.html'

    def post(self, request, *args, **kwargs):

        if request.POST['submit']:
            if request.session['person_id']:  # There is a bug where this is None
                id = int(request.session['person_id'])
                if id > 0:
                    try:
                        person = Person.objects.get(pk=request.session['person_id'])
                    except Person.DoesNotExist:
                        return redirect('pos_start')

                    authorised = False
                    pin = request.POST['pin']
                    if pin and check_password(pin, person.pin):
                        authorised = True
                    else:
                        user = User.objects.get(pk=person.auth_id)
                        password = request.POST['password']
                        if password and user.check_password(password):
                            authorised = True
                    if authorised:
                        # Redirect to selected app
                        app = request.session.get('app', None)
                        if app:
                            if app.event:
                                return redirect('pos_event_register', pk=app.event.id)
                            try:
                                url = reverse(app.view_name)
                                return redirect(url)
                            except NoReverseMatch:
                                request.session['message'] = f'Bad view name for app {app}'
                                return redirect('pos_start')

                        # if request.session['layout'].item_type.id == ItemType.VISITORS:
                        #     return redirect('pos_visitors_person', person_id=person.id)
                        # return redirect(menu_url(request))
                    request.session['message'] = "Incorrect PIN or password"

                else:  # Complimentary Bar sale
                    if request.POST['pin'] == str(datetime.now().year):
                        return redirect('pos_run')
        return redirect('pos_start')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return add_context(context, self.request)


def ajax_validate_person(request):
    id = request.POST['id']
    person = Person.objects.get(pk=id)
    if person.auth_id:
        return redirect('pos_password')
    else:
        if person.dob:
            age = person.age_for_membership()
            if age <= 10:
                return redirect('pos_start')
            if age > 13:
                return redirect('pos_register')
            return redirect('pos_dob')
    return redirect('pos_register')


def ajax_validate_user(request):
    authorised = False
    id = request.POST['id']
    request.session['person_id'] = id
    pin = request.POST['PIN']
    person = Person.objects.get(pk=id)
    if pin and check_password(pin, person.pin):
        authorised = True
    else:
        user = User.objects.get(pk=person.auth_id)
        password = request.POST['password']
        if password and user.check_password(password):
            authorised = True
    if authorised:
        # Redirect to selected app
        app = request.session.get('app', None)
        if app:
            if app.event:
                return redirect('pos_event_register', pk=app.event.id)
            try:
                url = reverse(app.view_name)
                return redirect(url)
            except NoReverseMatch:
                request.session['message'] = f'Bad view name for app {app}'
                return redirect('pos_start')


class GetDobView(LoginRequiredMixin, FormView):
    """ Validate junior by checking the date of birth """

    template_name = 'pos/dob.html'
    form_class = DobForm

    def form_valid(self, form):
        dob = form.cleaned_data['dob']
        id = self.request.session.get('person_id', None)
        person = Person.objects.get(pk=id)
        if person.dob == dob:
            return redirect(reverse('pos_visitors_person', kwargs={'person_id': id}))
        self.request.session['message'] = "Incorrect date of birth"
        return redirect('pos_start')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return add_context(context, self.request)


class PosRegisterView(LoginRequiredMixin, RegisterView):
    """ When user is not registered we use the public
    registration form and override some things """
    template_name = 'pos/register.html'
    re_register = False

    def get_initial(self):
        initial = super(PosRegisterView, self).get_initial()
        self.person = Person.objects.get(pk=self.request.session['person_id'])
        initial['first_name'] = self.person.first_name
        initial['last_name'] = self.person.last_name
        return initial

    def get_form_kwargs(self):
        """ set form kwargs so the name fields are hidden """
        kwargs = super().get_form_kwargs()
        kwargs.update({'hide_name': True})
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['buttons'] = [Button('Back', 'back', css_class='btn-success btn-lg'),
                              Button('Next', 'register', css_class='btn-success btn-lg')]
        return add_context(context, self.request)

    def post(self, request, *args, **kwargs):
        if 'back' in request.POST:
            return redirect('pos_start')
        if self.re_register:
            person = Person.objects.get(pk=self.request.session['person_id'])
            person.unregister()
        return super().post(request, args, kwargs)

    def get_success_url_name(self):
        return 'pos_register_token'

    def get_failure_url_name(self):
        return 'pos_start'


class PosRegisterTokenView(LoginRequiredMixin, RegisterTokenView):
    """
    Get username, PIN and password
    """
    template_name = 'pos/register_token.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return add_context(context, self.request)

    def get_success_url_name(self, **kwargs):
        return 'pos_consent_token'

    def get_already_registered_url_name(self):
        return 'pos_password'


class PosConsentView(LoginRequiredMixin, ConsentTokenView):
    template_name = 'pos/consent.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['pos'] = True
        return add_context(context, self.request)

    def get_success_url(self):
        return reverse(menu_url(self.request))


class MemberMenuView(LoginRequiredMixin, TemplateView):
    """ Menu of options for members
    This has a shorter timeout, defined in the url """
    template_name = 'pos/menu.html'
    timeout = LONG_TIMEOUT

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['attended'] = self.request.session['app'].attended and has_attended_cookie(self.request)
        return add_context(context, self.request, self.timeout)

    def post(self, request, *args, **kwargs):
        """ Attended mode is enabled if session['app'].attended is True and cookie 'attended' is 'on' """
        state = 'off'
        if 'attended_on' in request.POST:
            state = 'on'
            request.session['app'].attended = True
        elif 'attended_off' in request.POST:
            request.session['app'].attended = False
        request.session['app'].save()
        response = HttpResponseRedirect(reverse('pos_start'))
        max_age = 8 * 60 * 60 # 8 hours lifetime
        response.set_cookie('attended', state, max_age=max_age)
        return response


class PosView(LoginRequiredMixin, TemplateView):
    """ The main POS screen """
    template_name = 'pos/pos.html'

    def get_context_data(self, **kwargs):
        context = super(PosView, self).get_context_data(**kwargs)
        app = self.request.session['app']
        layout = app.layout
        context['rows'], used_items = build_pos_array(layout)
        context['items_url'] = reverse('pos_ajax_items')
        context['post_url'] = reverse('pos_run')
        context['exit_url'] = reverse('pos_menu')
        context['terminal'] = self.request.session['terminal']
        context = add_context(context, self.request)
        if app.attended and has_attended_cookie(self.request):
            if app.is_bar_app():
                context['exit_url'] = reverse('pos_start')
            else:
                context['exit_url'] = reverse('pos_menu')
            context['is_attended'] = 'true' # javascript true
            context['full_name'] = 'Attended mode'
        else:
            context['is_attended'] = 'false' # javascript false
        return context

    def post(self, request, *args, **kwargs):
        """ Write transaction to database"""

        if request.is_ajax():
            receipt = json.loads(request.body)
            pay_record = receipt.pop()
            system, terminal = read_cookie(request)
            layout_id = request.session['app'].layout_id
            try:
                trans = create_transaction_from_receipt(request.user.id,
                                                        terminal,
                                                        layout_id,
                                                        receipt,
                                                        pay_record['total'],
                                                        pay_record['people'],
                                                        request.session['attended']
                                                        )
                request.session['last_person'] = trans[0]
                request.session['last_total'] = trans[1]
            except PosServicesError:
                return HttpResponse(reverse('Error'))
            if self.request.session['attended']:
                return HttpResponse(reverse('pos_start'))
            else:
                return HttpResponse(reverse('pos_menu_timeout'))
        # should not get here - all posts are ajax
        return redirect('pos_start')


class VisitorBookView(LoginRequiredMixin, SingleTableView):
    """
    List visitors book
    This can be for all entries or for a specific person (not necessary the one logged in)
    """
    model = VisitorBook
    table_class = VisitorBookTable
    template_name = 'pos/visitor_book.html'
    table_pagination = {'per_page': 10}
    id = None
    all_entries = False

    def get_table_data(self):
        self.id = self.kwargs.get('person_id', None)
        if self.id:
            qs = VisitorBook.objects.filter(member_id=self.id)
        else:
            qs = VisitorBook.objects.all()
        return list(qs.order_by('-date', '-id').select_related('visitor').select_related('member__membership'))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['all_entries'] = self.all_entries
        if self.id:
            person = Person.objects.get(pk=self.id)
            context['person'] = person
        context['timeout_url'] = reverse('pos_start')
        context['timeout'] = LONG_TIMEOUT
        return add_context(context, self.request)


class VisitorMenuView(LoginRequiredMixin, TemplateView):
    template_name = 'pos/visitor_menu.html'
    form_class = VisitorForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return add_context(context, self.request)


class VisitorCreateView(LoginRequiredMixin, FormView):
    """
    Add an adult or junior visitor to the visitor book
    """
    template_name = 'pos/visitor_create.html'
    form_class = VisitorForm
    junior = False

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        self.person = Person.objects.get(pk=self.request.session['person_id'])
        # if not self.admin:
        kwargs.update({'person_id': self.person.id,
                       'junior': self.junior
                       },
                      )
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['has_existing'] = len(context['form'].fields['visitors'].choices) > 1
        context['junior'] = self.junior
        return add_context(context, self.request)

    def form_invalid(self, form):
        return super().form_invalid(form)

    def form_valid(self, form):
        member_id = form.cleaned_data['person_id']
        if not member_id:
            member_id = self.request.session['person_id']
        visitor_id = form.cleaned_data.get('visitors')
        fees = VisitorFees.objects.filter(year=Settings.current_year())
        fee = 6
        if fees:
            fee = fees[0].junior_fee if self.junior else fees[0].adult_fee
        if visitor_id == "0":
            # user entered name - check its not a dup
            existing_visitors = Visitor.objects.filter(first_name=form.cleaned_data['first_name'],
                                                       last_name=form.cleaned_data['last_name'],
                                                       junior=self.junior)
            if existing_visitors.count() > 0:
                visitor = existing_visitors[0]
            else:
                visitor = Visitor.objects.create(first_name=form.cleaned_data['first_name'],
                                                 last_name=form.cleaned_data['last_name'],
                                                 junior=self.junior)
            visitor_id = visitor.id
        entry = VisitorBook.objects.create(
            member_id=member_id,
            visitor_id=visitor_id,
            fee=fee,
            billed=False
        )
        return redirect('pos_visitors_person', person_id=member_id)


class LookupMemberView(LoginRequiredMixin, TemplateView):
    template_name = 'pos/lookup_member.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return add_context(context, self.request)


class PosEventRegisterView(EventRegisterView):
    template_name = 'pos/event_register.html'

    def post(self, request, *args, **kwargs):
        super().post(request, args, kwargs)
        return redirect('pos_event_register', pk=self.event.id)


def ajax_items_view(request):
    """ responds to ajax request for item list"""
    data = serialize('json', Item.objects.all())
    return JsonResponse(data, safe=False)


def ajax_ping_view(request):
    """ responds to keep alive from pos"""
    terminal = request.POST.get('terminal', None)
    if terminal:
        records = PosPing.objects.filter(terminal=terminal)
        if records:
            records[0].time = timezone.now()
            records[0].save()
        else:
            record = PosPing.objects.create(terminal=terminal, time=timezone.now())
        return HttpResponse('OK')
    return HttpResponse('Bad terminal')


def read_cookie(request):
    if 'pos' in request.COOKIES:
        values = request.COOKIES['pos'].split(';')
        return values[0], values[1]
    else:
        return None, None


def has_attended_cookie(request):
    value = request.COOKIES.get('attended', None)
    return value and value == 'on'


def menu_url(request):
    if request.session['app'].is_visitors_app():
        return 'pos_visitors_all'
    return 'pos_menu'


def add_context(context, request, timeout=LONG_TIMEOUT):
    id = request.session.get('person_id', None)
    if id and int(id) != -1:
        person = Person.objects.get(pk=id)
        context['person_id'] = int(id)
        context['person'] = person
        context['full_name'] = person.fullname
        if person.auth:
            context['admin'] = person.auth.is_staff or person.auth.groups.filter(name='Pos').exists()
    else:
        context['person_id'] = -1
        context['full_name'] = 'Complimentary'
    context['timeout_url'] = reverse('pos_start')
    context['timeout'] = timeout
    return context


def is_integer_string(s):
    try:
        int(s)
        return True
    except ValueError:
        return False