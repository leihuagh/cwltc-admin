import os
from django.core.exceptions import ImproperlyConfigured
import environ


def get_env_variable(var_name):
    """Get the environment variable or return an exception. (2 scoops page 47)"""
    try:
        return os.environ[var_name]
    except KeyError:
        error_msg = "Set the %s environment variable" % var_name
        raise ImproperlyConfigured(error_msg)


root = environ.Path(__file__) - 3  # three folder back (/a/b/c/ - 3 = /)
env = environ.Env(DEBUG=(bool, False), )  # set default values and casting

BASE_DIR = str(root)

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'

# This is where the static files get served from
STATIC_ROOT = os.path.join(BASE_DIR, 'wsgi', 'static')

INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.admin.apps.SimpleAdminConfig',
    'formtools',
    'import_export',
    'crispy_forms',
    'django_extensions',
    'widget_tweaks',
    'rest_framework',
#    'report_builder',
    'anymail',
    'django_tables2',
    'djcelery_email',
    'cookielaw',
    'taggit',
    'members',
    'pos',
    'public',
    'club',
    'authentication',
    'cardless',
    'wimbledon',
    'events'
]

MIDDLEWARE = [
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.security.SecurityMiddleware',
]

REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': ('rest_framework.permissions.IsAdminUser',),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.LimitOffsetPagination',
    'PAGE_SIZE': 10
}

SESSION_SERIALIZER = 'django.contrib.sessions.serializers.PickleSerializer'

ROOT_URLCONF = 'mysite.urls'

STATICFILES_FINDERS = [
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder'
]
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, "static")
]

MEDIA_ROOT = os.path.join(BASE_DIR, "media")

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            os.path.join(BASE_DIR, 'templates')
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'debug': False,
            'context_processors': [
                # Insert your TEMPLATE_CONTEXT_PROCESSORS here or use this
                # list if you haven't customized them:
                'django.contrib.auth.context_processors.auth',
                'django.template.context_processors.debug',
                'django.template.context_processors.i18n',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
                'django.template.context_processors.tz',
                'django.template.context_processors.request',
                'django.contrib.messages.context_processors.messages',
                'mysite.context_processors.site_name',
            ],
        },
    },
]


# Internationalization
# https://docs.djangoproject.com/en/1.6/topics/i18n/
LANGUAGE_CODE = 'en-uk'
TIME_ZONE = 'Europe/London'
USE_I18N = False
USE_L10N = False
USE_TZ = True

# LIST: https://docs.djangoproject.com/en/dev/ref/templates/builtins/#date
DATE_FORMAT = 'd/m/Y'
TIME_FORMAT = 'H:i'
DATETIME_FORMAT = 'd/m/Y H:i'
YEAR_MONTH_FORMAT = 'F Y'
MONTH_DAY_FORMAT = 'F j'
SHORT_DATE_FORMAT = 'd/m/Y'
SHORT_DATETIME_FORMAT = 'd/m/Y H:i'
FIRST_DAY_OF_WEEK = 1

# BUT here use the Python strftime format syntax,
# LIST: http://docs.python.org/library/datetime.html#strftime-strptime-behavior

DATE_INPUT_FORMATS = (
    '%d/%m/%Y',  # '21/03/2014'
    '%d-%m-%Y',  # '21-03-2014'
    '%d/%m/%y',  # '21/03/14'
    '%d %b &Y',  # '21 Mar 2014'
    '%d %B &Y',  # '21 March 2014'
)
TIME_INPUT_FORMATS = (
    '%H:%M:%S',  # '17:59:59'
    '%H:%M',  # '17:59'
)
DATETIME_INPUT_FORMATS = (
    '%d-%m-%Y %H:%M',  # '21-03-2014 17:59'
)

DECIMAL_SEPARATOR = u'.'
THOUSAND_SEPARATOR = u','
NUMBER_GROUPING = 3

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'members.validators.OneAlphaAndOneNumericValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
]

LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/club/'

CRISPY_TEMPLATE_PACK = 'bootstrap4'
DJANGO_TABLES2_TEMPLATE = 'django_tables2/bootstrap.html'

# EMAIL_BACKEND is defined in site specific settings

DEFAULT_FROM_EMAIL = 'Coombe Wood LTC <subs@coombewoodltc.co.uk>'
SUBS_EMAIL = 'subs@coombewoodltc.co.uk'
INFO_EMAIL = 'info@coombewoodltc.co.uk'
TEST_EMAIL = 'is@ktconsultants.co.uk'
ADMINS = (('membership_secretary', 'membership@coombewoodltc.co.uk'),)
MANAGERS = ADMINS


