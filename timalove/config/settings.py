"""
Django settings — TimaLove (Django + PostgreSQL).
Architecture MVC : models / controllers / views / middleware dans l'app `core`.
"""

from pathlib import Path

import environ
from celery.schedules import crontab

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, ["localhost", "127.0.0.1"]),
)

environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("SECRET_KEY")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])
if DEBUG:
    ALLOWED_HOSTS = list(dict.fromkeys([*ALLOWED_HOSTS, "testserver"]))

INSTALLED_APPS = [
    "daphne",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_htmx",
    "channels",
    "core",
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
    "django_htmx.middleware.HtmxMiddleware",
    "core.middleware.request_timing.RequestTimingMiddleware",
    "core.middleware.maintenance.MaintenanceMiddleware",
    "core.middleware.auth_guards.AuthGuardsMiddleware",
]

ROOT_URLCONF = "config.urls"

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
                "core.context_processors.site_branding",
                "core.context_processors.app_nav_badges",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("DB_NAME"),
        "USER": env("DB_USER"),
        "PASSWORD": env("DB_PASSWORD"),
        "HOST": env("DB_HOST"),
        "PORT": env("DB_PORT"),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "fr-fr"
TIME_ZONE = "America/Port-au-Prince"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"] if (BASE_DIR / "static").exists() else []
_static_backend = (
    "django.contrib.staticfiles.storage.StaticFilesStorage"
    if DEBUG
    else "whitenoise.storage.CompressedManifestStaticFilesStorage"
)
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": _static_backend},
}

# Médias : dossier local du projet (VPS). Pas de S3 / R2 pour l’instant.
_media_root = (env("MEDIA_ROOT", default="") or "").strip()
MEDIA_ROOT = Path(_media_root) if _media_root else BASE_DIR / "media"
_media_url = env("MEDIA_URL", default="/media/")
if not _media_url.startswith("/"):
    _media_url = "/" + _media_url
if not _media_url.endswith("/"):
    _media_url += "/"
MEDIA_URL = _media_url

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "auth:connexion"
LOGIN_REDIRECT_URL = "public:explorer"
LOGOUT_REDIRECT_URL = "public:home"

# Requis pour le popup Google / Firebase Auth (sinon la popup charge et ne revient jamais)
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin-allow-popups"
CSRF_TRUSTED_ORIGINS = env.list(
    "CSRF_TRUSTED_ORIGINS",
    default=["http://127.0.0.1:8000", "http://localhost:8000"],
)

# Derrière Nginx (Webuzo) : faire confiance au proto HTTPS transmis.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = env.bool("USE_X_FORWARDED_HOST", default=not DEBUG)
if not DEBUG:
    SESSION_COOKIE_SECURE = env.bool("SESSION_COOKIE_SECURE", default=True)
    CSRF_COOKIE_SECURE = env.bool("CSRF_COOKIE_SECURE", default=True)
    SESSION_COOKIE_HTTPONLY = True
    SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=False)
    SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=0)
    SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool("SECURE_HSTS_INCLUDE_SUBDOMAINS", default=False)
    SECURE_HSTS_PRELOAD = env.bool("SECURE_HSTS_PRELOAD", default=False)
    SECURE_REFERRER_POLICY = "same-origin"

REDIS_URL = env("REDIS_URL", default="redis://127.0.0.1:6379/0")
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    }
}
if env.bool("USE_REDIS_CHANNELS", default=False):
    # socket_timeout doit dépasser brpop_timeout (5 s) de channels_redis,
    # sinon Memurai/Redis lève TimeoutError et le WS chat se ferme en 1011.
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            "CONFIG": {
                "hosts": [
                    {
                        "address": REDIS_URL,
                        "socket_timeout": 20,
                        "socket_connect_timeout": 5,
                        "retry_on_timeout": True,
                        "health_check_interval": 30,
                    }
                ],
            },
        }
    }

CELERY_BROKER_URL = env("CELERY_BROKER_URL", default=REDIS_URL)
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", default="redis://127.0.0.1:6379/1")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
CELERY_BEAT_SCHEDULE = {
    "expire-subscriptions-and-boosts": {
        "task": "core.tasks.expire_subscriptions_and_boosts",
        "schedule": crontab(minute="*/15"),
    },
}

# Intégrations
# Paiement CinetPay (https://app.cinetpay.com)
CINETPAY_APIKEY = env("CINETPAY_APIKEY", default="")
CINETPAY_SITE_ID = env("CINETPAY_SITE_ID", default="")
CINETPAY_SECRET_KEY = env("CINETPAY_SECRET_KEY", default="")
CINETPAY_CURRENCY = env("CINETPAY_CURRENCY", default="XOF")
CINETPAY_CHANNELS = env("CINETPAY_CHANNELS", default="ALL")
CINETPAY_BASE_URL = env("CINETPAY_BASE_URL", default="https://api-checkout.cinetpay.com/v2")
# Checkout factice uniquement en local si CinetPay est injoignable
PAYMENT_SIMULATION = env.bool("PAYMENT_SIMULATION", default=DEBUG)
RESEND_API_KEY = env("RESEND_API_KEY", default="")
RESEND_FROM_EMAIL = env("RESEND_FROM_EMAIL", default="TimaLove <onboarding@resend.dev>")
RECAPTCHA_SITE_KEY = env("RECAPTCHA_SITE_KEY", default="")
RECAPTCHA_SECRET_KEY = env("RECAPTCHA_SECRET_KEY", default="")
MEDIA_CDN_URL = env("MEDIA_CDN_URL", default="")
SITE_URL = env("SITE_URL", default="http://127.0.0.1:8000")
FREE_MESSAGES_LIMIT_DEFAULT = 3
FREE_SWIPES_PER_DAY_DEFAULT = 20
FREE_LIKES_PER_DAY_DEFAULT = 10
FREE_LIKES_VISIBLE_DEFAULT = 1

EMAIL_BACKEND = env(
    "EMAIL_BACKEND",
    default="django.core.mail.backends.console.EmailBackend",
)

# Firebase Cloud Messaging (push web / mobile)
FCM_ENABLED = env.bool("FCM_ENABLED", default=True)
FIREBASE_CREDENTIALS_PATH = BASE_DIR / env(
    "FIREBASE_CREDENTIALS_FILE",
    default="timalove-ddaa5-1ee274740c65.json",
)
FIREBASE_WEB_API_KEY = env("FIREBASE_WEB_API_KEY", default="AIzaSyAekAUds26lHAT_ZnNNG4BsGVpmno_VoJs")
FIREBASE_AUTH_DOMAIN = env("FIREBASE_AUTH_DOMAIN", default="timalove-ddaa5.firebaseapp.com")
FIREBASE_PROJECT_ID = env("FIREBASE_PROJECT_ID", default="timalove-ddaa5")
FIREBASE_STORAGE_BUCKET = env("FIREBASE_STORAGE_BUCKET", default="timalove-ddaa5.firebasestorage.app")
FIREBASE_MESSAGING_SENDER_ID = env("FIREBASE_MESSAGING_SENDER_ID", default="251608525332")
FIREBASE_APP_ID = env("FIREBASE_APP_ID", default="1:251608525332:web:b390af68f9bbd131049501")
FIREBASE_MEASUREMENT_ID = env("FIREBASE_MEASUREMENT_ID", default="G-F134QKNJR6")
FIREBASE_VAPID_KEY = env(
    "FIREBASE_VAPID_KEY",
    default="BLtkWUCw0gz8tibsGYVk7TB10-B6ei4xCHQ0H1gW9Y-87nOZvH8oJKhz_jz_Xf7Ah1GWt4CubUmyn1trprNBDDo",
)
GOOGLE_WEB_CLIENT_ID = env(
    "GOOGLE_WEB_CLIENT_ID",
    default="251608525332-6mc6oqgnh76gi7ivhg1cojpp95ln2ho8.apps.googleusercontent.com",
)

if DEBUG:
    CELERY_TASK_ALWAYS_EAGER = env.bool("CELERY_TASK_ALWAYS_EAGER", default=True)

FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = 12 * 1024 * 1024
