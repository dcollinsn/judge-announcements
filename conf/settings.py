"""
Django settings for judge_announcements project.

Generated by 'django-admin startproject' using Django 2.1.7.

For more information on this file, see
https://docs.djangoproject.com/en/2.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/2.1/ref/settings/
"""

import os

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/2.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'gh5)&xhoou8d78$1vlogh$)--kssr1kxd32pxs*@ty%1ly^l9%'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_q',
    'mozilla_django_oidc',
    'announcements',
]

AUTHENTICATION_BACKENDS = (
    'announcements.oidc_config.MyOIDCAB',
    'django.contrib.auth.backends.ModelBackend',
)

OIDC_RP_SIGN_ALGO = "RS256"
OIDC_OP_AUTHORIZATION_ENDPOINT = "https://apps.magicjudges.org/openid/authorize"
OIDC_OP_TOKEN_ENDPOINT = "https://apps.magicjudges.org/openid/token"
OIDC_OP_USER_ENDPOINT = "https://apps.magicjudges.org/openid/userinfo"
OIDC_OP_JWKS_ENDPOINT = "https://apps.magicjudges.org/openid/jwks"
OIDC_RP_SCOPES = "openid profile email"
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'


MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'urls'

CACHES = {
    'default': {
        'BACKEND': "django_redis.cache.RedisCache",
        'LOCATION': "redis://127.0.0.1:6379/2",
        'OPTIONS': {
            'CLIENT_CLASS': "django_redis.client.DefaultClient",
        }
    }
}

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            os.path.abspath(os.path.join(BASE_DIR, 'templates')),
        ],
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

# Django-Q uses the same Redis cache connection for communication, and is used
# to handle async tasks or periodic jobs.
Q_CLUSTER = {
    'workers': 1,
    'queue_limit': 16,
    'catch_up': False,
    'django_redis': 'default',
}

WSGI_APPLICATION = 'wsgi.application'


# Database
# https://docs.djangoproject.com/en/2.1/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}


# Internationalization
# https://docs.djangoproject.com/en/2.1/topics/i18n/

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_L10N = True
USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.1/howto/static-files/

STATIC_URL = '/static/'

# Client IDs and secrets for the various OpenID things. We need to create these
# settings so that other developers / CI tools won't throw errors, developers
# should insert their own secrets in conf/dev_settings.py.
OIDC_RP_CLIENT_ID = ''
OIDC_RP_CLIENT_SECRET = ''

SLACK_CLIENT_ID = ''
SLACK_CLIENT_SECRET = ''
