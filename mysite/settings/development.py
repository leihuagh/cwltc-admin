from .base import *
DEBUG = True
# We could use the default path but make it explicit for clarity
env_path = os.path.join(BASE_DIR, "mysite", "settings", ".env")
environ.Env.read_env(env_path)

INSTALLED_APPS += (
    'debug_toolbar',
    'django_nose',
)

MIDDLEWARE_CLASSES += ('debug_toolbar.middleware.DebugToolbarMiddleware', )

DATABASES = {'default': env.db_url('DATABASE_URL')}

ALLOWED_HOSTS = []

TEMPLATES[0]['OPTIONS']['debug'] = DEBUG

SECRET_KEY = env.str('SECRET_KEY')
GO_CARDLESS = env.dict('GO_CARDLESS_SANDBOX')
BEE_FREE_ID = env.str('BEE_FREE_ID')
BEE_FREE_SECRET = env.str('BEE_FREE_SECRET')
ANYMAIL = env.dict('ANYMAIL')