from django.conf.urls import url
from public.views import *

# /public/ URLs

urlpatterns = [
    url(r'^$', PublicHomeView.as_view(), name='public-home'),
    url(r'^apply/adult/$', ApplyAdult.as_view(), name='public-apply-adult'),
    url(r'^apply/child/$', ApplyChild.as_view(), name='public-apply-child'),
    url(r'^apply/nonmember/$', ApplyNonMember.as_view(), name='public-apply-nonmember'),
    url(r'^apply/main/$', ApplyMain.as_view(), name='public-apply-main'),
    url(r'^apply/membership/(?P<index>\d+)/(?P<membership_id>\d+)/$', ApplyAdultMembershipView.as_view(),
        name='public-apply-membership'),
    url(r'^apply/next/$', ApplyNextActionView.as_view(), name='public-apply-next'),
    url(r'^apply/add/(?P<index>\d+)/$', ApplyAddView.as_view(), name='public-apply-add'),
    url(r'^apply/contact/(?P<index>\d+)/(?P<membership_id>\d+)/$', ApplyAdultContactView.as_view(),
        name='public-apply-contact'),
    url(r'^apply/adultprofile/(?P<index>\d+)/(?P<membership_id>\d+)/$', ApplyAdultProfileView.as_view(),
        name='public-apply-adult-profile'),
    url(r'^apply/childprofile/(?P<index>\d+)/(?P<membership_id>\d+)/$', ApplyJuniorProfileView.as_view(),
        name='public-apply-child-profile'),
    url(r'^apply/submit/$', ApplySubmitView.as_view(), name='public-apply-submit'),
    url(r'^apply/thank-you/$', ApplyThankYouView.as_view(), name='public-apply-thank-you'),

    url(r'^please_register/(?P<token>.+)/$', PleaseRegisterView.as_view(), name='public-please-register-token'),
    url(r'^register/$', RegisterView.as_view(), name='public-register'),
    url(r'^register/invoice/(?P<token>.+)/$', RegisterTokenView.as_view(invoice=True), name='public-register-invoice-token'),
    url(r'^register/token/(?P<token>.+)/$', RegisterTokenView.as_view(), name='public-register-token'),

    url(r'^consent/invoice/(?P<token>.+)/$', ConsentTokenView.as_view(invoice=True),
        name='public-consent-invoice-token'),
    url(r'^consent/(?P<token>.+)/$', ConsentTokenView.as_view(), name='public-consent-token'),

    url(r'^contact/$', ContactView.as_view(), name='public-contact'),
    url(r'^contact/(?P<person_id>\d+)/$', ContactView.as_view(), name='public-contact-person'),
    url(r'^thank_you/$', ThankyouView.as_view(), name='public-thank-you'),
    url(r'^resigned/$', ResignedView.as_view(), name='public-resigned'),

    url(r'^privacy_policy/$', PrivacyPolicyView.as_view(), name='privacy-policy'),

    url(r'^camp/$', CampHomeView.as_view(), name='camp-home'),
    url(r'^camp/register/$', CampRegisterView.as_view(), name='camp-register'),
    url(r'^camp/register/new/$', CampRegisterNewView.as_view(), name='camp-register-new'),
    url(r'^camp/register/find/$', CampRegisterOldView.as_view(), name='camp-register-find'),
    ]
