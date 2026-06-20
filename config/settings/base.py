from pathlib import Path

from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = config("SECRET_KEY", default="unsafe-dev-secret-key")
DEBUG = config("DEBUG", default=False, cast=bool)
ANTHROPIC_API_KEY = config("ANTHROPIC_API_KEY", default="")
ALLOWED_HOSTS = config(
    "ALLOWED_HOSTS",
    default="127.0.0.1,localhost",
    cast=lambda value: [host.strip() for host in value.split(",")],
)

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "widget_tweaks",
    "apps.accounts",
    "apps.dashboard",
    "apps.applications",
    "apps.daily_log",
    "apps.weekly_review",
    "apps.metrics",
    "apps.notes",
    "apps.exports",
    "apps.interviews",
    "apps.followups",
    "apps.recruiter_emails",
    "apps.job_intelligence",
    "apps.ai_agents",
    "apps.skill_gaps",
    "apps.skill_ledger",
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
                "apps.accounts.context_processors.account_menu",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-gb"
TIME_ZONE = "Europe/London"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

# Runtime generated files live outside tracked source folders.
STORAGE_ROOT = BASE_DIR / "storage"
GENERATED_DOCUMENTS_ROOT = STORAGE_ROOT / "generated_documents"
UPLOADED_DOCUMENTS_ROOT = STORAGE_ROOT / "application_documents"
GENERATED_EXPORTS_ROOT = STORAGE_ROOT / "exports"
GENERATED_SCREENSHOTS_ROOT = STORAGE_ROOT / "screenshots"
MEDIA_GENERATED_DOCUMENTS_ROOT = MEDIA_ROOT / "generated_documents"
MEDIA_APPLICATION_DOCUMENTS_ROOT = MEDIA_ROOT / "application_documents"
FORBIDDEN_GENERATED_FILE_PREFIXES = (
    "apps",
    "templates",
    "static",
    "docs",
    "data/master_cv",
)

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Optional local master CV template paths. Keep personal CV files outside the repo.
MASTER_CV_TEMPLATE_DOCX_PATH = config("MASTER_CV_TEMPLATE_DOCX_PATH", default="")
MASTER_CV_TEMPLATE_PDF_PATH = config("MASTER_CV_TEMPLATE_PDF_PATH", default="")
MASTER_CV_FILE_PATH = config("MASTER_CV_FILE_PATH", default="")

LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "dashboard:overview"
LOGOUT_REDIRECT_URL = "accounts:login"
