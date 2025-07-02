from django.apps import AppConfig


class DatabaseConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'swf_fastmon_agent.database'
    label = 'database'