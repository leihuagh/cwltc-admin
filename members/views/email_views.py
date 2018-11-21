# ========= EMAIL, TEXT BLOCKS and Mail Types
import datetime
import json
import logging

from braces.views import StaffuserRequiredMixin
from django.conf import settings
from django.contrib import messages
from django.core.signing import Signer
from django.http import JsonResponse
from django.shortcuts import redirect
from django.shortcuts import render_to_response
from django.shortcuts import reverse
from django.views.generic import ListView, CreateView, UpdateView, DetailView, TemplateView
from django.views.generic.edit import FormView

from members.forms import TextBlockForm, EmailForm, MailTypeForm
from members.mail import send_multiple_mails, send_template_mail
from members.models import (Person, MailType, TextBlock, MailCampaign)

stdlogger = logging.getLogger(__name__)


class EmailView(StaffuserRequiredMixin, FormView):
    form_class = EmailForm
    template_name = 'members/email.html'
    is_selection = False

    def __init__(self):
        super().__init__()
        self.person = None

    def get(self, request, *args, **kwargs):
        if request.is_ajax():
            # Return text block that was selected within editor
            try:
                block_id = int(request.GET['blockId'])
                block = TextBlock.objects.get(pk=block_id)
                dict = {'text': block.text}
                return JsonResponse(dict)
            except TextBlock.DoesNotExist:
                return JsonResponse({'error': 'Bad text block request'})
        else:
            return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Send email'
        blocks = TextBlock.objects.all()
        value_list = []
        for block in blocks:
            if block.text[0] != '_':
                dict_entry = {"text": "'" + block.name + "'", "value": "'" + str(block.id) + "'"}
                json_entry = json.dumps(dict_entry).replace('"', '')
                value_list.append(json_entry)
        context['blocks'] = value_list
        return context

    def get_initial(self):
        """
        This is called by get_context_data
        """
        initial = super().get_initial()
        person_id = self.kwargs.get('person_id', '')
        if person_id:
            person = Person.objects.get(pk=person_id)
            if person.linked and not person.pays_own_bill:
                person = person.linked
            to = person.email + f' ({person.fullname})'
        else:
            count = len(self.request.session.get('selected_people_ids', []))
            to = f'{count} selected people'
        initial['to'] = to
        initial['from_email'] = getattr(settings, 'SUBS_EMAIL')
        initial['subject'] = "Coombe Wood LTC membership"
        initial['text'] = """Dear {{first_name}}"""
        campaign_id = self.kwargs.get('campaign', 0)
        if campaign_id:
            campaign = MailCampaign.objects.get(pk=campaign_id)
            initial['text'] = campaign.text
        return initial

    def form_valid(self, form):
        from_email = form.cleaned_data['from_email']
        text = form.cleaned_data['text']
        subject = form.cleaned_data['subject']
        mail_type_list = []
        for mail_type in form.cleaned_data['mailtype']:
            mail_type_list.append(mail_type.id)
        mail_types = MailType.objects.filter(id__in=mail_type_list)

        if self.person:
            result = send_template_mail(request=self.request,
                                        person=self.person,
                                        text=text,
                                        from_email=from_email,
                                        subject=subject,
                                        mail_types=mail_types)
            if result == 'sent':
                messages.info(self.request, "Mail sent")
            else:
                messages.error(self.request, f'Mail not sent - {result}')
            return redirect('person-detail', pk=self.person.id)

        else:
            id_list = self.request.session['selected_people_ids']
            result = send_multiple_mails(self.request, Person.objects.filter(pk__in=id_list),
                                         text, from_email, None, None, subject, mail_types)
            self.request.session['selected_people_ids'] = []
            messages.info(self.request, result)
            return redirect(self.request.session['source_path'])


class EmailSelectionView(EmailView):
    is_selection = True


class TextBlockCreateView(StaffuserRequiredMixin, CreateView):
    model = TextBlock
    form_class = TextBlockForm
    template_name = 'members/textblock_form.html'
    title = 'Create text block'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['app-title'] = 'Create text block'
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({'no_delete': True})
        return kwargs

    def form_invalid(self, form):
        if 'cancel' in form.data:
            return redirect('text-list')
        return super(TextBlockCreateView, self).form_invalid(form)

    def form_valid(self, form):
        if 'cancel' in form.data:
            return redirect('text-list')
        return super(TextBlockCreateView, self).form_valid(form)

    def get_success_url(self):
        return reverse('text-list')


class TextBlockUpdateView(StaffuserRequiredMixin, UpdateView):
    model = TextBlock
    form_class = TextBlockForm
    template_name = 'members/textblock_form.html'
    title = 'Update text block'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['app-title'] = 'Update text block'
        return context

    def form_valid(self, form):

        if 'save' in form.data:
            form.save()
        if 'delete' in form.data:
            block = self.get_object()
            block.delete()
        return redirect('text-list')

    def form_invalid(self, form):
        if 'delete' in form.data:
            block = self.get_object()
            block.delete()
            return redirect('text-list')
        return super(TextBlockUpdateView, self).form_invalid(form)


class TextBlockListView(StaffuserRequiredMixin, ListView):
    model = TextBlock
    template_name = 'members/textblock_list.html'
    title = 'List text blocks'


# ========= MAIL TYPES


class MailTypeCreateView(StaffuserRequiredMixin, CreateView):
    model = MailType
    form_class = MailTypeForm
    template_name = 'members/generic_crispy_form.html'

    def get_success_url(self):
        return reverse('mailtype-list')


class MailTypeUpdateView(StaffuserRequiredMixin, UpdateView):
    model = MailType
    form_class = MailTypeForm
    template_name = 'members/generic_crispy_form.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['with_delete'] = True
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Edit message type'
        return context

    def form_invalid(self, form):
        if 'cancel' in form.data:
            return redirect(self.get_success_url())
        return super().form_invalid(form)

    def form_valid(self, form):
        if 'cancel' in form.data:
            return redirect(self.get_success_url())
        if 'submit' in form.data:
            return super().form_valid(form)
        if 'delete' in form.data:
            self.get_object().delete()
            return super().form_valid(form)

    def get_success_url(self):
        return reverse('mailtype-list')


class MailTypeListView(StaffuserRequiredMixin, ListView):
    """ List all mail type """
    model = MailType
    template_name = 'members/mailtype_list.html'
    context_object_name = 'mailtypes'
    ordering = 'sequence'


class MailTypeDetailView(StaffuserRequiredMixin, DetailView):
    model = MailType
    template_name = 'members/mailtype_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        mailtype = self.get_object()
        context['people'] = mailtype.person_set.all()
        context['mailtype'] = mailtype
        return context


class MailTypeSubscribeView(TemplateView):
    """
    Public View accessed by Token
    Displays a form with checkboxes that allows a user to unsubscribe
    User can either be logged in (self.token=None) or get here direct from an Unsubscribe link
    """
    template_name = 'public/mailtype_manage.html'

    def get_context_data(self, **kwargs):
        context = super(MailTypeSubscribeView, self).get_context_data(**kwargs)
        self.get_person()
        context['person'] = self.person
        context['token'] = self.token
        if self.person:
            mailtypes = MailType.objects.filter(can_unsubscribe=True).order_by('description')
            for m in mailtypes:
                if m.person_set.filter(id=self.person.id).exists():
                    m.subscribed = False
                else:
                    m.subscribed = True
            context['mailtypes'] = mailtypes
        return context

    def get_person(self):
        self.person = None
        person_id = None
        self.token = self.kwargs.pop('token', None)
        if self.token:
            try:
                signer = Signer()
                person_id = signer.unsign(self.token)
            except:
                pass
        else:
            if self.request.user.is_authenticated:
                person_id = self.kwargs.pop('person', None)
        if person_id:
            self.person = Person.objects.get(pk=person_id)

    def post(self, request, *args, **kwargs):
        self.get_person()
        checklist = request.POST.getlist('checks')
        mail_types = MailType.objects.all()
        has_selection = False
        for m in mail_types:
            if m.can_unsubscribe:
                if str(m.id) in checklist:
                    has_selection = True
                    m.person_set.remove(self.person)
                else:
                    m.person_set.add(self.person)
        if has_selection:
            self.person.allow_marketing = True
            self.person.consent_date = datetime.datetime.now()
            self.person.save()
        if self.token:
            return render_to_response('public/mailtype_done.html')
        else:
            messages.info(request, "Your mail choices have been saved")
            return redirect('club_person_pk', pk=self.person.pk)



