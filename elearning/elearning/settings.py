"""
Django settings for the LearnHub e-learning platform.

Every environment-specific value is read from environment variables (or a
local .env file) so the same code runs locally, in docker-compose and in
production. See .env.example at the repository root.
"""
import os
import sys
from datetime import timedelta
from pathlib import Path

import dj_database_url
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = BASE_DIR.parent

# Load .env from the repo root (docker-compose injects env directly, so this
# is mostly for running `manage.py` on the host).
load_dotenv(REPO_ROOT / ".env")


def env_bool(name: str, default: bool = False) -> bool:
    return os.environ.get(name, str(int(default))).strip().lower() in {"1", "true", "yes", "on"}


def env_list(name: str, default: str = "") -> list[str]:
    return [item.strip() for item in os.environ.get(name, default).split(",") if item.strip()]


# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-only-insecure-key-change-me")
DEBUG = env_bool("DJANGO_DEBUG", default=False)
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,[::1]")
CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS", "http://localhost:8000,http://127.0.0.1:8000")

SITE_NAME = os.environ.get("SITE_NAME", "LearnHub")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "whitenoise.runserver_nostatic",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    # third party
    "rest_framework",
    "rest_framework_simplejwt",
    "django_filters",
    "corsheaders",
    "axes",
    "csp",
    # local
    "main.apps.MainConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "csp.middleware.CSPMiddleware",
    "axes.middleware.AxesMiddleware",  # must be last: renders the lockout response
]

ROOT_URLCONF = "elearning.urls"

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
                "main.context_processors.site",
            ],
        },
    },
]

WSGI_APPLICATION = "elearning.wsgi.application"

# ---------------------------------------------------------------------------
# Database: DATABASE_URL (postgres in docker) or SQLite fallback
# ---------------------------------------------------------------------------
_database_url = os.environ.get("DATABASE_URL", "").strip()
if _database_url:
    DATABASES = {"default": dj_database_url.parse(_database_url, conn_max_age=600, conn_health_checks=True)}
else:
    DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
AUTH_USER_MODEL = "main.User"
AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesStandaloneBackend",  # must be first: blocks locked-out requests
    "django.contrib.auth.backends.ModelBackend",
]
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "dashboard"
LOGOUT_REDIRECT_URL = "home"

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ---------------------------------------------------------------------------
# i18n
# ---------------------------------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = os.environ.get("TIME_ZONE", "UTC")
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Static & media
# ---------------------------------------------------------------------------
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
TESTING = "test" in sys.argv or "pytest" in sys.modules
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        # The hashed manifest needs `collectstatic`; skip it for dev server and tests.
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"
        if (DEBUG or TESTING)
        else "whitenoise.storage.CompressedManifestStaticFilesStorage"
    },
}

MEDIA_URL = "/media/"
MEDIA_ROOT = Path(os.environ.get("MEDIA_ROOT", BASE_DIR / "media"))
# Let Django serve uploads itself when no reverse proxy / object storage is in front of it.
SERVE_MEDIA = env_bool("SERVE_MEDIA", default=True)

# ---------------------------------------------------------------------------
# Messages -> Bootstrap classes
# ---------------------------------------------------------------------------
from django.contrib.messages import constants as message_constants  # noqa: E402

MESSAGE_TAGS = {
    message_constants.DEBUG: "secondary",
    message_constants.INFO: "info",
    message_constants.SUCCESS: "success",
    message_constants.WARNING: "warning",
    message_constants.ERROR: "danger",
}

# ---------------------------------------------------------------------------
# REST framework / JWT / CORS
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticatedOrReadOnly"],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 12,
}

CORS_ALLOWED_ORIGINS = env_list("CORS_ALLOWED_ORIGINS")
CORS_ALLOW_ALL_ORIGINS = env_bool("CORS_ALLOW_ALL_ORIGINS", default=DEBUG)

# ---------------------------------------------------------------------------
# Security hardening when DEBUG is off
# ---------------------------------------------------------------------------
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SESSION_COOKIE_SECURE = env_bool("SESSION_COOKIE_SECURE", default=False)
    CSRF_COOKIE_SECURE = env_bool("CSRF_COOKIE_SECURE", default=False)
    SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", default=False)
    SECURE_HSTS_SECONDS = int(os.environ.get("SECURE_HSTS_SECONDS", "0"))
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = "DENY"

# ---------------------------------------------------------------------------
# Brute-force protection (django-axes)
# ---------------------------------------------------------------------------
AXES_ENABLED = env_bool("AXES_ENABLED", default=not TESTING)
AXES_FAILURE_LIMIT = int(os.environ.get("AXES_FAILURE_LIMIT", "5"))
AXES_COOLOFF_TIME = timedelta(minutes=int(os.environ.get("AXES_COOLOFF_MINUTES", "15")))
AXES_LOCKOUT_PARAMETERS = [["username", "ip_address"]]  # lock this username from this IP only
AXES_RESET_ON_SUCCESS = True
AXES_LOCKOUT_TEMPLATE = "auth/locked_out.html"
AXES_IPWARE_PROXY_COUNT = int(os.environ.get("AXES_PROXY_COUNT", "0"))  # set 1 behind nginx / a load balancer
AXES_IPWARE_META_PRECEDENCE_ORDER = ["HTTP_X_FORWARDED_FOR", "REMOTE_ADDR"]

# ---------------------------------------------------------------------------
# Content Security Policy (django-csp 4.x)
# ---------------------------------------------------------------------------
from csp.constants import NONCE, NONE, SELF  # noqa: E402

_CSP_DIRECTIVES = {
    "default-src": [SELF],
    "script-src": [SELF, NONCE, "https://cdn.jsdelivr.net"],
    "style-src": [SELF, "'unsafe-inline'", "https://cdn.jsdelivr.net", "https://fonts.googleapis.com"],
    "font-src": [SELF, "https://fonts.gstatic.com", "https://cdn.jsdelivr.net"],
    "img-src": [SELF, "data:", "https:"],
    "media-src": [SELF, "https:"],
    "frame-src": ["https://www.youtube-nocookie.com", "https://www.youtube.com", "https://player.vimeo.com"],
    "connect-src": [SELF],
    "object-src": [NONE],
    "base-uri": [SELF],
    "form-action": [SELF],
    "frame-ancestors": [NONE],
}
_CSP_CONFIG = {
    "DIRECTIVES": _CSP_DIRECTIVES,
    # DRF's browsable API ships its own inline scripts; the JSON API itself needs no CSP.
    "EXCLUDE_URL_PREFIXES": ["/api/"],
}
if env_bool("CSP_REPORT_ONLY", default=False):
    CONTENT_SECURITY_POLICY_REPORT_ONLY = _CSP_CONFIG
else:
    CONTENT_SECURITY_POLICY = _CSP_CONFIG

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": os.environ.get("DJANGO_LOG_LEVEL", "INFO")},
}
