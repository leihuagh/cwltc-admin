import socket
from .base import *
DEBUG = True # 'DEBUG' in os.environ
SITE_NAME = "Sandbox"
env_path = os.path.join(os.environ['OPENSHIFT_DATA_DIR'], ".env")
environ.Env.read_env(env_path)

INSTALLED_APPS += (
    'debug_toolbar',
    'djcelery_email'
)

MIDDLEWARE_CLASSES += ('debug_toolbar.middleware.DebugToolbarMiddleware', )

if "OPENSHIFT_POSTGRESQL_DB_USERNAME" in os.environ:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql_psycopg2',
            'NAME': os.environ['OPENSHIFT_APP_NAME'],
            'USER': os.environ['OPENSHIFT_POSTGRESQL_DB_USERNAME'],
            'PASSWORD': os.environ['OPENSHIFT_POSTGRESQL_DB_PASSWORD'],
            'HOST': os.environ['OPENSHIFT_POSTGRESQL_DB_HOST'],
            'PORT': os.environ['OPENSHIFT_POSTGRESQL_DB_PORT'],
        }
    }
else:
    error_msg = "OpenShift environment variable error"
    raise ImproperlyConfigured(error_msg)

ALLOWED_HOSTS = [os.environ['OPENSHIFT_APP_DNS'], socket.gethostname()]
SECURE_SSL_REDIRECT = True
TEMPLATES[0]['OPTIONS']['debug'] = DEBUG

SECRET_KEY = os.environ['OPENSHIFT_SECRET_TOKEN']
GO_CARDLESS = env.dict('GO_CARDLESS_SANDBOX')
BEE_FREE_ID = env.str('BEE_FREE_ID')
BEE_FREE_SECRET = env.str('BEE_FREE_SECRET')

EMAIL_BACKEND = 'djcelery_email.backends.CeleryEmailBackend'

CELERY_EMAIL_BACKEND = 'anymail.backends.mailgun.MailgunBackend'

ANYMAIL = env.dict('ANYMAIL')