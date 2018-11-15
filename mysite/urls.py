from django.urls import path, re_path, include
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.staticfiles.storage import staticfiles_storage
from django_mail_viewer import urls as django_mail_viewer_urls
from django.views.generic.base import RedirectView
from wagtail.admin import urls as wagtailadmin_urls
from wagtail.documents import urls as wagtaildocs_urls
from wagtail.core import urls as wagtail_urls
from mysite.views import index_view, test_celery_view, custom_500
from members.urls import ajax_patterns, person_patterns, people_patterns, group_patterns, membership_patterns, \
    fees_patterns, sub_patterns, invoiceitem_patterns, invoice_patterns, payment_patterns, text_patterns, \
    email_patterns, mailtype_patterns
from members.views.views import *
from members.viewsets import UserViewSet, GroupViewSet, InvoiceViewSet
from rest_framework import routers

handler500 = 'mysite.views.custom_500'

admin.autodiscover()

router = routers.DefaultRouter()
router.register(r'Xusers', UserViewSet)
router.register(r'Xgroups', GroupViewSet)
router.register(r'Xinvoices', InvoiceViewSet)

urlpatterns = [
    path('', index_view, name='index'),
    path('', include('authentication.urls')),
    path('admin/', admin.site.urls),
    re_path(r'^cms/', include(wagtailadmin_urls)),
    re_path(r'^documents/', include(wagtaildocs_urls)),
    re_path(r'^pages/', include(wagtail_urls)),
    path('celery', test_celery_view, name='celery'),
    path('mv/', include(django_mail_viewer_urls)),
    path('api/', include(router.urls)),
    # Apps
    path('public/', include('public.urls')),
    path('pos/', include('pos.urls')),
    path('club/', include('club.urls')),
    path('cardless/', include('cardless.urls')),
    path('wimbledon/', include('wimbledon.urls')),
    path('events/', include('events.urls')),
    path('diary/', include('diary.urls')),
    # Members app
    path('home/', HomeView.as_view(), name='home'),
    path('ajax/', include(ajax_patterns)),
    path('person/', include(person_patterns)),
    path('people/', include(people_patterns)),
    path('group/', include(group_patterns)),
    path('membership/', include(membership_patterns)),
    path('fees/', include(fees_patterns)),
    path('sub/', include(sub_patterns)),
    path('invoiceitem/', include(invoiceitem_patterns)),
    path('invoice/', include(invoice_patterns)),
    path('payment/', include(payment_patterns)),
    path('text/', include(text_patterns)),
    path('email/', include(email_patterns)),
    path('mailtype/', include(mailtype_patterns)),

    path('search/person/', search_person, name='search-person'),

    # YEAR END
    path('yearend/', YearEndView.as_view(), name='yearend'),
    path('yearend/year/', ChangeYearView.as_view(), name='yearend-year'),


    #    path('report_builder/', include('report_builder.urls')),
    #    path('rest/', include('rest_framework.urls', namespace='rest_framework')),
    # CAMPAIGNS

    # path('mailcampaign/create/', MailCampaignCreateView.as_view(), name='mail-campaign-create'),
    # path('mailcampaign/bee/<int:pk>/', MailCampaignBeeView.as_view(), name='mail-campaign-bee'),
    # path('MailCampaign/update/<int:pk>/', MailCampaignUpdateView.as_view(), name='mail-campaign-update'),
    # path('mailcampaign/<int:pk>/', MailCampaignDetailView.as_view(), name='mail-campaign-detail'),
    # path('mailcampaign/list/', MailCampaignListView.as_view(), name='mail-campaign-list'),
    # path('bee/', bee_test, name='bee'),

    # EXCEL IMPORT AND EXPORT
    path('import/', ImportExcelView.as_view(), name='import'),
    path('select/sheets/', SelectSheets.as_view(), name='select-sheets'),
    path('export/', export, name='export'),
    path('export/<str:option>/', PersonExportView.as_view(), name='export-option'),
    path('person/export', PersonExportView.as_view(), name='person-export'),



    # https://realfavicongenerator.net
    path('favicon.ico/',
         RedirectView.as_view(url=staticfiles_storage.url('favicons/favicon.ico'))),
    path('favicon-32x32.png/',
         RedirectView.as_view(url=staticfiles_storage.url('favicons/favicon-32x32.png'))),
    path('apple-touch-icon.png/',
         RedirectView.as_view(url=staticfiles_storage.url('favicons/apple-touch-icon.png'))),
    path('site.webmanifest/',
         RedirectView.as_view(url=staticfiles_storage.url('favicons/site.webmanifest'))),
    path('android-chrome-192x192.png/',
         RedirectView.as_view(url=staticfiles_storage.url('favicons/android-chrome-192x192.png'))),
    path('android-chrome-256x256.png/',
         RedirectView.as_view(url=staticfiles_storage.url('favicons/android-chrome-256x256.png'))),
    path('browserconfig.xml/',
         RedirectView.as_view(url=staticfiles_storage.url('favicons/browserconfig.xml'))),
    path('mstile-150x150.png/',
         RedirectView.as_view(url=staticfiles_storage.url('favicons/mstile-150x150.png'))),
    path('safari-pinned-tab.svg/',
         RedirectView.as_view(url=staticfiles_storage.url('favicons/safari-pinned-tab.svg'))),
]

if settings.DEBUG:
    import debug_toolbar
    urlpatterns += [(path('__debug__/', include(debug_toolbar.urls)))]
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
