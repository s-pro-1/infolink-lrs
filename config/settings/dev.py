from .base import *  # noqa

DEBUG = True
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}

# Lets you test the whole flow on a laptop without ClamAV installed.
ALLOW_APPROVE_WITHOUT_SCAN = True
