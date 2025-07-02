"""
Django settings for the SWF Fast Monitoring Agent database module.
"""

import os

# Database configuration using environment variables
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('POSTGRES_DB', 'swf_fastmonitoring'),
        'USER': os.getenv('POSTGRES_USER', 'postgres'),
        'PASSWORD': os.getenv('POSTGRES_PASSWORD', 'postgres'),
        'HOST': os.getenv('POSTGRES_HOST', 'localhost'),
        'PORT': os.getenv('POSTGRES_PORT', '5432'),
    }
}

# Minimal Django configuration for database operations
INSTALLED_APPS = [
    'django.contrib.contenttypes',
    'swf_fastmon_agent.database',
]

# Security settings
SECRET_KEY = os.getenv('SECRET_KEY', 'dev-key-for-database-operations')
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'

# Timezone settings
USE_TZ = True
TIME_ZONE = 'UTC'

# Default auto field
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Logging configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'swf_fastmon_agent': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}