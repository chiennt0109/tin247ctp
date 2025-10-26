import os
from pathlib import Path
from urllib.parse import urlparse
import logging

BASE_DIR = Path(__file__).resolve().parent.parent

# =====================
# ⚙️ Cấu hình bảo mật
# =====================
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-secret-key-change-me")
DEBUG = os.environ.get("DEBUG", "True").lower() == "true"
ALLOWED_HOSTS = ["*"]

# =====================
# 📦 Ứng dụng
# =====================
INSTALLED_APPS = [
    # Django mặc định
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Allauth (Google login)
    "django.contrib.sites",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
    #captcha
    "captcha",
    # Ứng dụng dự án
    "accounts",
    "problems",
    "submissions",
    "contests",
]

SITE_ID = 2

# =====================
# ⚙️ Middleware
# =====================
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "allauth.account.middleware.AccountMiddleware",  # ✅ BẮT BUỘC
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "oj.urls"

# =====================
# 🧱 Template
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
# 🗄️ Database
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
            "NAME": "dmoj_db",
            "USER": "dmoj_db_user",
            "PASSWORD": "yourpassword",
            "HOST": "localhost",
            "PORT": "5432",
        }
    }

# =====================
# 🧩 Static Files
# =====================
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# =====================
# 🌍 Quốc tế hóa
# =====================
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Ho_Chi_Minh"
USE_I18N = True
USE_TZ = True

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# =====================
# 🔐 Đăng nhập / Đăng xuất
# =====================
LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/"

# =====================
# 🔑 Cấu hình Allauth
# =====================
ACCOUNT_AUTHENTICATION_METHOD = "username_email"
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_EMAIL_VERIFICATION = "none"
ACCOUNT_USERNAME_REQUIRED = True
ACCOUNT_LOGOUT_REDIRECT_URL = "/"

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",  # ✅ THIẾU DÒNG NÀY LÀ KHÔNG ĐĂNG NHẬP GOOGLE ĐƯỢC
]
#Captcha

RECAPTCHA_PUBLIC_KEY = os.environ.get("RECAPTCHA_PUBLIC_KEY", "")
RECAPTCHA_PRIVATE_KEY = os.environ.get("RECAPTCHA_PRIVATE_KEY", "")
RECAPTCHA_REQUIRED_SCORE = 0.85  # dùng cho v3, không hại nếu để đó

ACCOUNT_FORMS = {
    "signup": "accounts.forms.SecureSignupForm",
}

#------------------------
SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "APP": {
            "client_id": os.environ.get("GOOGLE_CLIENT_ID", ""),
            "secret": os.environ.get("GOOGLE_CLIENT_SECRET", ""),
            "key": "",
        },
        "SCOPE": ["profile", "email"],
        "AUTH_PARAMS": {"access_type": "online"},
    }
}

# ✅ Gỡ lỗi trang trắng / redirect sai
SOCIALACCOUNT_LOGIN_ON_GET = True
SOCIALACCOUNT_DEBUG = True

# Bật logging chi tiết (Render sẽ ghi vào log)
logging.basicConfig(level=logging.DEBUG)
