"""
Django settings for draw_client project.

Generated by 'django-admin startproject' using Django 5.1.4.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.1/ref/settings/
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from celery.schedules import crontab


# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(
    os.path.join(
        BASE_DIR, ".env"
    )
) 

# load_dote/nv("/home/sougata/Documents/draw-client/.env")

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv("SECRET_KEY", "django-insecure-u69m@5_kjct)7fr9n@w%5wpby_)")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DJANGO_DEBUG', '') != 'False'
ALLOWED_HOSTS = os.environ.get('DJANGO_ALLOWED_HOSTS', '').split(',')
CSRF_TRUSTED_ORIGINS = os.environ.get('DJANGO_CSRF_TRUSTED_ORIGINS', '').split(',')
APSCHEDULER_DATETIME_FORMAT = "N j, Y, f:s a"
DOCS_ROOT = os.path.join(BASE_DIR, 'docs/build/html')
DOCS_ACCESS = 'public'

# Application definition

INSTALLED_APPS = [
    # Remove all other admin themes and make sure unfold is first
    'unfold',  # Must be before admin
    'unfold.contrib.filters',
    "unfold.contrib.forms",  # optional, if special form elements are needed
    "unfold.contrib.inlines",  # optional, if special inlines are needed
    "unfold.contrib.import_export",
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    "whitenoise.runserver_nostatic",
    'celery',       
    'django_celery_results',
    'django_celery_beat',
    # Your apps
    'django_apscheduler',
    'solo',
    'allauth_ui',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'widget_tweaks',
    'slippers',
    'dicom_handler',
    'docs',
    # 'log_viewer',
    'django_log_lens',
    'api_client',
    'deidapp',
]



SITE_ID = 1

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    "allauth.account.middleware.AccountMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",

]

ROOT_URLCONF = 'draw_client.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                #'unfold.context_processors.unfold',  # Add this line

            ],
            'builtins': ['slippers.templatetags.slippers',],
        },
    },
]

WSGI_APPLICATION = 'draw_client.wsgi.application'


AUTHENTICATION_BACKENDS = [
   
    # Needed to login by username in Django admin, regardless of `allauth`
    'django.contrib.auth.backends.ModelBackend',

    # `allauth` specific authentication methods, such as login by email
    'allauth.account.auth_backends.AuthenticationBackend',
]


# Database
# https://docs.djangoproject.com/en/5.1/ref/settings/#databases

# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.sqlite3',
#         'NAME': BASE_DIR / 'db.sqlite3',
#     }
# }

DATABASES = {
    'default': {
        'ENGINE': os.getenv('DJANGO_DB_ENGINE', 'django.db.backends.sqlite3'),
        'NAME': os.getenv('DJANGO_DB_NAME', BASE_DIR / 'db.sqlite3'),
        'USER': os.getenv('DJANGO_DB_USER', ''),
        'PASSWORD': os.getenv('DJANGO_DB_PASSWORD', ''),
        'HOST': os.getenv('DJANGO_DB_HOST', ''),
        'PORT': os.getenv('DJANGO_DB_PORT', ''),
    }
}


# Password validation
# https://docs.djangoproject.com/en/5.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.1/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'Asia/Kolkata'


USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.1/howto/static-files/

# Static
# Static files configuration
STATIC_URL = 'static/'
STATIC_ROOT = os.path.join(BASE_DIR, STATIC_URL)  # Changed to a directory within project
STATICFILES_STORAGE = "django.contrib.staticfiles.storage.ManifestStaticFilesStorage"


# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
# API Settings
API_URL = os.getenv('API_URL')
# API_USERNAME = os.getenv('API_USERNAME')
# API_PASSWORD = os.getenv('API_PASSWORD')


# redirect urls
LOGIN_REDIRECT_URL = '/'
LOGIN_URL = '/accounts/login/'
LOGOUT_REDIRECT_URL = '/'



# ACCOUNT_EMAIL_VERIFICATION = 'mandatory'
# ACCOUNT_EMAIL_CONFIRMATION_AUTHENTICATED_REDIRECT_URL = None


#Grappelli Dashboard

# GRAPPELLI_INDEX_DASHBOARD = 'draw_client.dashboard.CustomIndexDashboard'
# GRAPPELLI_ADMIN_TITLE = "DRAW-CLIENT"
# Unfold Settings
UNFOLD = {
    "SITE_HEADER": "DRAW CLIENT",
    "SITE_TITLE": "DRAW CLIENT",
    "SITE_BRAND": "DRAW CLIENT",

    "SITE_DROPDOWN": [
        {
            "icon": "book",
            "title": _("Documentation"),
            "link": "/docs",
            'target': '_blank',
        },
        {
            'icon': 'public',
            'title': _("DRAW Website"),
            'link': "http://144.126.254.23/",
            'target': '_blank',
        },
        {
            'icon': 'public',
            'title': _("CHAVI Website"),
            'link': "https://chavi.ai",
            'target': '_blank',
        },
        {
            'icon': 'groups',
            'title': _("Users"),
            'link': reverse_lazy("admin:auth_user_changelist"),
        },
        {
            'icon': 'diversity_4',
            'title': _("Groups"),
            'link': reverse_lazy("admin:auth_group_changelist"),
        },
             


    ],

    "SIDEBAR": {
        "show_search": False,  # Search in applications and models names
        "show_all_applications": False,  # Dropdown with all applications and models
        "navigation": [
            {
                "title": _("DICOMPath Configuration"),
                "separator": False,  # Top border
                "collapsible": True,  # Collapsible group of links
                "items": [
                    {
                        "title": _("DICOM Path"),
                        "icon": "folder_special",
                        "link": reverse_lazy("admin:dicom_handler_dicompathconfig_changelist"),
                    },                               
                ],
            },

            {
                "title": _("Autsegmentation Templates"),
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": _("Autosegmentation Templates"),
                        "icon": "draw",
                        "link": reverse_lazy("admin:dicom_handler_modelyamlinfo_changelist"),
                    },
                ],
            },
            {
                "title": _("Template Rulesets"),
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": _("DICOM Tags"),
                        "icon": "tag",
                        "link": reverse_lazy("admin:dicom_handler_tagname_changelist"),
                    },
                     {
                        "title": _("Rule Sets"),
                        "icon": "rule",
                        "link": reverse_lazy("admin:dicom_handler_ruleset_changelist"),
                    },
                    #  {
                    #     "title": _("Rules"),
                    #     "icon": "rule_folder",
                    #     "link": reverse_lazy("admin:dicom_handler_rule_changelist"),
                    # },
                ],
            },

            {
                "title": _("Task Scheduling"),
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": _("Celery Tasks Status"),
                        "icon": "schedule",
                        "link": reverse_lazy("admin:django_celery_results_taskresult_changelist"),
                    },
                    {
                        "title": _("Scheduled Tasks"),
                        "icon": "calendar_today",
                        "link": reverse_lazy("admin:django_celery_beat_periodictask_changelist"),
                    },
                ],
            },

            {
                "title": _("DICOM Processing"),
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": _("Copied DICOM Data"),
                        "icon": "folder",
                        "link": reverse_lazy("admin:dicom_handler_copydicom_changelist"),
                    },
                    {
                        "title": _("Dicom Series for Processing"),
                        "icon": "folder",
                        "link": reverse_lazy("admin:dicom_handler_dicomseriesprocessing_changelist"),
                    },
                    {
                        "title": _("Processing Status"),
                        "icon": "task_alt",
                        "link": reverse_lazy("admin:dicom_handler_processingstatus_changelist"),
                    },
                    {
                        "title": _("Send to Processing"),
                        "icon": "pending",
                        "link": reverse_lazy("admin:dicom_handler_dicomunprocessed_changelist"),
                    }                    
                ],
            },

            {
                "title": _("Upload DICOM File Manually"),
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": _("Upload zip"),
                        "icon": "upload",
                        "link": reverse_lazy("admin:dicom_handler_uploaddicom_changelist"),
                    }
                    
                ],
            },

            {
                "title": _("API Settings and Transfers"),
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": _("Client Settings"),
                        "icon": "settings",
                        "link": reverse_lazy("admin:api_client_systemsettings_changelist"),
                    },
                    # {
                    #     "title": _("Processing Folder Paths"),
                    #     "icon": "folder",
                    #     "link": reverse_lazy("admin:api_client_folderpaths_changelist"),
                    # },
                    {
                        "title": _("DICOM Processing Status"),
                        "icon": "cycle",
                        "link": reverse_lazy("admin:api_client_dicomtransfer_changelist"),
                    },                    
                    
                ],
            },

            {
                'title': 'Deidentification Application',
                'separator': True,
                'collapsible': True,
                'items': [
                    {
                        'title': 'Patient',
                        'icon': 'person',
                        'link': reverse_lazy("admin:deidapp_patient_changelist"),
                    },
                    {
                        'title': 'Dicom Study',
                        'icon': 'folder',
                        'link': reverse_lazy("admin:deidapp_dicomstudy_changelist"),
                    },
                    {
                        'title': 'Dicom Series',
                        'icon': 'folder',
                        'link': reverse_lazy("admin:deidapp_dicomseries_changelist"),
                    },
                    {
                        'title': 'Dicom Instance',
                        'icon': 'folder',
                        'link': reverse_lazy("admin:deidapp_dicominstance_changelist"),
                    },
                    {
                        'title': 'RT Structure File',
                        'icon': 'draft',
                        'link': reverse_lazy("admin:deidapp_rtstructfile_changelist"),
                    },
                    
                ],    
                               
            },

        ],
    },    

}


# file: settings.py
from django_log_lens import LOG_FORMAT

LOG_FOLDER = BASE_DIR / "logs"

if not os.path.exists(LOG_FOLDER):
    os.makedirs(LOG_FOLDER)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": LOG_FORMAT
        }
    },
    "handlers": {
        # Debug level handler
        "debug_file": {
            "level": "DEBUG",
            "class": "logging.FileHandler",
            "filename": str(LOG_FOLDER / "debug.log"),
            "formatter": "default",
        },
        # Info level handler
        "info_file": {
            "level": "INFO",
            "class": "logging.FileHandler", 
            "filename": str(LOG_FOLDER / "info.log"),
            "formatter": "default",
        },
        # Warning level handler
        "warning_file": {
            "level": "WARNING",
            "class": "logging.FileHandler",
            "filename": str(LOG_FOLDER / "warning.log"),
            "formatter": "default",
        },
        # Error level handler
        "error_file": {
            "level": "ERROR",
            "class": "logging.FileHandler",
            "filename": str(LOG_FOLDER / "error.log"),
            "formatter": "default",
        },
        # Critical level handler
        "critical_file": {
            "level": "CRITICAL",
            "class": "logging.FileHandler",
            "filename": str(LOG_FOLDER / "critical.log"),
            "formatter": "default",
        },
        # Dedicated handlers for specific apps
        "django_file": {
            "level": "DEBUG",
            "class": "logging.FileHandler",
            "filename": str(LOG_FOLDER / "django.log"),
            "formatter": "default",
        },
        "dicom_handler_file": {
            "level": "DEBUG",
            "class": "logging.FileHandler",
            "filename": str(LOG_FOLDER / "dicom_handler.log"),
            "formatter": "default",
        },
        "deidapp_file": {
            "level": "DEBUG",
            "class": "logging.FileHandler",
            "filename": str(LOG_FOLDER / "deidapp.log"),
            "formatter": "default",
        },
        "celery_file": {
            "level": "DEBUG",
            "class": "logging.FileHandler", 
            "filename": str(LOG_FOLDER / "celery.log"),
            "formatter": "default",
        },
        "celery_beat_file": {
            "level": "DEBUG",
            "class": "logging.FileHandler", 
            "filename": str(LOG_FOLDER / "celery_beat.log"),
            "formatter": "default",
        },
        "api_client_file": {
            "level": "DEBUG",
            "class": "logging.FileHandler", 
            "filename": str(LOG_FOLDER / "api_client.log"),
            "formatter": "default",
        }
    },
    "loggers": {
        "django": {
            "handlers": ["django_file", "debug_file", "info_file", "warning_file", "error_file", "critical_file"],
            "level": "DEBUG", 
            "propagate": True
        },
        "dicom_handler_logs": {
            "handlers": ["dicom_handler_file", "debug_file", "info_file", "warning_file", "error_file", "critical_file"],
            "level": "DEBUG",
            "propagate": True
        },
        "deidapp": {
            "handlers": ["deidapp_file", "debug_file", "info_file", "warning_file", "error_file", "critical_file"],
            "level": "DEBUG",
            "propagate": True
        },
        "celery": {
            "handlers": ["celery_file", "debug_file", "info_file", "warning_file", "error_file", "critical_file"],
            "level": "DEBUG",
            "propagate": True
        },
        "celery.task": {
            "handlers": ["celery_file", "debug_file", "info_file", "warning_file", "error_file", "critical_file"],
            "level": "DEBUG",
            "propagate": True
        },
        "celery.beat": {
            "handlers": ["celery_beat_file", "debug_file", "info_file", "warning_file", "error_file", "critical_file"],
            "level": "DEBUG",
            "propagate": True
        },
        "api_client": {
            "handlers": ["api_client_file", "debug_file", "info_file", "warning_file", "error_file", "critical_file"],
            "level": "DEBUG",
            "propagate": True
        }
    }
}

# ALLOW_JS_LOGGING = DEBUG # it's recommendable not to allow client logging in production

# Celery Configuration

CELERY_RESULT_BACKEND = 'django-db'
CELERY_CACHE_BACKEND = 'django-cache'
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Asia/Kolkata'
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'
CELERY_BEAT_PERIODIC = True
