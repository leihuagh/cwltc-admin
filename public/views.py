from django.shortcuts import render, render_to_response, redirect, get_object_or_404
from django.views.generic import DetailView, TemplateView
from django.views.generic.edit import FormView
from members.models import Invoice, Person, MailType

# ================= Public Views

class MailTypeSubscribeView(ProcessFormView, TemplateView):
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
        mailtypes = MailType.objects.all()
        for m in mailtypes:
            if str(m.id) in checklist:
                m.person_set.remove(self.person)
            else:
                m.person_set.add(self.person)
        if self.token:
            messages.info(request, "Your choices have been saved")
            return render_to_response('public/mailtype_done.html')
        return redirect(self.person)

class ResignedView(TemplateView):
    template_name = 'members/resigned.html'

class InvoicePublicView(DetailView):
    model = Invoice
    template_name = 'members/invoice_public.html'

    def get_object(self, querset=None):
        signer = Signer()
        try:
            invoice_id = signer.unsign(self.kwargs['token'])
            self.invoice = Invoice.objects.get(pk = invoice_id)
        except:
            self.invoice = None
        return self.invoice

    def get_context_data(self, **kwargs):
        context = super(InvoicePublicView, self).get_context_data(**kwargs)
        if self.invoice:
            self.invoice.add_context(context)
            context['token'] = self.kwargs['token']
        return context

    def post(self, request, *args, **kwargs):
        invoice = self.get_object()
        if 'pay' in request.POST:
            return redirect(gc_create_bill_url(invoice))
        if 'query' in request.POST:
            group = group_get_or_create("2017Query")
            invoice.person.groups.add(group)
            return redirect(reverse('contact-person', kwargs={'person_id': invoice.person.id}))
        elif 'resign' in request.POST:
            group = group_get_or_create("2017Resign")
            invoice.person.groups.add(group)
            return redirect(reverse('contact-resigned', kwargs={'person_id': invoice.person.id}))

class ContactView(FormView):
    form_class = ContactForm
    template_name = 'members/contact.html'
    resigned = False

    def get_context_data(self, **kwargs):
        context = super(ContactView, self).get_context_data(**kwargs)
        if self.resigned:
            context['message'] = "Please tell us briefly why you have resigned"
        else:
            context['message'] = "Please enter your query"
        return context

    def form_valid(self, form):
        if self.kwargs['person_id']:
            person = Person.objects.get(pk=self.kwargs['person_id'])
            message = "From {} id {} >".format(person.email, person.id)
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
                  recipient_list=["subs.cwltc@gmail.com","is@ktconsultants.co.uk"]
                  )
        if self.resigned:
            return HttpResponseRedirect(reverse('resigned'))
        else:
            return HttpResponseRedirect(reverse('thankyou'))
        
    def form_invalid(self, form):
        return super(ContactView, self).form_invalid(form)
    
class ThankyouView(TemplateView):
    template_name = 'members/thankyou.html'
