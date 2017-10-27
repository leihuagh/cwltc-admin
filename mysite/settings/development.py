from .base import *
SITE_NAME = "Development"
DEBUG = True
# We could use the default path but make it explicit for clarity
env_path = os.path.join(BASE_DIR, "mysite", "settings", ".env")
environ.Env.read_env(env_path)

INSTALLED_APPS += (
    'coverage',
#    'django-nose',
#    'debug_toolbar',
    )

# MIDDLEWARE_CLASSES += ('debug_toolbar.middleware.DebugToolbarMiddleware', )

DATABASES = {'default': env.db_url('DATABASE_URL')}

ALLOWED_HOSTS = ['55015a7c.ngrok.io', 'localhost']

TEMPLATES[0]['OPTIONS']['debug'] = DEBUG

SECRET_KEY = env.str('SECRET_KEY')
GO_CARDLESS = env.dict('GO_CARDLESS_SANDBOX')
BEE_FREE_ID = env.str('BEE_FREE_ID')
BEE_FREE_SECRET = env.str('BEE_FREE_SECRET')

EMAIL_BACKEND = 'django_mail_viewer.backends.locmem.EmailBackend'
ANYMAIL = env.dict('ANYMAIL')

CARDLESS_ACCESS_TOKEN = env.str('CARDLESS_ACCESS_TOKEN')
CARDLESS_ENVIRONMENT = 'sandbox'
CARDLESS_WEBHOOK_SECRET = env.str('CARDLESS_WEBHOOK_SECRET')
TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'

LOG_DIR = os.path.join(BASE_DIR, "logs")

# http://cheat.readthedocs.io/en/latest/django/logging.html
# https://www.webforefront.com/django/setupdjangologging.html
RAVEN_CONFIG = {
    'dsn': env.str('RAVEN'),
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
        'level': 'ERROR',
        },
    'loggers': {
        'django.request': {  # debug logging of things that break requests
            'handlers': [],
            'level': 'INFO',
            'propagate': True,
            }
        }
    }
