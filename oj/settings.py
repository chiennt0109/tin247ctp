import os
from pathlib import Path
from urllib.parse import urlparse
import logging
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")


# =====================
# ? Cau hinh bao mat
# =====================
load_dotenv(os.path.join(BASE_DIR, '.env'))
JUDGE_CALLBACK_URL = os.environ.get("JUDGE_CALLBACK_URL")
JUDGE_TOKEN = os.environ.get("JUDGE_TOKEN")


SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-secret-key-change-me")
#DEBUG = os.environ.get("DEBUG", "True").lower() == "true"
DEBUG = True
ALLOWED_HOSTS = ["*"]


# =====================
# Ung dung
# =====================
INSTALLED_APPS = [
    # Django default
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_rq",
    # Allauth (Google login)
    "django.contrib.sites",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
    #captcha
    "django_recaptcha",    
    "crispy_forms",
    "crispy_bootstrap5",
    # ung dung du an
    "accounts",
    "problems",
    "submissions",
    "contests",
    "arena.apps.ArenaConfig",
    "learning_analytics",
]

SITE_ID = 2

# =====================
# ?? Middleware
# =====================
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "problems.middleware.submission_throttle.SubmissionThrottleMiddleware",
]

ROOT_URLCONF = "oj.urls"

# =====================
# ?? Template
# =====================
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "oj.wsgi.application"

# =====================
# ? Database
# =====================
if "DATABASE_URL" in os.environ:
    result = urlparse(os.environ["DATABASE_URL"])
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": result.path[1:],
            "USER": result.username,
            "PASSWORD": result.password,
            "HOST": result.hostname,
            "PORT": result.port or 5432,
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": "dmoj",
            "USER": "dmojuser",
            "PASSWORD": "dmojpass",
            "HOST": "localhost",
            "PORT": "5432",
        }
    }

# =====================
#  Static Files
# =====================
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# =====================
# 
# =====================
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Ho_Chi_Minh"
USE_I18N = True
USE_TZ = True

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# =====================
# 
# =====================
LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/"

# =====================
# ??  Allauth
# =====================
ACCOUNT_AUTHENTICATION_METHOD = "username_email"
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_EMAIL_VERIFICATION = "none"
ACCOUNT_USERNAME_REQUIRED = True
ACCOUNT_LOGOUT_REDIRECT_URL = "/"

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",  
]
#Captcha

RECAPTCHA_PUBLIC_KEY = os.environ.get("RECAPTCHA_PUBLIC_KEY", "")
RECAPTCHA_PRIVATE_KEY = os.environ.get("RECAPTCHA_PRIVATE_KEY", "")
RECAPTCHA_REQUIRED_SCORE = 0.85  
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"


ACCOUNT_FORMS = {
    "signup": "accounts.forms.SecureSignupForm",
}

#------------------------
SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "APP": {
            "client_id": os.environ.get("GOOGLE_CLIENT_ID"),
            "secret": os.environ.get("GOOGLE_CLIENT_SECRET"),
            "key": "",
        },
        "SCOPE": [
            "profile",
            "email",
        ],
        "AUTH_PARAMS": {
            "access_type": "online",
        },
        "OAUTH_PKCE_ENABLED": True,
    }
}

# 
SOCIALACCOUNT_LOGIN_ON_GET = True
SOCIALACCOUNT_DEBUG = True

# 
logging.basicConfig(level=logging.DEBUG)

# =====================
# ?? Cache System (Redis + Fallback)
# =====================
try:
    import django_redis  # noqa
    _use_redis = True
except Exception:
    _use_redis = False

if _use_redis:
    CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": "redis://127.0.0.1:6379/1",
            "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"},
            "TIMEOUT": 300,
        }
    }
else:
    # fallback if Redis not available
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "throttle-fallback",
            "TIMEOUT": 300,
        }
    }

# =====================
# ?? Logging for Throttle
# =====================
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "[%(asctime)s] %(levelname)s [%(name)s] %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "handlers": {
        "file_throttle": {
            "class": "logging.FileHandler",
            "filename": "/var/www/tin247ctp/throttle.log",
            "formatter": "verbose",
        },
    },
    "loggers": {
        "submission_throttle": {
            "handlers": ["file_throttle"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

# =====================
# ?? Anti-spam settings
# =====================
SUBMISSION_THROTTLE_ENABLED = True
SUBMISSION_THROTTLE_RATE = 3          # max submissions
SUBMISSION_THROTTLE_WINDOW = 60       # seconds
SUBMISSION_THROTTLE_VIEWS = ["submissions:submission_create"]  # only judge submissions


# =====================
# ?? Redis Queue cho h? th?ng ch?m
# =====================
RQ_QUEUES = {
    'default': {
        'URL': os.environ.get('REDIS_URL', 'redis://127.0.0.1:6379/0'),
        'DEFAULT_TIMEOUT': 300,
    },
    'judge': {
        'URL': os.environ.get('REDIS_URL', 'redis://127.0.0.1:6379/0'),
        'DEFAULT_TIMEOUT': 600,
    },
}
RQ_PREFIX = ""

