import socket
from .base import *
DEBUG = False
# We could use the default path but make it explicit for clarity
env_path = os.path.join(BASE_DIR, "mysite", "settings", ".env")
environ.Env.read_env(env_path)

DATABASES = {'default': env.db_url('DATABASE_URL')}

ALLOWED_HOSTS = ['139.59.185.182']
SECURE_SSL_REDIRECT = False

TEMPLATES[0]['OPTIONS']['debug'] = DEBUG

SECRET_KEY = env.str('SECRET_KEY')
GO_CARDLESS = env.dict('GO_CARDLESS_SANDBOX')
BEE_FREE_ID = env.str('BEE_FREE_ID')
BEE_FREE_SECRET = env.str('BEE_FREE_SECRET')
ANYMAIL = env.dict('ANYMAIL')