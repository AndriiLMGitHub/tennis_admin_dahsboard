from pathlib import Path
import dj_database_url
import os

from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from dotenv import load_dotenv

load_dotenv()


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_list(name: str, default: list[str]) -> list[str]:
    value = os.getenv(name)
    if not value:
        return default
    return [item.strip() for item in value.split(",") if item.strip()]

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/6.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv("SECRET_KEY", "unsafe-dev-secret-key-change-me")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env_bool("DEBUG", True)

MESSAGE_TAGS = {
    messages.ERROR: 'danger',
    messages.SUCCESS: 'success',
    messages.WARNING: 'warning',
    messages.INFO: 'info',
}

ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", ["*"])
CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS", [])

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'adminsortable2',
    'storages',
    'config',

    'allauth',
    'allauth.account',

    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',

    'apps.accounts_core',
    'apps.consulting.apps.ConsultingConfig',
    'apps.feedback.apps.FeedbackConfig',
    "django_extensions",

    'django_cleanup.apps.CleanupConfig',
]

AUTH_USER_MODEL = "accounts_core.User"
SITE_ID = 1

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",

    "django.contrib.auth.middleware.AuthenticationMiddleware",

    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",

    # Add the account middleware:
    "allauth.account.middleware.AccountMiddleware",
    "apps.accounts_core.middleware.CheckRoleMiddleware",
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            BASE_DIR / 'templates',
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",

                # `allauth` needs this from django
                'django.template.context_processors.request',
            ],
        },
    },
]

AUTHENTICATION_BACKENDS = [
    # Needed to log in by username in Django admin, regardless of `allauth`
    'django.contrib.auth.backends.ModelBackend',

    # `allauth` specific authentication methods, such as login by email
    'allauth.account.auth_backends.AuthenticationBackend',
]

WSGI_APPLICATION = 'config.wsgi.application'

# Database
# https://docs.djangoproject.com/en/6.0/ref/settings/#databases
DATABASES = {
    "default": dj_database_url.parse(
        os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'db.sqlite3'}"),
        conn_max_age=600,
        ssl_require=False,  # True for production
    )
}

# Password validation
# https://docs.djangoproject.com/en/6.0/ref/settings/#auth-password-validators
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Internationalization
# https://docs.djangoproject.com/en/6.0/topics/i18n/
LANGUAGE_CODE = 'en'


LANGUAGES = [
    ('en', _('English')),
    ('ru', _('Russian')),
]

# The path where Django will look for your .po files
LOCALE_PATHS = [
    BASE_DIR / 'locale',
]

TIME_ZONE = "Europe/Kyiv"

USE_I18N = True

USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/6.0/howto/static-files/
STATIC_URL = 'static/'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]
STATIC_ROOT = BASE_DIR / 'staticfiles'

CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://127.0.0.1:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", CELERY_BROKER_URL)

CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"

CELERY_TASK_ACKS_LATE = True
CELERY_TASK_REJECT_ON_WORKER_LOST = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1

CELERY_TIMEZONE = TIME_ZONE
CELERY_ENABLE_UTC = False

# Email host configurations
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD")
SUPPORT_EMAIL = EMAIL_HOST_USER
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER
EMAIL_TIMEOUT = 20

# Accounts settings
ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_SIGNUP_FIELDS = ["email*", "password1*", "password2*"]

# Custom user model has no username field
ACCOUNT_USER_MODEL_USERNAME_FIELD = None
ACCOUNT_USER_MODEL_EMAIL_FIELD = "email"

# Email verification behavior
ACCOUNT_EMAIL_VERIFICATION = "mandatory"

ACCOUNT_EMAIL_MODEL_REQUIRED = True
ACCOUNT_UNIQUE_EMAIL = True

# Automatic login ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION = True
ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION = False
ACCOUNT_CONFIRM_EMAIL_ON_GET = False

SOCIALACCOUNT_QUERY_MODEL_EMAIL = True
# Disables redirect to intermediate page - SOCIALACCOUNT_LOGIN_ON_GET = True
SOCIALACCOUNT_LOGIN_ON_GET = True

LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = "account_login"

ACCOUNT_ADAPTER = "infrastructure.email.auth_adapter.CustomAccountAdapter"
SOCIALACCOUNT_ADAPTER = "apps.accounts_core.adapters.MySocialAccountAdapter"

ACCOUNT_FORMS = {
    "signup": "apps.accounts_core.forms.CustomSignupForm",
    "login": "apps.accounts_core.forms.CustomLoginForm",
    "reset_password": "apps.accounts_core.forms.CustomResetPasswordForm",
    "reset_password_from_key": "apps.accounts_core.forms.CustomResetPasswordFromKeyForm",
}

SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "SCOPE": ["email", "profile", ],
        "AUTH_PARAMS": {"access_type": "online"},
        "OAUTH_PKCE_ENABLED": True,
    }
}

# --- Settings Cloudflare R2 (Production for Django 6.0) ---
R2_ACCESS_KEY_ID = os.getenv('R2_ACCESS_KEY_ID')
R2_SECRET_ACCESS_KEY = os.getenv('R2_SECRET_ACCESS_KEY')
R2_BUCKET_NAME = os.getenv('R2_BUCKET_NAME')
R2_ACCOUNT_ID = os.getenv('R2_ACCOUNT_ID')
R2_CUSTOM_DOMAIN = os.getenv('R2_CUSTOM_DOMAIN')

# Storage for Django 6.0
STORAGES = {
    # Media files (avatars, user uploads) go to Cloudflare R2
    "default": {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": {
            "access_key": R2_ACCESS_KEY_ID,
            "secret_key": R2_SECRET_ACCESS_KEY,
            "bucket_name": R2_BUCKET_NAME,
            "endpoint_url": f'https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com',
            "region_name": "auto",
            "signature_version": "s3v4",
            "custom_domain": R2_CUSTOM_DOMAIN,
            "file_overwrite": True,

            # Internal compatibility options (moved inside OPTIONS)
            "default_acl": None,
            "querystring_auth": False,

            "object_parameters": {
                'CacheControl': 'max-age=86400',
            },
        },
    },
    # Static files (CSS/JS from Metronic) are collected locally via `collect static`
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# Public URL for displaying media in templates
MEDIA_URL = f'https://{R2_CUSTOM_DOMAIN}/'

### ===== Others settings ===== ####
# Pagination
ITEMS_PER_PAGE = 6

# Max avatar size in MB
MAX_UPLOAD_SIZE_AVATAR = 2

ALLOWED_EXTENSIONS = {
    'video': ['.mp4', '.mov', '.avi', '.mkv', '.webm'],
    'file': ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.txt', '.jpg', '.jpeg', '.png'],
    'image': ['.jpg', '.jpeg', '.png'],
}

# Реальні ліміти для категорій файлів та специфічних форм
SIZE_LIMITS = {
    'video': 100 * 1024 * 1024,  # 100MB
    'file': 10 * 1024 * 1024,  # 10MB
    'image': 10 * 1024 * 1024,  # 10MB
    'nutrition_intake': 10 * 1024 * 1024,  # 10MB
}

UPLOAD_DIRECTORIES = {
    'general': 'requests/general',
    'nutrition_intake': 'requests/nutrition',
    'coach_request': 'requests/tennis',
    'psychology_request': 'requests/psychology',
    'avatars': 'avatars',
}

# For production
# CSRF_COOKIE_SECURE=True
