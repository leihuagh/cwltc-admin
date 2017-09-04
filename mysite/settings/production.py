import socket
from .base import *
DEBUG = False
env_path = os.path.join(BASE_DIR, "data", ".env")
environ.Env.read_env(env_path)

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
GO_CARDLESS = env.dict('GO_CARDLESS_PRODUCTION')
BEE_FREE_ID = env.str('BEE_FREE_ID')
BEE_FREE_SECRET = env.str('BEE_FREE_SECRET')
ANYMAIL = env.dict('ANYMAIL')