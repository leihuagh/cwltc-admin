import json
import logging
from datetime import datetime
from django.core.serializers import serialize
from django.http import HttpResponse, JsonResponse, HttpResponseRedirect
from django.views.generic import TemplateView, FormView
from django.urls import reverse, reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.hashers import check_password
from django.shortcuts import redirect
from django.utils import timezone
from django_tables2 import SingleTableView
from braces.views import GroupRequiredMixin
from public.views import RegisterView, RegisterTokenView, ConsentTokenView
from mysite.common import Button
from members.models import VisitorFees, Settings
from pos.tables import *
from pos.forms import TerminalForm, VisitorForm
from pos.services import create_transaction_from_receipt, build_pos_array

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
        layout, terminal = read_cookie(self.request)
        initial.update({'layout': layout,
                        'terminal': terminal})
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Start POS on this screen"
        context['layouts'] = Layout.objects.all()
        return context

    def post(self, request, *args, **kwargs):
        if 'disable' in request.POST:
            response = HttpResponseRedirect(reverse('pos_admin'))
            response.delete_cookie('pos')
            return response
        if 'start' in request.POST:
            terminal = request.POST['terminal']
            layout_id = request.POST['layout']
            layout = Layout.objects.get(pk=layout_id)
            if layout.item_type_id == ItemType.BAR:
                start_screen = 'pos_start'
            else:
                start_screen = 'pos_select_app'
            request.session['start_screen'] = start_screen
            response = HttpResponseRedirect(reverse(start_screen))
            max_age = 10 * 365 * 24 * 60 * 60
            response.set_cookie('pos', layout_id + ';' + terminal, max_age=max_age)
            request.session['layout'] = layout
            return response
        return redirect('pos_admin')


class DisabledView(LoginRequiredMixin, TemplateView):
    template_name = 'pos/disabled.html'


class StartView(LoginRequiredMixin, TemplateView):
    """ Member login or attended mode selection """
    template_name = 'pos/start.html'

    def get(self, request, *args, **kwargs):
        request.session['person_id'] = None
        layout_id, request.session['terminal'] = read_cookie(request)
        if layout_id:
            request.session['layout'] = Layout.objects.get(id=layout_id)
            if request.session['layout'].item_type.id != ItemType.BAR:
                return redirect('pos_select_app')
            return super().get(request, *args, **kwargs)
        return redirect('pos_disabled')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['layout'] = self.request.session['layout']
        context['message'] = self.request.session.get('message', "")
        self.request.session['message'] = ""
        context['timeout'] = PING_TIMEOUT
        context['ping_url'] = reverse('pos_ajax_ping')
        return context

    def post(self, request, *args, **kwargs):
        if 'login' in request.POST:
            request.session['attended'] = False
            return redirect('pos_user')
        elif 'attended' in request.POST:
            request.session['attended'] = True
            return redirect('pos_run')
        return redirect('pos_start')


class SelectAppView(StartView):
    """ Choose Cafe or Vistors book """
    template_name = 'pos/select_app.html'

    def post(self, request, *args, **kwargs):
        if 'layout' in request.POST:
            return redirect('pos_user')
        elif 'visitors' in request.POST:
            visitors = visitors_layout()
            request.session['layout'] = visitors
            return redirect('pos_visitors_all')
        elif 'lookup' in request.POST:
            return redirect('pos_lookup_member')

        return redirect('pos_select_app')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['visitors'] = visitors_layout()
        return context


def visitors_layout():
    visitors = Layout.objects.filter(name="Visitors")
    if visitors:
        return visitors[0]
    return None


def read_cookie(request):
    if 'pos' in request.COOKIES:
        values = request.COOKIES['pos'].split(';')
        return values[0], values[1]
    else:
        return None, None


def restart_url(request):
    if request.session['layout'].item_type.id == ItemType.BAR:
        return 'pos_start'
    return 'pos_select_app'


def menu_url(request):
    if request.session['layout'].item_type.id == ItemType.VISITORS:
        return 'pos_visitors_all'
    return 'pos_menu'


class MemberSelectView(LoginRequiredMixin, TemplateView):
    """ Select member for transactions view"""
    template_name = 'pos/select_member.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['timeout_url'] = reverse(restart_url(self.request))
        context['timeout'] = LONG_TIMEOUT
        return context

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
                return redirect('pos_register')
            else:
                # Complimentary sale, id = -1
                return redirect('pos_password')
        return redirect(restart_url(request))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['timeout_url'] = reverse(restart_url(self.request))
        context['timeout'] = LONG_TIMEOUT
        return context


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
                        return redirect(restart_url(request))

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
                        if request.session['layout'].item_type.id == ItemType.VISITORS:
                            return redirect('pos_visitors_person', person_id=person.id)
                        return redirect(menu_url(request))
                    request.session['message'] = "Incorrect PIN or password"

                else:  # Complimentary
                    if request.POST['pin'] == str(datetime.now().year):
                        return redirect('pos_run')
        return redirect(restart_url(request))

    def get_context_data(self, **kwargs):
        context = super(GetPasswordView, self).get_context_data(**kwargs)
        id = self.request.session.get('person_id', None)
        if id:
            person = Person.objects.get(pk=id)
            context['person_id'] = int(id)
            context['full_name'] = person.fullname
        else:
            context['full_name'] = 'Complimentary'
        context['timeout_url'] = reverse(restart_url(self.request))
        context['timeout'] = LONG_TIMEOUT
        return context


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
        context['person'] = self.person
        context['timeout_url'] = reverse(restart_url(self.request))
        context['timeout'] = LONG_TIMEOUT
        context['buttons'] = [Button('Back', 'back', css_class='btn-success btn-lg'),
                              Button('Next', 'register', css_class='btn-success btn-lg')]
        return context

    def post(self, request, *args, **kwargs):
        if 'back' in request.POST:
            return redirect(restart_url(request))
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
        context['timeout_url'] = reverse(restart_url(self.request))
        context['timeout'] = LONG_TIMEOUT
        return context

    def get_success_url_name(self, **kwargs):
        return 'pos_consent_token'

    def get_already_registered_url_name(self):
        return 'pos_password'


class PosConsentView(LoginRequiredMixin, ConsentTokenView):
    template_name = 'pos/consent.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['pos'] = True
        context['timeout_url'] = reverse(restart_url(self.request))
        context['timeout'] = LONG_TIMEOUT
        return context

    def get_success_url(self):
        return reverse(menu_url(self.request))


class MemberMenuView(LoginRequiredMixin, TemplateView):
    """ Menu of options for members """
    template_name = 'pos/menu.html'
    timeout = LONG_TIMEOUT

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        id = self.request.session.get('person_id', None)
        if id:
            person = Person.objects.get(pk=id)
            context['person_id'] = int(id)
            context['fullname'] = person.fullname
            context['admin'] = person.auth.is_staff or person.auth.groups.filter(name='Pos').exists()
        else:
            context['person_id'] = -1
            context['fullname'] = 'Complimentary'
        context['timeout_url'] = reverse(restart_url(self.request))
        context['timeout'] = self.timeout
        return context

    def post(self, request, *args, **kwargs):
        if 'attended_on' in request.POST:
            request.session['attended_allowed'] = True
        elif 'attended_off' in request.POST:
            request.session['attended_allowed'] = False
        return redirect('pos_menu')


class PosView(LoginRequiredMixin, TemplateView):
    """ The main POS screen """
    template_name = 'pos/pos.html'

    def get_context_data(self, **kwargs):
        context = super(PosView, self).get_context_data(**kwargs)
        layout = self.request.session['layout']
        context['rows'], used_items = build_pos_array(layout)
        context['items_url'] = reverse('pos_ajax_items')
        context['post_url'] = reverse('pos_run')
        context['exit_url'] = reverse('pos_start' if self.request.session['attended'] else 'pos_menu')
        context['terminal'] = self.request.session['terminal']
        context['complimentary'] = False
        if self.request.session['attended']:
            context['is_attended'] = 'true'
            context['full_name'] = 'Attended mode'
        else:
            context['is_attended'] = 'false'
            id = int(self.request.session['person_id'])
            context['person_id'] = id
            if id > 0:
                person = Person.objects.get(pk=id)
                context['full_name'] = person.fullname
            else:
                context['complimentary'] = True
                context['full_name'] = 'Complimentary'

        context['timeout_url'] = reverse(restart_url(self.request))
        context['timeout'] = LONG_TIMEOUT
        return context

    def post(self, request, *args, **kwargs):
        """ Write transaction to database"""

        if request.is_ajax():
            receipt = json.loads(request.body)
            pay_record = receipt.pop()
            layout_id, terminal = read_cookie(request)
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
            if self.request.session['attended']:
                return HttpResponse(reverse(restart_url(request)))
            else:
                return HttpResponse(reverse('pos_menu_timeout'))
        # should not get here - all posts are ajax
        return redirect(restart_url(request))


class VisitorBookView(LoginRequiredMixin, SingleTableView):
    """ List visitors book"""
    model = VisitorBook
    table_class = VisitorBookTable
    template_name = 'pos/visitor_book.html'
    table_pagination = {'per_page': 10}

    def get_table_data(self):
        self.id = self.kwargs.get('person_id', None)
        if self.id:
            qs = VisitorBook.objects.filter(member_id=self.id)
        elif self.request.session.get('person_id', None):
            qs = VisitorBook.objects.filter(member_id=self.request.session['person_id'])
        else:
            qs = VisitorBook.objects.all()
        return list(qs.order_by('-date', '-id').select_related('visitor').select_related('member__membership'))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.id:
            context['person'] = Person.objects.get(pk=self.id)
        context['timeout_url'] = reverse(restart_url(self.request))
        context['timeout'] = LONG_TIMEOUT
        return context


class VisitorMenuView(LoginRequiredMixin, TemplateView):
    template_name = 'pos/visitor_menu.html'
    form_class = VisitorForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['person'] = Person.objects.get(pk=self.request.session['person_id'])
        context['timeout_url'] = reverse(restart_url(self.request))
        context['timeout'] = LONG_TIMEOUT
        return context


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
        self.admin = self.person.auth.is_staff or self.person.auth.groups.filter(name='Pos').exists()
        # if not self.admin:
        kwargs.update({'person_id': self.person.id,
                       'junior': self.junior
                       },
                      )
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['has_existing'] = len(context['form'].fields['visitors'].choices) > 1
        context['person'] = self.person
        context['admin'] = self.admin
        # context['visitors'] = VisitorBook.objects.filter(member_id=person.id, visitor__junior=self.junior)
        context['junior'] = self.junior
        context['timeout_url'] = reverse(restart_url(self.request))
        context['timeout'] = LONG_TIMEOUT
        return context

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

    # def post(self, request, *args, **kwargs):
    #     if request.POST['person_id']:
    #         request.session['person_id'] = request.POST['person_id']
    #         if int(request.POST['person_id']) > 0:
    #             person = Person.objects.get(pk=request.POST['person_id'])
    #             if person.auth_id:
    #                 return redirect('pos_password')
    #             return redirect('pos_register')
    #         else:
    #             # Complimentary sale, id = -1
    #             return redirect('pos_password')
    #     return redirect(restart_url(request))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['timeout_url'] = reverse(restart_url(self.request))
        context['timeout'] = LONG_TIMEOUT
        return context



def ajax_items_view(request):
    """ responds to ajax request for item list"""
    data = serialize('json', Item.objects.all())
    return JsonResponse(data, safe=False)


def ajax_ping_view(request):
    """ responds to keep alive from pos"""
    terminal = request.POST['terminal']
    records = PosPing.objects.filter(terminal=terminal)
    if records:
        records[0].time = timezone.now()
        records[0].save()
    else:
        record = PosPing.objects.create(terminal=terminal, time=timezone.now())
    return HttpResponse('OK')

def ajax_member_lookup(request):
    id = request.POST['id']