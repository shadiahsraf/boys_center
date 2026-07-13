import os
from pathlib import Path
from urllib.parse import urlparse

# Load .env from BASE_DIR if present (dev-friendly)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = os.environ.get(
    'DJANGO_SECRET_KEY',
    'django-insecure-boys-center-development-key-change-in-production',
)
DEBUG = os.environ.get('DJANGO_DEBUG', 'true').lower() in ('1', 'true', 'yes', 'on')
ALLOWED_HOSTS = [h.strip() for h in os.environ.get('DJANGO_ALLOWED_HOSTS', '*').split(',') if h.strip()]

# ─── CSRF ────────────────────────────────────────────────────────────────
# Django 4.0+ checks the Origin header on every state-changing request.
# By default we trust the common local-dev origins. Set
# DJANGO_CSRF_TRUSTED_ORIGINS=https://example.com,http://192.168.1.10:8000
# to add more (comma-separated). Always include the scheme.
_default_csrf = (
    'http://localhost:8000,http://127.0.0.1:8000,'
    'http://localhost,http://127.0.0.1'
)
CSRF_TRUSTED_ORIGINS = [
    o.strip()
    for o in os.environ.get('DJANGO_CSRF_TRUSTED_ORIGINS', _default_csrf).split(',')
    if o.strip()
]

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'users',
    'attendance',
    'evaluations',
    'sports',
    'events',
    'news',
    'reports',
    'notifications',
    'quiz',
    'dailychallenge',
    'ratings',
]

# Order matters - LocaleMiddleware must come AFTER SessionMiddleware and BEFORE CommonMiddleware
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.i18n',
                'users.context_processors.user_role_context',
                'notifications.context_processors.notifications',
                'quiz.context_processors.quiz_streak',
                'dailychallenge.context_processors.daily_challenge',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# ─── DATABASE ─────────────────────────────────────────────────────────────
# Priority:
#   1. DATABASE_URL  (postgres://user:pass@host:port/dbname)  — easiest, deploy-friendly
#   2. discrete DB_* env vars (DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT)
#   3. fall back to local SQLite for dev convenience
def _build_databases():
    url = os.environ.get('DATABASE_URL', '').strip()
    if url:
        u = urlparse(url)
        engine_map = {
            'postgres': 'django.db.backends.postgresql',
            'postgresql': 'django.db.backends.postgresql',
            'mysql': 'django.db.backends.mysql',
            'sqlite': 'django.db.backends.sqlite3',
        }
        engine = engine_map.get(u.scheme, 'django.db.backends.postgresql')
        return {
            'default': {
                'ENGINE': engine,
                'NAME': (u.path or '').lstrip('/') or 'postgres',
                'USER': u.username or '',
                'PASSWORD': u.password or '',
                'HOST': u.hostname or 'localhost',
                'PORT': str(u.port) if u.port else '5432',
                'CONN_MAX_AGE': 60,
            }
        }

    if os.environ.get('DB_NAME'):
        return {
            'default': {
                'ENGINE': os.environ.get('DB_ENGINE', 'django.db.backends.postgresql'),
                'NAME': os.environ['DB_NAME'],
                'USER': os.environ.get('DB_USER', ''),
                'PASSWORD': os.environ.get('DB_PASSWORD', ''),
                'HOST': os.environ.get('DB_HOST', 'localhost'),
                'PORT': os.environ.get('DB_PORT', '5432'),
                'CONN_MAX_AGE': 60,
            }
        }

    # Dev fallback — SQLite at <project>/db.sqlite3
    return {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }


DATABASES = _build_databases()

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
     'OPTIONS': {'min_length': 6}},
]

AUTH_USER_MODEL = 'users.User'
LOGIN_URL = '/ar/auth/login/'
LOGIN_REDIRECT_URL = '/ar/dashboard/'
LOGOUT_REDIRECT_URL = '/ar/auth/login/'

# Arabic is the primary language; English is available as a toggle.
LANGUAGE_CODE = 'ar'
TIME_ZONE = 'Africa/Cairo'
USE_I18N = True
USE_L10N = True
USE_TZ = True

LANGUAGES = [
    ('ar', 'العربية'),
    ('en', 'English'),
]
LOCALE_PATHS = [BASE_DIR / 'locale']

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Session settings
SESSION_COOKIE_AGE = 86400 * 7
SESSION_SAVE_EVERY_REQUEST = True
