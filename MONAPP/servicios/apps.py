from django.apps import AppConfig

class ServiciosConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'servicios'
    verbose_name = 'Gestión de Servicios'

    def ready(self):
        import servicios.signals