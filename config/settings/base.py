"""Shared settings. Environment-specific values live in dev.py / prod.py."""
import os
from pathlib import Path

import dj_database_url
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env")


def env(key, default=None):
    return os.environ.get(key, default)


def env_bool(key, default=False):
    return str(env(key, str(default))).lower() in ("1", "true", "yes", "on")


SECRET_KEY = env("DJANGO_SECRET_KEY", "dev-only-insecure-key-change-me")
DEBUG = False
ALLOWED_HOSTS = [h for h in env("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if h]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "apps.core",
    "apps.accounts",
    "apps.academics",
    "apps.resources",
    "apps.moderation",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.core.context_processors.branding",
            ],
        },
    },
]

# SQLite by default so local development needs nothing installed.
# Set DATABASE_URL (e.g. a Render PostgreSQL URL) to use PostgreSQL.
DATABASES = {
    "default": dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}", conn_max_age=600
    )
}

AUTH_USER_MODEL = "accounts.User"
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "core:dashboard"
LOGOUT_REDIRECT_URL = "core:home"

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Africa/Addis_Ababa"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---- Resource uploads -------------------------------------------------------
# Private folder: never served by the web server or MEDIA_URL. Files leave it
# only through Django views that check permissions. Replaced by private cloud
# storage at deployment (see apps/resources/storage.py).
PRIVATE_MEDIA_ROOT = Path(env("PRIVATE_MEDIA_ROOT", str(BASE_DIR / "private_media")))
MAX_UPLOAD_MB = int(env("MAX_UPLOAD_MB", "20"))
UPLOADS_PER_HOUR = int(env("UPLOADS_PER_HOUR", "20"))

# Malware scanning. Leave RESOURCE_SCANNER empty when no scanner is available:
# files then stay "pending" and unscanned (never marked safe).
RESOURCE_SCANNER = env("RESOURCE_SCANNER", "")  # e.g. apps.resources.scanning.ClamAVScanner
CLAMAV_HOST = env("CLAMAV_HOST", "")
CLAMAV_PORT = int(env("CLAMAV_PORT", "3310"))
CLAMAV_UNIX_SOCKET = env("CLAMAV_UNIX_SOCKET", "")
CLAMAV_TIMEOUT = int(env("CLAMAV_TIMEOUT", "20"))
# Moderators may approve a file whose scan was unavailable. Development only.
ALLOW_APPROVE_WITHOUT_SCAN = False

# Institution branding is configuration, not hardcoded identity.
PLATFORM_NAME = env("PLATFORM_NAME", "Learning Resource Hub")
INSTITUTION_NAME = env("INSTITUTION_NAME", "Infolink University College")
PRIMARY_COLOR = env("PRIMARY_COLOR", "#1f4e79")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": env("LOG_LEVEL", "INFO")},
}
