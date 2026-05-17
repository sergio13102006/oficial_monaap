from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Servicio
from servicios_web.models import ServicioWeb

@receiver(post_save, sender=Servicio)
def sincronizar_servicio_en_web(sender, instance, created, **kwargs):
    ServicioWeb.objects.update_or_create(
        servicio_origen=instance,
        defaults={
            'nombre': instance.nombre,
            'descripcion': instance.descripcion,
            'precio': instance.precio,
            'imagen': instance.imagen,
            'video': instance.video,
            'activo': instance.activo,
        }
    )

@receiver(post_delete, sender=Servicio)
def eliminar_servicio_web_relacionado(sender, instance, **kwargs):
    ServicioWeb.objects.filter(servicio_origen=instance).delete()