from django.contrib.auth.views import LoginView
from django.core.signing import Signer
from members.models import Person
from .forms import *

class CustomLoginView(LoginView):
    """ Login with person's id optionally passed as a token """
    template_name = 'authentication/login.html'
    form_class = CrispyAuthenticationForm
    redirect_authenticated_user = True
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
        initial = super().get_initial()
        if self.person and self.person.auth:
            initial['username'] = self.person.auth.username
        return initial