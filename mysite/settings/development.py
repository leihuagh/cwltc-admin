from .base import *
import logging

SITE_NAME = "Development"
DEBUG = True
DEBUG_TOOLBAR = False
LIVE_GO_CARDLESS = True


# We could use the default path but make it explicit for clarity
env_path = os.path.join(BASE_DIR, "mysite", "settings", ".env")
environ.Env.read_env(env_path)

INSTALLED_APPS += [
    'django_mail_viewer',
    'raven.contrib.django.raven_compat',
    'coverage',
#    'django-nose',
    ]

if DEBUG_TOOLBAR:
    INSTALLED_APPS += ['debug_toolbar']
    MIDDLEWARE.insert(0, 'debug_toolbar.middleware.DebugToolbarMiddleware')
    INTERNAL_IPS = ['127.0.0.1']

DATABASES = {'default': env.db_url('DATABASE_URL_DEV')}

ALLOWED_HOSTS = ['55015a7c.ngrok.io', 'localhost']

TEMPLATES[0]['OPTIONS']['debug'] = DEBUG

AUTH_PASSWORD_VALIDATORS = []

SECRET_KEY = env.str('SECRET_KEY')
# GO_CARDLESS = env.dict('GO_CARDLESS_SANDBOX')
BEE_FREE_ID = env.str('BEE_FREE_ID')
BEE_FREE_SECRET = env.str('BEE_FREE_SECRET')

EMAIL_BACKEND = 'django_mail_viewer.backends.locmem.EmailBackend'
ANYMAIL = env.dict('ANYMAIL')


if LIVE_GO_CARDLESS:
    CARDLESS_ACCESS_TOKEN = env.str('CARDLESS_PRODUCTION_TOKEN')
    CARDLESS_ENVIRONMENT = 'live'
    CARDLESS_WEBHOOK_SECRET = env.str('CARDLESS_WEBHOOK_SECRET')
    print('WARNING - LIVE Go Cardless site')
else:
    CARDLESS_ACCESS_TOKEN = env.str('CARDLESS_SANDBOX_TOKEN')
    CARDLESS_ENVIRONMENT = 'sandbox'
    CARDLESS_WEBHOOK_SECRET = env.str('CARDLESS_WEBHOOK_SECRET')



TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'

LOG_DIR = os.path.join(BASE_DIR, "logs")

RAVEN_CONFIG = {
    'dsn': None,
}
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {  # Log to stdout
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            },
    },
    'root': {  # For dev, show errors + some info in the console
        'handlers': ['console'],
        'level': 'INFO',
        },
    'loggers': {
        'django.request': {  # debug logging of things that break requests
            'handlers': [],
            'level': 'INFO',
            'propagate': True,
            }
        }
    }

logging.getLogger('raven').setLevel(logging.WARNING)