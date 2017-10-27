from .base import *
SITE_NAME = "Sandbox"
DEBUG = False

# We could use the default path but make it explicit for clarity
env_path = os.path.join(BASE_DIR, "mysite", "settings", ".env")
environ.Env.read_env(env_path)

if DEBUG:
    INSTALLED_APPS += (
        'debug_toolbar',
#        'django-nose',
    )

DATABASES = {'default': env.db_url('DATABASE_URL_SANDBOX')}
ALLOWED_HOSTS = ['sandbox.coombewoodltc.com']
SECURE_SSL_REDIRECT = False

TEMPLATES[0]['OPTIONS']['debug'] = DEBUG

STATIC_ROOT = os.path.join(BASE_DIR, 'static_files/')
SECRET_KEY = env.str('SECRET_KEY')
GO_CARDLESS = env.dict('GO_CARDLESS_SANDBOX')
BEE_FREE_ID = env.str('BEE_FREE_ID')
BEE_FREE_SECRET = env.str('BEE_FREE_SECRET')

EMAIL_BACKEND = 'djcelery_email.backends.CeleryEmailBackend'
CELERY_EMAIL_BACKEND = 'anymail.backends.mailgun.MailgunBackend'
ANYMAIL = env.dict('ANYMAIL')
# TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'

RAVEN_CONFIG = {
    'dsn': env.str('RAVEN'),
}
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {  # Log to stdout
            'level': 'WARNING',
            'class': 'logging.StreamHandler',
            },
        'sentry': {
            'level': 'WARNING', # To capture more than ERROR, change to WARNING, INFO, etc.
            'class': 'raven.contrib.django.raven_compat.handlers.SentryHandler',
            'tags': {'custom-tag': 'Sandbox'},
        },
    },
    'root': {  # For dev, show errors + some info in the console
        'handlers': ['console', 'sentry'],
        'level': 'WARNING',
        },
    'loggers': {
        'django.request': {  # debug logging of things that break requests
            'handlers': ['sentry'],
            'level': 'DEBUG',
            'propagate': True,
            }
        }
    }