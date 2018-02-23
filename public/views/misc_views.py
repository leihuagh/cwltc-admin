import logging
from django.shortcuts import render_to_response, redirect
from django.views.generic import DetailView, TemplateView
from django.core.signing import Signer
from django.core.mail import send_mail
from django.contrib import messages
from django.views.generic.edit import FormView
from members.models import Invoice, MailType
from members.services import group_get_or_create
from public.forms import *
from cardless.services import detokenise, invoice_payments_list

logger = logging.getLogger(__name__)


class ThankyouView(TemplateView):
    template_name = 'public/thankyou.html'


class PublicHomeView(TemplateView):
    template_name = 'public/home.html'


class LoginView(FormView):
    template_name = 'authentication/login.html'

# ================= Public Views accessed through a token

class MailTypeSubscribeView(TemplateView):
    """
    Displays a form with checkboxes that allows a user to unsubscribe
    """
    template_name = 'public/mailtype_manage.html'

    def get_context_data(self, **kwargs):
        context = super(MailTypeSubscribeView, self).get_context_data(**kwargs)
        self.get_person()
        context['person'] = self.person
        if self.person:
            mailtypes = MailType.objects.all().order_by('can_unsubscribe')
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
        for m in mail_types:
            if str(m.id) in checklist:
                m.person_set.remove(self.person)
            else:
                m.person_set.add(self.person)
        if self.token:
            return render_to_response('public/mailtype_done.html')
        else:
            messages.info(request, "Your mail choices have been saved")
            return redirect(self.person)


class InvoicePublicView(DetailView):
    model = Invoice
    template_name = 'public/invoice_public.html'

    def get_object(self, queryset=None):
        self.invoice = detokenise(self.kwargs['token'], Invoice)
        return self.invoice

    def get_context_data(self, **kwargs):
        context = super(InvoicePublicView, self).get_context_data(**kwargs)
        if self.invoice:
            self.invoice.add_context(context)
            context['token'] = self.kwargs['token']
            context['payments_pending'] = invoice_payments_list(self.invoice, pending=True)
            context['payments_paid'] = invoice_payments_list(self.invoice, paid=True)
        return context

    def post(self, request, *args, **kwargs):
        invoice = self.get_object()
        if 'pay' in request.POST:
            return redirect('cardless_payment_create', kwargs['token'])
        if 'query' in request.POST:
            group = group_get_or_create("2017Query")
            invoice.person.groups.add(group)
            return redirect('public-contact-person', person_id=invoice.person.id)
        elif 'resign' in request.POST:
            group = group_get_or_create("2017Resign")
            invoice.person.groups.add(group)
            return redirect('public-resigned')


class ContactView(FormView):
    form_class = ContactForm
    template_name = 'public/crispy_form.html'
    resigned = False

    def get_context_data(self, **kwargs):
        context = super(ContactView, self).get_context_data(**kwargs)
        if self.resigned:
            context['title'] = "Resignation"
            context['message'] = "Please tell us briefly why you have resigned"
        else:
            context['title'] = "Send message to club management"
        return context

    def form_valid(self, form):
        id = self.kwargs.get('person_id')
        if id:
            try:
                person = Person.objects.get(pk=id)
                message = "From {} id {} >".format(person.email, person.id)
            except Person.DoesNotExist:
                message = "From bad person id {} >".format(id)
        else:
            message = ""
        message += form.cleaned_data['email']
        message += '  '
        if self.resigned:
            message += 'Resignation:  '
        else:
            message += 'Query:  '
        message += form.cleaned_data['message']
        send_mail(subject='CWLTC contact',
                  from_email='contact@coombewoodltc.co.uk',
                  message=message,
                  recipient_list=["subs.cwltc@gmail.com", "is@ktconsultants.co.uk"]
                  )
        if self.resigned:
            return redirect('public-resigned')
        else:
            return redirect('public-thank-you')

    def form_invalid(self, form):
        return super(ContactView, self).form_invalid(form)


class ResignedView(TemplateView):
    template_name = 'public/resigned.html'
