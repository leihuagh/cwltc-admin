from .base import *
DEBUG = False
SITE_NAME = ""
# We could use the default path but make it explicit for clarity
env_path = os.path.join(BASE_DIR, "mysite", "settings", ".env")
environ.Env.read_env(env_path)

DATABASES = {'default': env.db_url('DATABASE_URL')}

ALLOWED_HOSTS = ['www.coombewoodltc.com', 'coombewoodltc.com', '46.101.49.99']
SECURE_SSL_REDIRECT = True

TEMPLATES[0]['OPTIONS']['debug'] = DEBUG

STATIC_ROOT = os.path.join(BASE_DIR, 'static_files/')
SECRET_KEY = env.str('SECRET_KEY')
# GO_CARDLESS = env.dict('GO_CARDLESS')
BEE_FREE_ID = env.str('BEE_FREE_ID')
BEE_FREE_SECRET = env.str('BEE_FREE_SECRET')

EMAIL_BACKEND = 'djcelery_email.backends.CeleryEmailBackend'
CELERY_EMAIL_BACKEND = 'anymail.backends.mailgun.MailgunBackend'
ANYMAIL = env.dict('ANYMAIL')
CARDLESS_ACCESS_TOKEN = env.str('CARDLESS_PRODUCTION_TOKEN')
CARDLESS_ENVIRONMENT = 'live'
CARDLESS_WEBHOOK_SECRET = env.str('CARDLESS_WEBHOOK_SECRET')

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
            'tags': {'custom-tag': 'Production'},
        },
    },
    'root': {  # For dev, show errors + some info in the console
        'handlers': ['console', 'sentry'],
        'level': 'WARNING',
        },
    'loggers': {
        'django.request': {  # debug logging of things that break requests
            'handlers': ['sentry'],
            'level': 'WARNING',
            'propagate': True,
            }
        }
    }
