from django.conf.urls import url
from public.views import *

# /public/ URLs

urlpatterns = [
    url(r'^$', PublicHomeView.as_view(), name='public-home'),
    url(r'^apply/adult/$', ApplyAdult.as_view(), name='public-apply-adult'),
    url(r'^apply/child/$', ApplyChild.as_view(), name='public-apply-child'),
    url(r'^apply/main/$', ApplyMain.as_view(), name='public-apply-main'),
    url(r'^apply/next/$', ApplyNextActionView.as_view(), name='public-apply-next'),
    url(r'^apply/add/(?P<index>\d+)/$', ApplyAddView.as_view(), name='public-apply-add'),
    url(r'^apply/addadult/(?P<index>\d+)/(?P<membership_id>\d+)/$', ApplyAdultProfileView.as_view(),
        name='public-apply-addadult'),
    url(r'^apply/addchild/(?P<index>\d+)/(?P<membership_id>\d+)/$', ApplyChildProfileView.as_view(),
        name='public-apply-addchild'),
    url(r'^apply/submit/$', ApplySubmitView.as_view(), name='public-apply-submit'),
    url(r'^apply/thankyou/$', ApplyThankYouView.as_view(), name='public-apply-thankyou'),
    url(r'^register/(?P<next>[\w\-]+)/$', RegisterView.as_view(), name='public_register'),
    url(r'^register/person/(?P<next>[\w\-])+/(?P<token>.+)/$', RegisterTokenView.as_view(), name='public_register2'),
    url(r'^contact/$', ContactView.as_view(), name='public-contact'),
    url(r'^contact/(?P<person_id>\d+)/$', ContactView.as_view(), name='public-contact-person'),
    url(r'^thankyou/$', ThankyouView.as_view(), name='public-thankyou'),
    url(r'^resigned/$', ResignedView.as_view(), name='public-resigned'),
    url(r'^privacy_policy/$', PrivacyPolicyView.as_view(), name='privacy-policy')
    ]
