import os
from pathlib import Path
import dj_database_url
from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env file
load_dotenv(BASE_DIR / '.env')

# Quick-start development settings - unsuitable for production
SECRET_KEY = os.environ.get(
    'SECRET_KEY',
    'django-insecure-dieta-deficit-calorico-secret-key-change-in-production'
)

DEBUG = os.environ.get('DEBUG', 'True').lower() in ('true', '1', 'yes')

# Allowed hosts: can be comma-separated list
allowed_hosts_env = os.environ.get('ALLOWED_HOSTS', '')
if allowed_hosts_env:
    ALLOWED_HOSTS = [h.strip() for h in allowed_hosts_env.split(',') if h.strip()]
    if 'testserver' not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append('testserver')
else:
    ALLOWED_HOSTS = [
        'dieta.dario10.pw',
        '192.168.1.25',
        'localhost',
        '127.0.0.1',
        'testserver',
        '*'
    ]

# CSRF Trusted Origins for Cloudflare and reverse proxy
csrf_trusted_origins_env = os.environ.get('CSRF_TRUSTED_ORIGINS', '')
if csrf_trusted_origins_env:
    CSRF_TRUSTED_ORIGINS = [o.strip() for o in csrf_trusted_origins_env.split(',') if o.strip()]
else:
    CSRF_TRUSTED_ORIGINS = [
        'https://dieta.dario10.pw',
        'http://dieta.dario10.pw',
        'http://192.168.1.25:8040',
        'http://192.168.1.25:8000',
        'http://192.168.1.25',
        'http://localhost:8040',
        'http://localhost:8000',
        'http://127.0.0.1:8040',
        'http://127.0.0.1:8000'
    ]

# Cloudflare / Reverse Proxy SSL settings
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = True

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'whitenoise.runserver_nostatic',
    'django.contrib.staticfiles',
    'tracker',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
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
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# Database configuration
# 1. First check DATABASE_URL
database_url = os.environ.get('DATABASE_URL')
if database_url:
    DATABASES = {
        'default': dj_database_url.parse(database_url, conn_max_age=600)
    }
# 2. Check individual DB environment variables
elif os.environ.get('DB_NAME') and os.environ.get('DB_USER'):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.environ.get('DB_NAME', 'postgres'),
            'USER': os.environ.get('DB_USER', 'postgres'),
            'PASSWORD': os.environ.get('DB_PASSWORD', ''),
            'HOST': os.environ.get('DB_HOST', '192.168.1.25'),
            'PORT': os.environ.get('DB_PORT', '5432'),
            'CONN_MAX_AGE': 600,
        }
    }
# 3. Fallback to SQLite for local development
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# Password validation (simple registration without complexity blockers)
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 4,
        },
    },
]

# Internationalization
LANGUAGE_CODE = 'es-es'
TIME_ZONE = os.environ.get('TIME_ZONE', 'America/Argentina/Buenos_Aires')
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

# WhiteNoise compressed storage for production
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Media files (User uploads, photos)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_REDIRECT_URL = 'dashboard'
LOGOUT_REDIRECT_URL = 'login'
LOGIN_URL = 'login'
