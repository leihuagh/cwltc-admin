# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
import socket

BASE_DIR = os.path.dirname(os.path.dirname(__file__))

# openshift is our PAAS for now.
ON_PAAS = 'OPENSHIFT_REPO_DIR' in os.environ
REMOTE_ADMIN = False
REMOTE_SANDBOX = False

PRODUCTION = False

if ON_PAAS:
    DEBUG = 'DEBUG' in os.environ
    SECRET_KEY = os.environ['OPENSHIFT_SECRET_TOKEN']
    ALLOWED_HOSTS = [os.environ['OPENSHIFT_APP_DNS'], socket.gethostname()]
    SECURE_SSL_REDIRECT = True
    if os.environ['OPENSHIFT_APP_NAME'] == "admin":
        PRODUCTION = True
        #DEBUG = False
else:
    DEBUG = True
    SECRET_KEY = ')_7av^!cy(wfx=k#3*7x+(=j^fzv+ot^1@sh9s9t=8$bu@r(z$'
    ALLOWED_HOSTS = []
    DIGITAL_OCEAN = False
if ON_PAAS and DEBUG:
    print("*** Warning - Debug mode is on ***")

# Application definition
INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.admin.apps.SimpleAdminConfig',
    'debug_toolbar',
    'formtools',
    'import_export',
    'crispy_forms',
    'django_extensions',
    'widget_tweaks',
    'rest_framework',
    'report_builder',
    'anymail',
    'django_mail_viewer',
    'django_tables2',
    'coverage',
	'members',
    'gc_app',
    'pos',
    'public',
    'club',
    'authentication',
    'django_nose',
)

MIDDLEWARE_CLASSES = (
    'debug_toolbar.middleware.DebugToolbarMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.security.SecurityMiddleware',
)

REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': ('rest_framework.permissions.IsAdminUser',),
    'PAGE_SIZE': 10
}

SESSION_SERIALIZER = 'django.contrib.sessions.serializers.PickleSerializer'

ROOT_URLCONF = 'mysite.urls'

# Database
# https://docs.djangoproject.com/en/1.6/ref/settings/#databases

if ON_PAAS:
    if "OPENSHIFT_POSTGRESQL_DB_USERNAME" in os.environ: 
    
        DATABASES = {
            'default': {
                'ENGINE': 'django.db.backends.postgresql_psycopg2',  
                'NAME':     os.environ['OPENSHIFT_APP_NAME'],
                'USER':     os.environ['OPENSHIFT_POSTGRESQL_DB_USERNAME'],
                'PASSWORD': os.environ['OPENSHIFT_POSTGRESQL_DB_PASSWORD'],
                'HOST':     os.environ['OPENSHIFT_POSTGRESQL_DB_HOST'],
                'PORT':     os.environ['OPENSHIFT_POSTGRESQL_DB_PORT'],
            }
        } 
elif REMOTE_ADMIN:
    # local app with connection to live system
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql_psycopg2',
            'NAME': 'admin',
            'USER': 'admin3vrx6bg',
            'PASSWORD': 'PED2kJfZ8DWL',
            'HOST': '127.0.0.1',
            'PORT': '5433',
            }
        }  
elif REMOTE_SANDBOX:
    # local app with connection to remote sandbox
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql_psycopg2',
            'NAME': 'sandbox',
            'USER': 'adminrzfhei2',
            'PASSWORD': 'M4lhCiAkIV-_',
            'HOST': '127.0.0.1',
            'PORT': '5433',
            }
        }
elif DIGITAL_OCEAN:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql_psycopg2',
            'NAME': 'admin',
            'USER': 'django',
            'PASSWORD': '302453b9eabd041c355eda462965bc2a',
            'HOST': '139.59.185.182',
            'PORT': '5432',
            }
        } 
else:  
    # local database
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql_psycopg2',
            'NAME': 'admin',
            'USER': 'django',
            'PASSWORD': 'cwltc',
            'HOST': '',
            'PORT': '',
            }
        }

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
    '%d/%m/%Y',    # '21/03/2014'
    '%d-%m-%Y',    # '21-03-2014'
    '%d/%m/%y',    # '21/03/14'
    '%d %b &Y',    # '21 Mar 2014'
    '%d %B &Y',    # '21 March 2014'
)
TIME_INPUT_FORMATS = (
    '%H:%M:%S',     # '17:59:59'
    '%H:%M',        # '17:59'
)
DATETIME_INPUT_FORMATS = (
    '%d-%m-%Y %H:%M',     # '21-03-2014 17:59'
)

DECIMAL_SEPARATOR = u'.'
THOUSAND_SEPARATOR = u','
NUMBER_GROUPING = 3

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'

# This is where the static files get served from
STATIC_ROOT = os.path.join(BASE_DIR, 'wsgi', 'static')

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder'
)
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, "static")
]

MEDIA_ROOT = os.environ.get('OPENSHIFT_DATA_DIR', '')

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            os.path.join(BASE_DIR, 'templates')
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'debug': DEBUG,
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
            ],
        },
    },
]

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

#LOGGING = {
#    'version': 1,
#    'disable_existing_loggers': False,
#    'formatters': {
#        'verbose': {
#            'format' : "[%(asctime)s] %(levelname)s [%(name)s:%(lineno)s] %(message)s",
#            'datefmt' : "%d/%b/%Y %H:%M:%S"
#        },
#        'simple': {
#            'format': '%(levelname)s %(message)s'
#        },
#    },
#    'handlers': {
#        'file': {
#            'level': 'DEBUG',
#            'class': 'logging.FileHandler',
#            'filename': 'admin.log',
#            'formatter': 'verbose'
#        },
#    },
#    'loggers': {
#        'django': {
#            'handlers':['file'],
#            'propagate': True,
#            'level':'DEBUG',
#        },
#        'gc_app': {
#            'handlers': ['file'],
#            'level': 'DEBUG',
#        },
#    }
#}

TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'

LOGIN_URL = '/login/'

CRISPY_TEMPLATE_PACK = 'bootstrap3'

if DEBUG:
    if ON_PAAS:
        EMAIL_BACKEND = 'anymail.backends.mailgun.MailgunBackend'
        #EMAIL_BACKEND = 'django.core.mail.backends.dummy.EmailBackend'
        #EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
    else:
        EMAIL_BACKEND = 'django_mail_viewer.backends.locmem.EmailBackend'
        #EMAIL_BACKEND = 'django.core.mail.backends.filebased.EmailBackend'
        #EMAIL_FILE_PATH = os.path.join(BASE_DIR, 'temp','emails')
        #EMAIL_BACKEND = 'anymail.backends.mailgun.MailgunBackend'
else:

    EMAIL_BACKEND = 'anymail.backends.mailgun.MailgunBackend'

DJANGO_WYSIWYG_FLAVOR = 'tinymce'

ANYMAIL = {
    "MAILGUN_API_KEY": 'key-44e941ede1264ea215021bb0b3634eb4',
}
DEFAULT_FROM_EMAIL = 'Coombe Wood LTC <subs@coombewoodltc.co.uk>'
SUBS_EMAIL = 'subs@coombewoodltc.co.uk'
INFO_EMAIL = 'info@coombewoodltc.co.uk'
TEST_EMAIL = 'is@ktconsultants.co.uk'


if PRODUCTION:
    GO_CARDLESS = {
        'ENVIRONMENT': 'production',
        'APP_ID': '8MZAE33KTS90MKJV0QDG8MC1FCG8J6P556NYQ16K0AXRR3SS5YDF1E7V1PENGHPF',
        'APP_SECRET': 'QCV54646DRQH6YMV8W2WETBN0RT003V3QPZFRMDTYW4B0HKW9455H1HB0PQ9AZ71',
        'ACCESS_TOKEN': 'YSVM80D2XAT63RY29GHCD7K34E923X80T7A1NTJVNSNK3A33YTD7PB62PH5Z8XXH',
        'MERCHANT_ID': '0VTW3337YC'
        }
else:
    GO_CARDLESS = {
        'ENVIRONMENT': 'sandbox',
        'APP_ID': '2J7RAH17Y3Q2PMGGACBJEQK4EY8X6VGXXB60D3SKR4YAAKWAV9G87K7H6BKSGKCQ',
        'APP_SECRET': 'K5NNZA4KKTSPCE2TF1PPKP41K9VMNEVWVMZGZEYQWM8T4897J1A1ZAGV6FDQ8QXT',
        'ACCESS_TOKEN': '6T93JFXX6XTS7C38XCZRWZ7379AJTXXBXE8ZC53FJMYZ0KBPG0S5S77G73N1FCX3',
        'MERCHANT_ID': '0VTW3337YC'
        }
BEE_FREE_ID = 'ab151c30-4d75-496f-b610-733eee85b12b'
BEE_FREE_SECRET = 'v5Z89TTSVNHXI4QG8DX1qRd8uYixLygn1TO8wrQy78rSWcbvtVP'

DEBUG_TOOLBAR_PATCH_SETTINGS = False
INTERNAL_IPS = ['127.0.0.1', '::1']

