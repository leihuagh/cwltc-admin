import socket
from .base import *
DEBUG = 'DEBUG' in os.environ

INSTALLED_APPS += (
    'debug_toolbar',
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

SECRET_KEY = os.environ['OPENSHIFT_SECRET_TOKEN']
ALLOWED_HOSTS = [os.environ['OPENSHIFT_APP_DNS'], socket.gethostname()]
SECURE_SSL_REDIRECT = True

TEMPLATES[0]['OPTIONS']['debug'] = DEBUG

GO_CARDLESS = env.dict('GO_CARDLESS_SANDBOX')