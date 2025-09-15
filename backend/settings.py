from pathlib import Path

from environ import Env

BASE_DIR = Path(__file__).resolve().parent.parent


ENV = Env()

ENV.read_env(Path(BASE_DIR, '.env'))
SECRET_KEY = ENV.str("SECRET_KEY")
DEBUG = ENV.bool("DEBUG", default=False)

ALLOWED_HOSTS = ENV.list("ALLOWED_HOSTS", default=["127.0.0.1", "localhost"])

CSRF_TRUSTED_ORIGINS = ENV.list(
    "CSRF_TRUSTED_ORIGINS", default=["http://127.0.0.1:8000"]
)

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "drf_spectacular",
    "import_export",
    "backend.apps.BackendConfig",
    "users.apps.UsersConfig",
    "admin_panel.apps.AdminPanelConfig",
    "liveconfigs",
    "items",
    "orders",
    "codes",
    "api",
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

ROOT_URLCONF = "backend.urls"

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

WSGI_APPLICATION = "backend.wsgi.application"


DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": ENV.str("POSTGRES_DB"),
        "USER": ENV.str("POSTGRES_USER"),
        "PASSWORD": ENV.str("POSTGRES_PASSWORD"),
        "HOST": ENV.str("POSTGRES_HOST"),
        "PORT": ENV.str("POSTGRES_PORT"),
    }
}


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

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "api.authentication.APIKeyAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Ragner Shop Public API",
    "DESCRIPTION": "Welcome to the Ragner Shop Public API documentation. This guide provides details about the API, authentication methods, request/response formats, and error handling.",  # NOQA
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "AUTHENTICATION_EXTENSIONS": {
        "api.schema.APIKeyAuthenticationScheme": None,
    },
}

LANGUAGE_CODE = "en-us"

TIME_ZONE = "Asia/Omsk"

USE_I18N = True

USE_TZ = True


STATIC_URL = "/static/"
MEDIA_URL = "/media/"


STATIC_ROOT = BASE_DIR / "static"
MEDIA_ROOT = BASE_DIR / "media/"
LOGS_PATH = BASE_DIR / "logs"


DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

DEFAULT_PAGINATION = 5

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": f"redis://{ENV.str('REDIS_HOST')}:6379",
    }
}

LC_MAX_STR_LENGTH_DISPLAYED_AS_TEXTINPUT = 50
LC_ENABLE_PRETTY_INPUT = True
LIVECONFIGS_SYNCWRITE = True
LC_CACHE_TTL = 10

CELERY_BROKER_URL = f"redis://{ENV.str('REDIS_HOST')}:6379/10"
CELERY_RESULT_BACKEND = f"redis://{ENV.str('REDIS_HOST')}:6379/11"
CELERY_TASK_TRACK_STARTED = True
