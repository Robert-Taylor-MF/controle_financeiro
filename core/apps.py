from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'

    def ready(self):
        try:
            from .backup_service import iniciar_agendador_backup
            iniciar_agendador_backup()
        except ImportError:
            pass
