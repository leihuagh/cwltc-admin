from django.conf.urls import url, include
from public.views import *

# /public/ URLs

urlpatterns = [
    url(r'^$', PublicHomeView.as_view(), name='public-home'),
    url(r'apply/junior/$', ApplyJuniorView.as_view(), name='public-apply-junior'),
    url(r'apply/adult/$', ApplyAdultView.as_view(), name='public-apply-adult'),
    url(r'register/$', RegisterView.as_view(), name='public-register'),
    url(r'login/$', LoginView.as_view(), name='public-login'),
    url(r'thankyou/$', ThankyouView.as_view(), name='public-thankyou'),
    url(r'resigned/$', ResignedView.as_view(), name='public-resigned'),
    ]