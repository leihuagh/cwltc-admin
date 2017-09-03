from .base import *
DEBUG = True

INSTALLED_APPS += (
    'debug_toolbar',
    'django_nose',
)

MIDDLEWARE_CLASSES += ('debug_toolbar.middleware.DebugToolbarMiddleware', )

DATABASES = {'default': env.db_url('DATABASE_URL')}

SECRET_KEY = env.str('SECRET_KEY')

ALLOWED_HOSTS = []

TEMPLATES[0]['OPTIONS']['debug'] = DEBUG

GO_CARDLESS = env.dict('GO_CARDLESS_SANDBOX')