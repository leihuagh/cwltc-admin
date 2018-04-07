from django.conf.urls import url
from django.contrib.auth import views as auth_views
from .forms import *
from .views import *

urlpatterns = [
    url(r'login/$', CustomLoginView.as_view(), name='login'),
    url(r'login/(?P<token>.+)/$', CustomLoginView.as_view(), name='login-token'),
    url(r'logout$', auth_views.LogoutView.as_view(next_page='/public/'),name='logout'),
    url(r'password_change/$', auth_views.PasswordChangeView.as_view(
        template_name='authentication/password_change_form.html',form_class=CrispyPasswordChangeForm),
        name='password_change'),
    url(r'password_change/done/$',
        auth_views.PasswordChangeDoneView.as_view(
            template_name='authentication/password_change_done.html'),
        name='password_change_done'),
    url(r'password_reset/$',
        auth_views.PasswordResetView.as_view(
            template_name='authentication/password_reset_form.html',
            form_class=CrispyPasswordResetForm),
        name='password_reset'),
    url(r'password_reset/done/$',
        auth_views.PasswordResetDoneView.as_view(
            template_name='authentication/password_reset_done.html'),
        name='password_reset_done'),
    url(r'reset/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$',
        auth_views.PasswordResetConfirmView.as_view(
            template_name='authentication/password_reset_confirm.html',
            form_class=CrispySetPasswordForm),
        name='password_reset_confirm'),
    url(r'reset/done/$', auth_views.PasswordResetCompleteView.as_view(
        template_name='authentication/password_reset_complete.html'),
        name='password_reset_complete'),
    ]
