"""
Django development settings for app project.
"""

from .base import *

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "django-insecure-huvkbm&^u+xwh3_!rf=@*=_6ukx4jeta5q99+ei+mh)n8pzs$f"

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "*"]

# Database - SQLite for development
# https://docs.djangoproject.com/en/6.0/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# CORS settings for development
CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
CORS_ALLOW_CREDENTIALS = True  # Required for HttpOnly cookie auth across dev ports

# Update JWT signing key with SECRET_KEY
SIMPLE_JWT["SIGNING_KEY"] = SECRET_KEY