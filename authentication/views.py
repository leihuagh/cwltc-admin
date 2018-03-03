from django.contrib.auth.views import LoginView
from django.core.signing import Signer
from members.models import Person
from .forms import *

class CustomLoginView(LoginView):
    """ Login with username optionally passed as a token """
    template_name = 'authentication/login.html'
    form_class = CrispyAuthenticationForm
    person = None

    def dispatch(self, request, *args, **kwargs):
        token = self.kwargs.pop('token', None)
        if token:
            try:
                self.person = Person.objects.get(pk=Signer().unsign(token))
            except Person.DoesNotExist:
                pass
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        initial = {}
        if self.person:
            initial['username'] = self.person.email
        return initial