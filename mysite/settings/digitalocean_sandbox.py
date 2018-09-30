from .base import *
SITE_NAME = "Sandbox"
DEBUG = False
LIVE_GO_CARDLESS = True
LIVE_MAIL = True

# We could use the default path but make it explicit for clarity
env_path = os.path.join(BASE_DIR, "mysite", "settings", ".env")
environ.Env.read_env(env_path)

if DEBUG:
    INSTALLED_APPS += (
        'debug_toolbar',
#        'django-nose',
    )

DATABASES = {'default': env.db_url('DATABASE_URL_SANDBOX')}
ALLOWED_HOSTS = ['sandbox.coombewoodltc.com', 'coombewoodltc.com', '46.101.49.99']
SECURE_SSL_REDIRECT = False

TEMPLATES[0]['OPTIONS']['debug'] = DEBUG

STATIC_ROOT = os.path.join(BASE_DIR, 'static_files/')
SECRET_KEY = env.str('SECRET_KEY')

BEE_FREE_ID = env.str('BEE_FREE_ID')
BEE_FREE_SECRET = env.str('BEE_FREE_SECRET')


if LIVE_MAIL:
    print('Warning - Live mail')
    EMAIL_BACKEND = "anymail.backends.mailgun.EmailBackend"
    ANYMAIL = env.dict('ANYMAIL')
else:
    EMAIL_BACKEND = 'django_mail_viewer.backends.locmem.EmailBackend'
    INSTALLED_APPS += ('django_mail_viewer',)
# Mails go to dummy
# EMAIL_BACKEND = 'django.core.mail.backends.dummy.EmailBackend'


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

BROKER_URL = env.str('BROKER_URL_SANDBOX')

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
        # stop sentry logging disallowed host
        'django.security.DisallowedHost': {
            'handlers': ['console'],
            'propagate': False,
        },
        'django.request': {  # debug logging of things that break requests
            'handlers': ['sentry'],
            'level': 'DEBUG',
            'propagate': True,
            }
        }
    }