from django.contrib.auth.models import User
from django.db import models as djmodels
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from .models import Stock

UMBRAL_BAJO = 5


def _estado_stock(cantidad):
    if cantidad <= 0:
        return "cero"
    if cantidad <= UMBRAL_BAJO:
        return "bajo"
    return "ok"


def _destinatarios():
    return User.objects.filter(is_active=True).filter(
        djmodels.Q(is_superuser=True)
        | djmodels.Q(groups__name__in=["Administrador", "Auxiliar"])
    ).distinct().select_related("perfil")


def _emails_destinatarios():
    return [u.email for u in _destinatarios() if u.email]


def _crear_notif_stock_cero(nombre):
    from notificaciones.models import Notificacion

    titulo = f"Sin stock: {nombre}"

    for usuario in _destinatarios():
        Notificacion.objects.filter(destinatario=usuario, titulo=titulo).delete()
        Notificacion.objects.create(
            destinatario=usuario,
            titulo=titulo,
            mensaje=(
                f'El producto "{nombre}" tiene 0 unidades disponibles. '
                f"Reabastece urgentemente para evitar quiebres de inventario."
            ),
            tipo="danger",
            urgente=True,
        )


def _crear_notif_stock_bajo(nombre, cantidad):
    from notificaciones.models import Notificacion

    titulo = f"Stock bajo: {nombre}"

    for usuario in _destinatarios():
        ya_existe = Notificacion.objects.filter(
            destinatario=usuario,
            titulo=titulo,
            leida=False,
        ).exists()
        if not ya_existe:
            Notificacion.objects.create(
                destinatario=usuario,
                titulo=titulo,
                mensaje=(
                    f'El producto "{nombre}" solo tiene {cantidad} '
                    f'unidad{"es" if cantidad != 1 else ""} disponible{"s" if cantidad != 1 else ""}. '
                    f"Considera reabastecer pronto."
                ),
                tipo="warning",
                urgente=False,
            )


@receiver(pre_save, sender=Stock)
def _capturar_stock_anterior(sender, instance, **kwargs):
    if not instance.pk:
        instance._cantidad_anterior = None
        return

    instance._cantidad_anterior = (
        Stock.objects.filter(pk=instance.pk)
        .values_list("cantidad_actual", flat=True)
        .first()
    )


@receiver(post_save, sender=Stock)
def notificar_stock(sender, instance, created=False, **kwargs):
    cantidad = instance.cantidad_actual
    nombre = instance.producto.nombre
    cantidad_anterior = getattr(instance, "_cantidad_anterior", None)

    if cantidad_anterior is not None and _estado_stock(cantidad_anterior) == _estado_stock(cantidad):
        return

    if cantidad <= 0:
        _crear_notif_stock_cero(nombre)
        from notificaciones.email_alertas import enviar_alerta_stock_cero

        enviar_alerta_stock_cero(nombre, _emails_destinatarios())
    elif 1 <= cantidad <= UMBRAL_BAJO:
        from notificaciones.models import Notificacion

        Notificacion.objects.filter(
            titulo=f"Sin stock: {nombre}",
            leida=True,
        ).delete()
        _crear_notif_stock_bajo(nombre, cantidad)
        from notificaciones.email_alertas import enviar_alerta_stock_bajo

        enviar_alerta_stock_bajo(nombre, cantidad, _emails_destinatarios())
    else:
        from notificaciones.models import Notificacion

        Notificacion.objects.filter(
            djmodels.Q(titulo=f"Sin stock: {nombre}")
            | djmodels.Q(titulo=f"Stock bajo: {nombre}")
        ).delete()

