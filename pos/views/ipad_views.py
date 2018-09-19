import json
import logging
from django.core.serializers import serialize
from django.http import HttpResponse, JsonResponse, HttpResponseRedirect, HttpResponseBadRequest
from django.views.generic import TemplateView, FormView
from django.urls import reverse
from django.contrib.auth.mixins import LoginRequiredMixin

from django.shortcuts import redirect
from django.utils.safestring import mark_safe
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
            response.set_cookie('terminal', terminal, max_age=max_age)
            return response
        return redirect('pos_admin')


class DisabledView(LoginRequiredMixin, TemplateView):
    template_name = 'pos/disabled.html'


class OfflineView(LoginRequiredMixin, TemplateView):
    template_name = 'pos/offline.html'


class StartView(LoginRequiredMixin, TemplateView):
    """ Member login or attended mode selection """
    template_name = 'pos/start.html'
    system = ''
    person_id = None

    def dispatch(self, request, *args, **kwargs):
        self.person_id = kwargs.pop('person_id', None)
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        request.session['person_id'] = None
        request.session['app'] = None
        request.session['attended'] = False
        self.system, request.session['terminal'] = read_cookie(request)
        if self.system:
            return super().get(request, *args, **kwargs)
        return redirect('pos_disabled')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        apps = PosApp.objects.filter(enabled=True, layout__item_type = ItemType.BAR)
        if apps:
            context['bar_app'] = apps[0]
        apps = PosApp.objects.filter(enabled=True, layout__item_type = ItemType.TEAS)
        if apps:
            context['teas_app'] = apps[0]
        context['apps'] = PosApp.objects.filter(enabled=True, layout_id=None)
        context['is_bar'] = self.system == 'bar'
        context['urls'] = mark_safe(json.dumps({
            'ping': reverse('pos_ajax_ping'),
            'items': reverse('pos_ajax_items'),
            'start': reverse('pos_start'),
            'redirect': reverse('pos_redirect', kwargs={'view': 'xxxx', 'person_id': '9999'}),
            'event': reverse('pos_event_register', kwargs={'pk': '9999'}),
            'adults': reverse('ajax-adults'),
            'password': reverse('ajax-password'),
            'postCode': reverse('ajax-postcode'),
            'setPin': reverse('ajax-set-pin'),
            'transactions': reverse('pos_transactions'),
            'transactionsPerson': reverse('pos_transactions_person', kwargs={'person_id': '9999'}),
            'transactionsComp': reverse('pos_transactions_comp'),
            'transactionsCash': reverse('pos_transactions_cash'),
        }))
        context['rows'], _ = build_pos_array()
        return context

    def post(self, request, *args, **kwargs):
        """ Write transaction to database"""

        if request.is_ajax():
            #return HttpResponse('error')

            receipt = json.loads(request.body)
            pay_record = receipt.pop()
            creation_date = datetime.fromtimestamp(pay_record['stamp']/1000, tz = timezone.get_current_timezone())
            system, terminal = read_cookie(request)
            existing = Transaction.objects.filter(creation_date=creation_date, terminal=terminal)
            if not existing:
                try:
                    trans = create_transaction_from_receipt(request.user.id,
                                                            pay_record['terminal'],
                                                            pay_record['layout_id'],
                                                            receipt,
                                                            pay_record['total'],
                                                            pay_record['people'],
                                                            pay_record['attended'],
                                                            creation_date=creation_date
                                                            )
                except PosServicesError:
                    return HttpResponse(status=500)
                return HttpResponse(f'Saved;{trans[0]};{trans[1]}')
            return HttpResponse(f'Exists;{existing[0].id};{existing[0].total}')
        # should not get here - all posts are ajax
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
    """ Overirde the standard event register form"""
    template_name = 'pos/event_register.html'

    def get_template_names(self):
        return ['pos/event_register.html']

    def post(self, request, *args, **kwargs):
        self.person = Person.objects.get(id=self.request.session['person_id'])
        super().post(request, args, kwargs)
        return redirect('pos_event_register', pk=self.event.id)


def pos_redirect(request, view, person_id):
    return redirect(view, person_id=person_id)


def ajax_items(request):
    """ Responds to ajax request for item list"""

    if request.is_ajax() and request.method == 'GET':
        dict = {}
        dict['items'] = serialize('json', Item.objects.all())
        dict['colours'] = serialize('json', Colour.objects.all())
        layouts = Layout.objects.all()
        layout_dict = {}
        for layout in layouts:
            locs_dict ={}
            locs = Location.objects.filter(layout_id=layout.id)
            for loc in locs:
                key = f'#btn{loc.row}{loc.col}'
                if loc.col == 0:
                    locs_dict[key] = loc.description
                else:
                    locs_dict[key] = loc.item_id
            layout_dict[layout.id] = json.dumps(locs_dict)
        dict['layouts'] = layout_dict
        return JsonResponse(dict, safe=False)
    return HttpResponseBadRequest

def ajax_colours(request):
    """ Responds to ajax request for item colours """
    if request.is_ajax() and request.method == 'GET':
        data = serialize('json', Colour.objects.all())
        return JsonResponse(data, safe=False)
    return HttpResponseBadRequest


def ajax_locations(request):
    """ Return a dictionary of locations that have an associated item """
    if request.is_ajax() and request.method == 'GET':
        id = request.GET.get('layout_id', None)
        if id:
            dict = {}
            locations = Location.objects.filter(layout_id=id)
            for loc in locations:
                key = f'#btn{loc.row}{loc.col}'
                if loc.col == 0:
                    dict[key] = loc.description
                else:
                    dict[key] = loc.item_id
            return JsonResponse(dict)
    return HttpResponseBadRequest


def ajax_ping(request):
    """ responds to keep alive from pos"""
    if request.is_ajax() and request.method == 'POST':
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
    return HttpResponseBadRequest


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
    return 'pos_start_person'


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