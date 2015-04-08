"""
Django settings for Cwltc project.
"""
from os import path, environ
from socket import gethostname

PROJECT_ROOT = path.dirname(path.abspath(path.dirname(__file__)))

# openshift is our PAAS for now.
ON_PAAS = 'OPENSHIFT_REPO_DIR' in environ
ON_AZURE = 'ON_AZURE' in environ
REMOTE_OPENSHIFT = False
#ON_AZURE = True
if ON_PAAS:
    SECRET_KEY = environ['OPENSHIFT_SECRET_TOKEN']
else:
    SECRET_KEY = 'n(bd1f1c%e8=_xad02x5qtfn%wgwpi492e$8_erx+d)!tpeoim'

# SECURITY WARNING: don't run with debug turned on in production!
# adjust to turn off when on Openshift, but allow an environment variable to override on PAAS
DEBUG = not ON_PAAS
DEBUG = DEBUG or 'DEBUG' in environ
if ON_PAAS and DEBUG:
    print("*** Warning - Debug mode is on ***")

TEMPLATE_DEBUG = DEBUG

if ON_PAAS:
    ALLOWED_HOSTS = [environ['OPENSHIFT_APP_DNS'], gethostname()]
else:
    ALLOWED_HOSTS = ('localhost',)

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

if ON_PAAS:
    # determine if we are on MySQL or POSTGRESQL
    if "OPENSHIFT_POSTGRESQL_DB_USERNAME" in environ: 
    
        DATABASES = {
            'default': {
                'ENGINE': 'django.db.backends.postgresql_psycopg2',  
                'NAME':     environ['OPENSHIFT_APP_NAME'],
                'USER':     environ['OPENSHIFT_POSTGRESQL_DB_USERNAME'],
                'PASSWORD': environ['OPENSHIFT_POSTGRESQL_DB_PASSWORD'],
                'HOST':     environ['OPENSHIFT_POSTGRESQL_DB_HOST'],
                'PORT':     environ['OPENSHIFT_POSTGRESQL_DB_PORT'],
            }
        }  
        
elif REMOTE_OPENSHIFT:
    DATABASES = {
        'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'members',
        'USER': 'adminp86pk7r',
        'PASSWORD': 'xcrTf6-cABCY',
        'HOST': '127.0.0.1',
        'PORT': '5433',
        }
    }
       
elif ON_AZURE:

    DATABASES = {
        'default': {
        'ENGINE': 'sql_server.pyodbc',
        'NAME': 'members',
        'USER': 'is@ktconsultants.co.uk@j92m2lkhsp',
        'PASSWORD': 'Namibia2014',
        'HOST': 'j92m2lkhsp.database.windows.net',
        'PORT': '',
        'OPTIONS': {
            'driver': 'SQL Server Native Client 11.0',
            }
        }
    }
else:   
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql_psycopg2',
            'NAME': 'cwltc',
            'USER': 'django',
            'PASSWORD': 'cwltc',
            'HOST': '',
            'PORT': '',
            }
        }

LOGIN_URL = '/login'

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'Europe/London'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-uk'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = False

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale.
USE_L10N = True

# If you set this to False, Django will not use timezone-aware datetimes.
USE_TZ = True

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/media/"
MEDIA_ROOT = path.join(PROJECT_ROOT, 'media').replace('\\', '/')
if ON_PAAS:
    MEDIA_ROOT = path.join(PROJECT_ROOT, 'wsgi', 'media').replace('\\', '/')

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
MEDIA_URL = '/media/'


# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/home/media/media.lawrence.com/static/"
# https://docs.djangoproject.com/en/1.6/howto/static-files/

STATIC_ROOT = path.join(PROJECT_ROOT, 'static').replace('\\', '/')
if ON_PAAS:
    STATIC_ROOT = path.join(PROJECT_ROOT, 'wsgi', 'static').replace('\\', '/')

# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"
STATIC_URL = '/static/'

# Additional locations of static files
STATICFILES_DIRS = (
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)



# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    # Uncomment the next line for simple clickjacking protection:
    # 'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'Cwltc.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'Cwltc.wsgi.application'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or
    # "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # next line changed for Djrill
    # was 'django.contrib.admin',
    'django.contrib.admin.apps.SimpleAdminConfig',
    'debug_toolbar',
    'import_export',
    'crispy_forms',
    'djrill',
    'jquery_ui',
    'django-extensions',
    'members',  
    # Uncomment the next line to enable admin documentation:
    # 'django.contrib.admindocs',
)

# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error when DEBUG=False.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler'
        }
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
    }
}

# Specify the default test runner.
TEST_RUNNER = 'django.test.runner.DiscoverRunner'

# LIST: https://docs.djangoproject.com/en/dev/ref/templates/builtins/#date
DATE_FORMAT = 'd-m-Y'
TIME_FORMAT = 'H:i'
DATETIME_FORMAT = 'd-m-Y H:i'
YEAR_MONTH_FORMAT = 'F Y'
MONTH_DAY_FORMAT = 'F j'
SHORT_DATE_FORMAT = 'd/m/Y'
SHORT_DATETIME_FORMAT = 'd/m/Y P'
FIRST_DAY_OF_WEEK = 1

# BUT here use the Python strftime format syntax,
# LIST: http://docs.python.org/library/datetime.html#strftime-strptime-behavior

DATE_INPUT_FORMATS = (
    '%d-%m-%Y',    # '21-03-2014'
    '%d/%m/%Y',    # '21/03/2014'
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

CRISPY_TEMPLATE_PACK = 'bootstrap3'

# Configuration for Djrill
MANDRILL_API_KEY = "GlGcSfGZhHlpO75odVYTAQ"
EMAIL_BACKEND = "djrill.mail.backends.djrill.DjrillBackend"