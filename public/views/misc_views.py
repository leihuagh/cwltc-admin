import logging
from django.shortcuts import redirect
from django.views.generic import TemplateView
from django.core.mail import send_mail
from django.views.generic.edit import FormView
from public.forms import *
from cardless.services import person_from_token

logger = logging.getLogger(__name__)


class ThankyouView(TemplateView):
    template_name = 'public/thankyou.html'


class PublicHomeView(TemplateView):
    template_name = 'public/home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        context['no_container'] = True
        return context


class LoginView(FormView):
    template_name = 'authentication/login.html'

# ================= Public Views accessed through a token

class ContactView(FormView):
    """
    Send a message. Note token is a person token
    """
    form_class = ContactForm
    template_name = 'public/crispy_form.html'
    resign = False
    token = None

    def dispatch(self, request, *args, **kwargs):
        self.token = kwargs.pop('token', None)
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        initial = super().get_initial()
        if self.token:
            person = person_from_token(self.token, Person)
            initial.update({'email': person.email})
        return initial

    def get_context_data(self, **kwargs):
        context = super(ContactView, self).get_context_data(**kwargs)
        if self.resign:
            context['title'] = "Resignation"
            context['message'] = "Please tell us briefly why you have resigned."
        else:
            context['title'] = "Query your bill"
            context['message'] = "Please type your query below"
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
        if self.resign:
            message += 'Resignation:  '
        else:
            message += 'Query:  '
        message += form.cleaned_data['message']
        send_mail(subject='CWLTC contact',
                  from_email='contact@coombewoodltc.co.uk',
                  message=message,
                  recipient_list=["subs.cwltc@gmail.com", "is@ktconsultants.co.uk"]
                  )
        if self.resign:
            return redirect('public-resigned')
        else:
            return redirect('public-thank-you')

    def form_invalid(self, form):
        return super(ContactView, self).form_invalid(form)


class ResignView(ContactView):
    resign = True


class ResignedView(TemplateView):
    template_name = 'public/resigned.html'

