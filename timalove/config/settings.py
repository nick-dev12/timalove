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
    "core.middleware.force_update.ForceUpdateMiddleware",
    "core.middleware.auth_guards.AuthGuardsMiddleware",
    "core.middleware.admin_security.AdminSecurityMiddleware",
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
                "core.context_processors.app_features",
                "core.context_processors.admin_panel_nav",
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

# Session persistante — rester connecté entre les visites (renouvelée à chaque requête).
SESSION_COOKIE_AGE = env.int("SESSION_COOKIE_AGE", default=60 * 60 * 24 * 365)
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
SESSION_SAVE_EVERY_REQUEST = True
CSRF_COOKIE_AGE = SESSION_COOKIE_AGE

# Requis pour le popup Google / Firebase Auth (sinon la popup charge et ne revient jamais)
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin-allow-popups"
CSRF_TRUSTED_ORIGINS = env.list(
    "CSRF_TRUSTED_ORIGINS",
    default=["http://127.0.0.1:8000", "http://localhost:8000"],
)
CSRF_FAILURE_VIEW = "core.views.csrf.csrf_failure"
CSRF_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_HTTPONLY = False

# Derrière Nginx (Webuzo) : faire confiance au proto HTTPS transmis.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = env.bool("USE_X_FORWARDED_HOST", default=not DEBUG)
if DEBUG:
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False
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
    "process-scheduled-campaigns": {
        "task": "core.tasks.process_scheduled_campaigns",
        "schedule": crontab(minute="*"),
    },
}

# Intégrations
# Paiement — NabooPay (https://platform.naboopay.com) ou CinetPay (legacy)
PAYMENT_PROVIDER = env("PAYMENT_PROVIDER", default="")  # naboopay | cinetpay | auto
NABOOPAY_API_KEY = env("NABOOPAY_API_KEY", default="")
NABOOPAY_WEBHOOK_SECRET = env("NABOOPAY_WEBHOOK_SECRET", default="")
NABOOPAY_BASE_URL = env("NABOOPAY_BASE_URL", default="https://api.naboopay.com")
NABOOPAY_CURRENCY = env("NABOOPAY_CURRENCY", default="XOF")
NABOOPAY_METHODS = env("NABOOPAY_METHODS", default="wave,orange_money")
NABOOPAY_FEES_CUSTOMER_SIDE = env.bool("NABOOPAY_FEES_CUSTOMER_SIDE", default=False)
# URL publique HTTPS pour success_url / error_url NabooPay (prod ou ngrok). Vide = SITE_URL.
NABOOPAY_PUBLIC_SITE_URL = env("NABOOPAY_PUBLIC_SITE_URL", default="")
NABOOPAY_PRODUCTION_SITE_URL = env(
    "NABOOPAY_PRODUCTION_SITE_URL",
    default="https://timalove.goo-bridge.com",
)
NGROK_URL = env("NGROK_URL", default="")
# CinetPay — back-office marchand https://app.cinetpay.com (Intégrations)
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

from core.utils.public_hosts import extend_hosts  # noqa: E402
from core.utils.site_url import resolve_public_site_url  # noqa: E402

SITE_URL = resolve_public_site_url(
    env("SITE_URL", default="http://127.0.0.1:8000"),
    debug=DEBUG,
    allowed_hosts=ALLOWED_HOSTS,
)

from urllib.parse import urlparse  # noqa: E402

for _public_url in (NABOOPAY_PUBLIC_SITE_URL, NGROK_URL):
    if _public_url:
        extend_hosts(_public_url, allowed_hosts=ALLOWED_HOSTS, csrf_origins=CSRF_TRUSTED_ORIGINS)

_site_origin = urlparse(SITE_URL)
if _site_origin.scheme and _site_origin.netloc:
    _origin = f"{_site_origin.scheme}://{_site_origin.netloc}"
    if _origin not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS.append(_origin)
FREE_MESSAGES_LIMIT_DEFAULT = 5
FREE_SWIPES_PER_DAY_DEFAULT = 20
FREE_LIKES_PER_DAY_DEFAULT = 20
FREE_LIKES_VISIBLE_DEFAULT = 2
FREE_HISTORY_VISIBLE_DEFAULT = 5
# False = tests complets (messages, swipes, likes, historique, photos sans quota).
# Remettre True avant l’ouverture publique.
FREEMIUM_LIMITS_ENABLED = env.bool("FREEMIUM_LIMITS_ENABLED", default=True)

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
