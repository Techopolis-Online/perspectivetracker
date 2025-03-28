"""
For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.1/ref/settings/
"""

from pathlib import Path
import os
import dj_database_url
from dotenv import load_dotenv
from django.core.exceptions import ImproperlyConfigured
import sys

# Determine which .env file to load
ENV = os.environ.get('DJANGO_ENV', 'development')
if ENV == 'development':
    load_dotenv('.env.development')
else:
    load_dotenv('.env')

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-6a8xoo4jlia$(3f9ma^p+8lkc-)8b0up6j*-p0w$@uw=1#qc^^')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DEBUG', 'False') == 'True'

# Update ALLOWED_HOSTS to include your Heroku domain
ALLOWED_HOSTS = [
    'perspectivetracker-16b3c6ba0f46.herokuapp.com',
    'perspectivetracker.herokuapp.com',
    '.herokuapp.com',
    'localhost',
    '127.0.0.1',
]

# For better security in production environments, consider using environment variables:
# ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

# Add any additional hosts from environment variables
env_hosts = os.environ.get('ALLOWED_HOSTS', '').split(',')
ALLOWED_HOSTS.extend([host for host in env_hosts if host])


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'users',
    'clients',
    'projects',
    'social_django',
    'whitenoise.runserver_nostatic',
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
    'social_django.middleware.SocialAuthExceptionMiddleware',
]

ROOT_URLCONF = 'perspectivetracker.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            BASE_DIR / 'perspectivetracker' / 'templates',
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'social_django.context_processors.backends',
                'social_django.context_processors.login_redirect',
            ],
        },
    },
]

WSGI_APPLICATION = 'perspectivetracker.wsgi.application'


# Add logging configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'filters': {
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        },
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
            'filters': ['require_debug_true'],  # Only log to console in debug mode
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'django.log'),
            'formatter': 'verbose',
            'filters': ['require_debug_false'],  # Log to file in production
        },
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler',
            'filters': ['require_debug_false'],
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.db': {
            'handlers': ['console', 'file'],
            'level': 'INFO' if DEBUG else 'WARNING',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['console', 'file', 'mail_admins'],
            'level': 'DEBUG' if DEBUG else 'ERROR',
            'propagate': False,
        },
        'django.server': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG' if DEBUG else 'ERROR',
            'propagate': False,
        },
        'social_django': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG' if DEBUG else 'WARNING',
            'propagate': False,
        },
        'auth0_debug': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG' if DEBUG else 'ERROR',
            'propagate': False,
        },
    },
}

# Database
# https://docs.djangoproject.com/en/5.1/ref/settings/#databases

# Default to SQLite for local development
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Override with PostgreSQL if DATABASE_URL is provided (Heroku)
if 'DATABASE_URL' in os.environ:
    DATABASE_URL = os.environ.get('DATABASE_URL')
    DATABASES['default'] = dj_database_url.config(
        default=DATABASE_URL,
        conn_max_age=600,
        ssl_require=True
    )
    # Removed print statement that was showing in production logs

# Session configuration
SESSION_ENGINE = 'django.contrib.sessions.backends.db'
SESSION_COOKIE_AGE = 1209600  # 2 weeks
# Set these conditionally based on environment
SESSION_COOKIE_SECURE = not DEBUG  # Only use secure cookies in production
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_SAVE_EVERY_REQUEST = True  # Ensure sessions are created for anonymous users too

# Development overrides
if ENV == 'development':
    # Explicitly disable all SSL/HTTPS settings for local development
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False
    SECURE_SSL_REDIRECT = False
    SECURE_PROXY_SSL_HEADER = None
    SECURE_HSTS_SECONDS = 0
    SECURE_HSTS_INCLUDE_SUBDOMAINS = False
    SECURE_HSTS_PRELOAD = False
    # Remove any proxy headers that might trigger SSL
    os.environ.pop('HTTP_X_FORWARDED_PROTO', None)
    os.environ.pop('HTTPS', None)
    # Force debug mode in development
    DEBUG = True
    # Set environment variables explicitly
    os.environ['SECURE_SSL_REDIRECT'] = 'False'
    os.environ['DEBUG'] = 'True'
    # Make sure Auth0 works with HTTP
    SOCIAL_AUTH_REDIRECT_IS_HTTPS = False
    
    # Instead of custom middleware, just remove the security middleware
    MIDDLEWARE = [m for m in MIDDLEWARE if m != 'django.middleware.security.SecurityMiddleware']

# Use a more reliable session configuration for Heroku
database_url = os.environ.get('DATABASE_URL', None)
if database_url:
    # Ensure sessions use the PostgreSQL database
    SESSION_ENGINE = 'django.contrib.sessions.backends.db'
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'

# Ensure sessions are created for anonymous users too
SESSION_SAVE_EVERY_REQUEST = True

# Password validation
# https://docs.djangoproject.com/en/5.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.1/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.1/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'perspectivetracker/static'),
]

# Simplified static file serving with whitenoise
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Media files (User uploads)
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTH_USER_MODEL = 'users.CustomUser'

AUTHENTICATION_BACKENDS = [
    'social_core.backends.auth0.Auth0OAuth2',
    'django.contrib.auth.backends.ModelBackend',
]

# Auth0 Settings
SOCIAL_AUTH_AUTH0_DOMAIN = os.environ.get('AUTH0_DOMAIN')
SOCIAL_AUTH_AUTH0_KEY = os.environ.get('AUTH0_CLIENT_ID')
SOCIAL_AUTH_AUTH0_SECRET = os.environ.get('AUTH0_CLIENT_SECRET')
SOCIAL_AUTH_AUTH0_SCOPE = [
    'openid',
    'profile',
    'email'
]

# Auth0 UI customization
SOCIAL_AUTH_AUTH0_EXTRA_AUTHORIZE_PARAMS = {
    'ui_locales': 'en',
    'auth0Client': '{"name":"Perspective Tracker","version":"1.0.0"}',
    'screen_hint': 'login'
}

# Auth0 callback URL - this should match what's configured in Auth0
SOCIAL_AUTH_REDIRECT_IS_HTTPS = os.environ.get('SOCIAL_AUTH_REDIRECT_IS_HTTPS', 'False') == 'True'
SOCIAL_AUTH_LOGIN_REDIRECT_URL = '/'
SOCIAL_AUTH_LOGIN_ERROR_URL = '/login-error/'
SOCIAL_AUTH_RAISE_EXCEPTIONS = os.environ.get('SOCIAL_AUTH_RAISE_EXCEPTIONS', 'False') == 'True'

# Explicitly set the callback URL
SOCIAL_AUTH_AUTH0_REDIRECT_URI = os.environ.get('AUTH0_CALLBACK_URL', 'https://perspectivetracker-16b3c6ba0f46.herokuapp.com/users/complete/auth0/')

# Set HTTP callback URL for development
if ENV == 'development':
    # Force HTTP for development
    if SOCIAL_AUTH_AUTH0_REDIRECT_URI and SOCIAL_AUTH_AUTH0_REDIRECT_URI.startswith('https://'):
        SOCIAL_AUTH_AUTH0_REDIRECT_URI = SOCIAL_AUTH_AUTH0_REDIRECT_URI.replace('https://', 'http://')
    # Default to localhost if not set
    if not SOCIAL_AUTH_AUTH0_REDIRECT_URI or ('localhost' not in SOCIAL_AUTH_AUTH0_REDIRECT_URI and '127.0.0.1' not in SOCIAL_AUTH_AUTH0_REDIRECT_URI):
        SOCIAL_AUTH_AUTH0_REDIRECT_URI = 'http://localhost:8000/users/complete/auth0/'

# Make sure the callback URL always has a value
if not SOCIAL_AUTH_AUTH0_REDIRECT_URI or SOCIAL_AUTH_AUTH0_REDIRECT_URI == 'https://perspectivetracker.herokuapp.com/users/complete/auth0/':
    SOCIAL_AUTH_AUTH0_REDIRECT_URI = 'https://perspectivetracker-16b3c6ba0f46.herokuapp.com/users/complete/auth0/'

# For troubleshooting - set meaningful error messages with stacktraces in debug mode
SOCIAL_AUTH_FIELDS_STORED_IN_SESSION = ['state']
SOCIAL_AUTH_SANITIZE_REDIRECTS = False
MIDDLEWARE.append('social_django.middleware.SocialAuthExceptionMiddleware')

# Auth0 Pipeline
SOCIAL_AUTH_PIPELINE = (
    'social_core.pipeline.social_auth.social_details',
    'social_core.pipeline.social_auth.social_uid',
    'social_core.pipeline.social_auth.auth_allowed',
    'social_core.pipeline.social_auth.social_user',
    'social_core.pipeline.user.get_username',
    'social_core.pipeline.social_auth.associate_by_email',  # Associate users by email
    'social_core.pipeline.user.create_user',
    'social_core.pipeline.social_auth.associate_user',
    'social_core.pipeline.social_auth.load_extra_data',
    'social_core.pipeline.user.user_details',
    'users.pipeline.get_user_role',  # Custom pipeline to assign role
)

# Ensure Auth0 users are created with proper permissions
SOCIAL_AUTH_CREATE_USERS = True
SOCIAL_AUTH_USER_MODEL = 'users.CustomUser'
SOCIAL_AUTH_STORAGE = 'social_django.models.DjangoStorage'

# Associate users by email to prevent duplicate accounts
SOCIAL_AUTH_ASSOCIATE_BY_EMAIL = True

LOGIN_URL = '/users/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

# Email settings
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'mail.techopolis.app')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 465))
EMAIL_USE_SSL = os.environ.get('EMAIL_USE_SSL', 'True') == 'True'
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'False') == 'True'
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', 'tracker@techopolis.app')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', 'Techopolis25@@')
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'Techopolis Online Solutions <tracker@techopolis.app>')
SERVER_EMAIL = os.environ.get('SERVER_EMAIL', 'tracker@techopolis.app')
EMAIL_TIMEOUT = int(os.environ.get('EMAIL_TIMEOUT', 30))

# Only override email settings if explicitly set to use console backend
if os.environ.get('USE_CONSOLE_EMAIL', 'False') == 'True':
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
    EMAIL_HOST = 'localhost'
    EMAIL_PORT = 25
    EMAIL_USE_SSL = False
    EMAIL_USE_TLS = False
    EMAIL_HOST_USER = ''
    EMAIL_HOST_PASSWORD = ''
    DEFAULT_FROM_EMAIL = 'noreply@localhost'
    SERVER_EMAIL = 'noreply@localhost'

# Security settings for production
if not DEBUG and ENV != 'development':
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
else:
    # Explicitly disable SSL settings for local development
    SECURE_SSL_REDIRECT = False
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False

# Debug settings - helpful for troubleshooting
if os.environ.get('HEROKU_DEBUG', 'False') == 'True':
    DEBUG = True
    SOCIAL_AUTH_RAISE_EXCEPTIONS = True
    RAISE_EXCEPTIONS = True
    # Only log to console if explicitly enabled
    LOGGING['loggers']['django']['level'] = 'DEBUG'
    LOGGING['loggers']['social_django']['level'] = 'DEBUG'
    LOGGING['loggers']['django.request']['level'] = 'DEBUG'
    LOGGING['root']['level'] = 'DEBUG'
