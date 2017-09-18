import socket
from .base import *
DEBUG = True
# We could use the default path but make it explicit for clarity
env_path = os.path.join(BASE_DIR, "mysite", "settings", ".env")
environ.Env.read_env(env_path)

DATABASES = {'default': env.db_url('DATABASE_URL_SANDBOX')}

ALLOWED_HOSTS = ['sandbox.coombewoodltc.com']
SECURE_SSL_REDIRECT = True

TEMPLATES[0]['OPTIONS']['debug'] = DEBUG

STATIC_ROOT = os.path.join(BASE_DIR, 'static_files/')
SECRET_KEY = env.str('SECRET_KEY')
GO_CARDLESS = env.dict('GO_CARDLESS_SANDBOX')
BEE_FREE_ID = env.str('BEE_FREE_ID')
BEE_FREE_SECRET = env.str('BEE_FREE_SECRET')

EMAIL_BACKEND = 'django_mail_viewer.backends.locmem.EmailBackend'
ANYMAIL = env.dict('ANYMAIL')
