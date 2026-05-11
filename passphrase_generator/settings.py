import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get("DJANGO_SECRET", "change-me-for-local-dev-only")
DEBUG      = os.environ.get("DEBUG", "false").lower() == "true"
ADULT_WORD_UNLOCK_PASSWORD = os.environ.get("ADULT_WORD_UNLOCK_PASSWORD", "fluchmodus")

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0"]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "generator.apps.GeneratorConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "passphrase_generator.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
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

def _parse_db_url(url: str) -> dict:
    from urllib.parse import urlparse
    p = urlparse(url)
    return {
        "ENGINE":   "django.db.backends.postgresql",
        "NAME":     p.path.lstrip("/"),
        "USER":     p.username,
        "PASSWORD": p.password,
        "HOST":     p.hostname,
        "PORT":     str(p.port or 5432),
    }

_db_url = os.environ.get(
    "DATABASE_URL",
    "postgres://passphrase:passphrase@localhost:5432/passphrase_generator",
)
DATABASES = {"default": _parse_db_url(_db_url)}

LANGUAGE_CODE = "de-de"
TIME_ZONE     = "Europe/Berlin"
USE_I18N      = True
USE_TZ        = True
STATIC_URL   = "/static/"
STATIC_ROOT  = BASE_DIR / "staticfiles"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
