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
from braces.views import GroupRequiredMixin
from public.views import RegisterView, RegisterTokenView, ConsentTokenView
from mysite.common import Button
from pos.tables import *
from pos.forms import TerminalForm
from pos.services import create_transaction_from_receipt, build_pos_array

LONG_TIMEOUT = 120000
SHORT_TIMEOUT = 30000

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
            layout = request.POST['layout']
            terminal = request.POST['terminal']
            response = HttpResponseRedirect(reverse('pos_start'))
            max_age = 10 * 365 * 24 * 60 * 60
            response.set_cookie('pos', layout + ';' + terminal, max_age=max_age)
            request.session['layout_id'] = layout
            return response
        return redirect('pos_admin')


class DisabledView(TemplateView):
    template_name = 'pos/disabled.html'


class StartView(LoginRequiredMixin, TemplateView):
    """ Member login or attended mode selection """
    template_name = 'pos/start.html'

    def get(self, request, *args, **kwargs):
        request.session['person_id'] = None
        request.session['layout_id'], request.session['terminal'] = read_cookie(request)
        request.session['message'] = self.get_message()
        if request.session['layout_id']:
            return super().get(request, *args, **kwargs)
        return redirect('pos_disabled')

    def get_message(self):
        return ""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['layout_name'] = Layout.objects.get(pk=self.request.session['layout_id']).name
        return context

    def post(self, request, *args, **kwargs):
        if 'login' in request.POST:
            request.session['attended'] = False
            return redirect('pos_user')
        elif 'attended' in request.POST:
            request.session['attended'] = True
            return redirect('pos_run')
        return redirect('pos_start')


class RestartView(StartView):
    """ Restart after error or bad password - show a message """

    def get_message(self):
        return self.request.session['message']


def read_cookie(request):
    if 'pos' in request.COOKIES:
        values = request.COOKIES['pos'].split(';')
        return values[0], values[1]
    else:
        return None, None


class GetUserView(TemplateView):
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
        return redirect('pos_start')

    def get_context_data(self, **kwargs):
        context = super(GetUserView, self).get_context_data(**kwargs)
        context['timeout_url'] = reverse('pos_start')
        context['timeout'] = LONG_TIMEOUT
        return context


class GetPasswordView(TemplateView):
    """ User's password or PIN """
    template_name = 'pos/get_password.html'

    def post(self, request, *args, **kwargs):
        if request.POST['submit']:
            if request.session['person_id']: # There is a bug where this is None
                id = int("abc")
                id = int(request.session['person_id'])
                if id > 0:
                    try:
                        person = Person.objects.get(pk=request.session['person_id'])
                    except Person.DoesNotExist:
                        return redirect('pos_start')
                    if check_password(request.POST['pin'], person.pin):
                        return redirect('pos_menu')
                    user = User.objects.get(pk=person.auth_id)
                    if user.check_password(request.POST['password']):
                        return redirect('pos_menu')
                else: # Complimentary
                    if request.POST['pin'] == str(datetime.now().year):
                        return redirect('pos_run')
            request.session['message'] = "Incorrect PIN or password"
            return redirect('pos_restart')
        return redirect('pos_start')

    def get_context_data(self, **kwargs):
        context = super(GetPasswordView, self).get_context_data(**kwargs)
        id = int(self.request.session['person_id'])
        if id > 0:
            person = Person.objects.get(pk=self.request.session['person_id'])
            context['full_name'] = person.fullname
        else:
            context['full_name'] = 'Complimentary'
        context['timeout_url'] = reverse('pos_start')
        context['timeout'] = LONG_TIMEOUT
        return context


class PosRegisterView(RegisterView):
    """ When user is not registered we use the public
    registration form and override some things """
    template_name = 'pos/register.html'

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
        context['timeout_url'] = reverse('pos_start')
        context['timeout'] = LONG_TIMEOUT
        context['buttons'] = [Button('Back', 'back', css_class='btn-success btn-lg'),
                             Button('Next', 'register', css_class='btn-success btn-lg')]
        return context

    def post(self, request, *args, **kwargs):
        if 'back' in request.POST:
            return redirect('pos_start')
        return super().post(request, args, kwargs)

    def get_success_url_name(self):
        return 'pos_register_token'

    def get_failure_url_name(self):
        return 'pos_start'


class PosRegisterTokenView(RegisterTokenView):
    """
    Get username, PIN and password
    """
    template_name = 'pos/register_token.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['timeout_url'] = reverse('pos_start')
        context['timeout'] = LONG_TIMEOUT
        return context

    def get_success_url_name(self, **kwargs):
        return 'pos_consent_token'

    def get_already_registered_url_name(self):
        return 'pos_password'


class PosConsentView(ConsentTokenView):
    template_name = 'pos/consent.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['pos'] = True
        context['timeout_url'] = reverse('pos_start')
        context['timeout'] = LONG_TIMEOUT
        return context

    def get_success_url(self):
        return reverse('pos_menu')


class MemberMenuView(LoginRequiredMixin, TemplateView):
    """ Menu of options for members """
    template_name = 'pos/menu.html'
    timeout = LONG_TIMEOUT

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        id = int(self.request.session['person_id'])
        if id > 0:
            person = Person.objects.get(pk=self.request.session['person_id'])
            context['person_id'] = id
            context['full_name'] = person.fullname
            context['admin'] = person.auth.is_staff or person.auth.groups.filter(name='Pos').exists()
        else:
            context['person_id'] = -1
            context['full_name'] = 'Complimentary'
        context['timeout_url'] = reverse('pos_start')
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
        layout = Layout.objects.get(pk=self.request.session['layout_id'])
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

        context['timeout_url'] = reverse('pos_start')
        context['timeout'] = LONG_TIMEOUT
        return context

    def post(self, request, *args, **kwargs):
        """ Write transaction to database"""

        if request.is_ajax():
            receipt = json.loads(request.body)
            pay_record = receipt.pop()
            layout, terminal = read_cookie(request)
            trans = create_transaction_from_receipt(request.user.id,
                                                    terminal,
                                                    layout,
                                                    receipt,
                                                    pay_record['total'],
                                                    pay_record['people'],
                                                    request.session['attended']
                                                    )
            request.session['last_person'] = trans[0]
            request.session['last_total'] = trans[1]
            if self.request.session['attended']:
                return HttpResponse(reverse('pos_start'))
            else:
                return HttpResponse(reverse('pos_menu_timeout'))
        # should not get here - all posts are ajax
        return redirect('pos_start')


def ajax_items_view(request):
    """ responds to ajax request for item list"""
    data = serialize('json', Item.objects.all())
    return JsonResponse(data, safe=False)



