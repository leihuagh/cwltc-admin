import logging
from django.views.generic import ListView, DetailView, CreateView, UpdateView, FormView
from django.contrib import messages
from django.shortcuts import redirect, reverse, get_object_or_404
from django.forms import ModelForm
from braces.views import StaffuserRequiredMixin

from members.models import Subscription, Person, Membership
from members.forms import SubscriptionForm, SubCorrectForm, YearConfirmForm
from members.services import subscription_activate, subscription_delete, subscription_renew, subscription_renew_batch, \
    subscription_renew_list, subscription_create_invoiceitems, subscription_delete_invoiceitems, person_resign


stdlogger = logging.getLogger(__name__)


class SubCreateView(StaffuserRequiredMixin, CreateView):
    model = Subscription
    form_class = SubscriptionForm
    template_name = 'members/subscription_form.html'

    def get_form_kwargs(self):
        """ pass the person_id to the form """
        kwargs = super().get_form_kwargs()
        kwargs.update({'person_id': self.kwargs['person_id']})
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['person'] = Person.objects.get(pk=self.kwargs['person_id'])
        return context

    def form_valid(self, form):

        form.instance.person_member = Person.objects.get(pk=self.kwargs['person_id'])
        # ensure a previously inactive or resigned person is now active
        form.instance.person_member.state = Person.ACTIVE
        form.instance.person_member.save()
        parent = form.instance.person_member.linked
        if parent:
            if parent.state == Person.APPLIED and parent.adultapplication_set.count == 0:
                parent.state = Person.ACTIVE
                parent.save()

        form.instance.invoiced_month = 0
        form.instance.membership = Membership.objects.get(pk=form.cleaned_data['membership_id'])

        sub = form.save()
        subscription_activate(sub)
        subscription_create_invoiceitems(sub, sub.start_date.month)
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('person-detail', kwargs={'pk': self.kwargs['person_id']})


class SubUpdateView(StaffuserRequiredMixin, UpdateView):
    model = Subscription
    form_class = SubscriptionForm
    template_name = 'members/subscription_form.html'

    def get_form_kwargs(self):
        """ pass the person_id to the form """
        sub = self.get_object()
        kwargs = super().get_form_kwargs()
        kwargs.update({'person_id': sub.person_member_id})
        return kwargs

    def get_context_data(self, **kwargs):
        context = super(SubUpdateView, self).get_context_data(**kwargs)
        sub = self.get_object()
        context['sub'] = sub
        context['person'] = sub.person_member
        context['items'] = sub.invoiceitem_set.all().order_by('item_type')
        return context

    def form_invalid(self, form):
        sub = self.get_object()
        if 'cancel' in form.data:
            return redirect(sub.person_member)
        return super().form_invalid(form)

    def form_valid(self, form):
        sub = self.get_object()
        if 'cancel' in form.data:
            return redirect(sub.person_member)

        if 'submit' in form.data:
            form.instance.membership = Membership.objects.get(pk=form.cleaned_data['membership_id'])
            return super(SubUpdateView, self).form_valid(form)

        if 'delete' in form.data:
            sub = self.get_object()
            subscription_delete_invoiceitems(sub)
            person = sub.person_member
            subscription_delete(sub)
            return redirect(person)

        if 'resign' in form.data:
            person_resign(form.instance.person_member)
            return redirect(reverse('person-detail', kwargs={'pk': sub.person_member_id}))

    def get_success_url(self):
        sub = self.get_object()
        subscription_activate(sub)
        subscription_create_invoiceitems(sub, sub.start_date.month)
        return reverse('person-detail', kwargs={'pk': sub.person_member_id})


class SubCorrectView(StaffuserRequiredMixin, UpdateView):
    """ standard model view that skips validation """
    model = Subscription
    form_class = SubCorrectForm

    def get_success_url(self):
        sub = self.get_object()
        subscription_activate(sub)
        return reverse('person-detail', kwargs={'pk': sub.person_member_id})


class SubDetailView(StaffuserRequiredMixin, DetailView):
    model = Subscription
    template_name = 'members/generic_detail.html'

    class Form(ModelForm):
        class Meta:
            model = Subscription
            exclude = ['person_member', 'membership']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        sub = self.object
        context.update(
            {'width': '25rem',
             'title': 'Subscription',
             'sub_title': ('person-detail', sub.person_member.id, sub.person_member.fullname),
             'form': SubDetailView.Form(instance=sub),
             })
        items = sub.invoiceitem_set.all()
        if items:
            context['links'] = [('Invoice item', 'item-detail', items[0].id)]
        return context


class SubHistoryView(StaffuserRequiredMixin, ListView):
    """ Subs history for 1 person """
    model = Subscription
    template_name = 'members/subscription_history.html'
    context_object_name = 'subs'
    person = None

    def get_queryset(self):
        self.person = get_object_or_404(Person, pk=self.kwargs['person_id'])
        return Subscription.objects.filter(person_member=self.person).order_by('-start_date', 'active')

    def get_context_data(self, **kwargs):
        context = super(SubHistoryView, self).get_context_data(**kwargs)
        context['person'] = self.person
        return context


class SubRenewAllView(StaffuserRequiredMixin, FormView):
    form_class = YearConfirmForm
    template_name = 'members/generic_crispy_form.html'
    subs = None

    def get_context_data(self, **kwargs):
        context = super(SubRenewAllView, self).get_context_data(**kwargs)
        self.subs = Subscription.objects.filter(active=True, no_renewal=False)
        context['title'] = 'Renew subscriptions'
        context['message'] = '{} subscriptions to renew'.format(self.subs.count())
        return context

    def form_valid(self, form):
        year = form.cleaned_data['sub_year']
        if 'renew' in self.request.POST:
            subscription_renew_batch(year, 5)
            messages.success(self.request, 'Subscriptions for {} generated'.format(year))
        return redirect(reverse('home'))

    def get_success_url(self):
        return reverse('home')


class SubRenewSelectionView(StaffuserRequiredMixin, FormView):
    """
    Renew a selected list of subscriptions
    If the list contains only one person, redirect to the person
    else redirect to the source path
    """
    form_class = YearConfirmForm
    template_name = 'members/generic_crispy_form.html'

    def get_context_data(self, **kwargs):
        context = super(SubRenewSelectionView, self).get_context_data(**kwargs)
        selection = self.request.session['selected_people_ids']
        subtext = "subscription"
        if len(selection) > 1:
            subtext += "s"
        context['title'] = "Renew " + subtext
        if selection:
            context['message'] = '{} {} to renew'.format(len(selection), subtext)
        return context

    def form_valid(self, form):
        sub_year = form.cleaned_data['sub_year']
        selection = self.request.session['selected_people_ids']
        if 'apply' in self.request.POST and selection:
            if len(selection) == 1:
                person = Person.objects.get(pk=self.request.session['selected_people_ids'][0])
                subscription_renew(person.sub, sub_year, Subscription.START_MONTH, generate_item=True)
                self.request.session['selected_people_ids'] = []
                return redirect(person)
            else:
                count = subscription_renew_list(sub_year, Subscription.START_MONTH, selection)
                people = "person" if len(selection) == 1 else "people"
                messages.success(self.request, '{} {} processed and {} subscriptions for {} generated'.format(
                    len(selection),
                    people,
                    count,
                    sub_year))
        self.request.session['selected_people_ids'] = []
        return redirect(self.request.session['source_path'])

    def get_success_url(self):
        return reverse('home')

