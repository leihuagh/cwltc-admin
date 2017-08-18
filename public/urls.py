from django.conf.urls import url, include
from public.views import *

# /public/ URLs

urlpatterns = [
    url(r'^$', PublicHomeView.as_view(), name='public-home'),
    url(r'apply/adult/$', ApplyAdult.as_view(), name='public-apply-adult'),
    url(r'apply/child/$', ApplyChild.as_view(), name='public-apply-child'),
    url(r'apply/main/$', ApplyMain.as_view(), name='public-apply-main'),
    url(r'apply/next/$', ApplyNextActionView.as_view(), name='public-apply-next'),
    url(r'apply/add/(?P<index>\d+)/$', ApplyAddView.as_view(), name='public-apply-add'),
    url(r'apply/addadult/(?P<index>\d+)/(?P<membership_id>\d+)/$', ApplyAdultProfileView.as_view(),
       name='public-apply-addadult'),  
    url(r'apply/addchild/(?P<index>\d+)/(?P<membership_id>\d+)/$', ApplyChildProfileView.as_view(),
       name='public-apply-addchild'),
    url(r'apply/submit/$', ApplySubmitView.as_view(), name='public-apply-submit'),
    url(r'apply/thankyou/$', ApplyThankyouView.as_view(), name='public-apply-thankyou'),
    url(r'register/$', RegisterView.as_view(), name='public-register'),
    url(r'register/person/(?P<token>.+)/$', RegisterTokenView.as_view(), name='public-register2'),
    url(r'thankyou/$', ThankyouView.as_view(), name='public-thankyou'),
    url(r'resigned/$', ResignedView.as_view(), name='public-resigned'),
    url(r'privacy_policy', PrivacyPolicyView.as_view(), name='privacy-policy')
    ]