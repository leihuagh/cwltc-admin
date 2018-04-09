from django.shortcuts import redirect
from django.views.generic import TemplateView
from braces.views import LoginRequiredMixin
from .models import *

class BallotView(LoginRequiredMixin, TemplateView):
    template_name = 'wimbledon/ballot.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['bg_class'] = 'bg-white'
        return context

class ChoiceView(LoginRequiredMixin, TemplateView):
    template_name = 'wimbledon/choice.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return common_context(context, self.request)

    def post(self, request, *args, **kwargs):
        if 'cancel' in request.POST:
            return redirect('wimbledon_ballot')
        person = Person.objects.get(auth=request.user.id)
        OptOut.objects.filter(person_id=person.id).delete()
        if 'all' in request.POST:
            opt = OptOut.objects.create(person_id=person.id, ticket_id=None, all_days=True)
        else:
            for key in request.POST:
                if key[:6] == 'ticket':
                    id = key[7:]
                    opt = OptOut.objects.create(person_id=person.id, ticket_id=id)
        return redirect('wimbledon_done')


class DoneView(LoginRequiredMixin, TemplateView):
    template_name = 'wimbledon/done.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return common_context(context, self.request)

def common_context(context, request):
    person = Person.objects.get(auth=request.user.id)
    all_days = OptOut.objects.filter(all_days=True)
    if len(all_days) > 0:
        context['all_days'] = True
        context['opt_out'] = []
    else:
        context['all_days'] = False
        context['opt_out'] = list(OptOut.objects.filter(person_id=person.id).values_list('ticket_id', flat=True))
    context['tickets'] = list(Tickets.objects.order_by('id'))
    context['bg_class'] = 'bg-white'
    return context