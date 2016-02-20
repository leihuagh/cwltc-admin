# Create your views here.
import gocardless
from django.views.generic import RedirectView
from django.views.generic import TemplateView

gocardless.set_details(app_id="2J7RAH17Y3Q2PMGGACBJEQK4EY8X6VGXXB60D3SKR4YAAKWAV9G87K7H6BKSGKCQ",
        app_secret="K5NNZA4KKTSPCE2TF1PPKP41K9VMNEVWVMZGZEYQWM8T4897J1A1ZAGV6FDQ8QXT",
        access_token="6T93JFXX6XTS7C38XCZRWZ7379AJTXXBXE8ZC53FJMYZ0KBPG0S5S77G73N1FCX3",
        merchant_id="0VTW3337YC")

class SubmitGC(RedirectView):
  """
  Redirect customer to GoCardless payment pages
  """
  def get_redirect_url(self, **kwargs):
    url = gocardless.client.new_subscription_url(
              amount=10,
              interval_length=1,
              interval_unit="month",
              name="Premium Subscription",
              description="A premium subscription for my site",
              user={'email': self.request.POST['email']})
    return url

  """
  Use get logic for post requests (Django 1.3 support)
  """
  def post(self, request, *args, **kwargs):
    return self.get(request, *args, **kwargs)

class ConfirmGC(TemplateView):
  """
  Confirms payment creation
  """
  def dispatch(self, request, *args, **kwargs):
    # Patch the Django dispatch method to confirm successful receipt of the
    # payment details before doing anything else
    gocardless.client.confirm_resource(request.GET)
    return super(ConfirmGC, self).dispatch(request, *args, **kwargs)