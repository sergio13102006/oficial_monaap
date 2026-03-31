# notificaciones/management/commands/revisar_stock.py
#
# Revisa TODOS los stocks y crea/recrea notificaciones.
# - Stock == 0  → SIEMPRE recrea (aunque ya la hayan aceptado)
# - Stock 1-5   → solo crea si no hay una no leída ya
# - Stock > 5   → limpia notificaciones anteriores de ese producto
#
# Uso:
#   python manage.py revisar_stock

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.db import models as djmodels

from inventario.models import Stock
from notificaciones.models import Notificacion

UMBRAL_BAJO = 5


def _destinatarios():
    return User.objects.filter(
        is_active=True,
    ).filter(
        djmodels.Q(is_superuser=True) |
        djmodels.Q(groups__name__in=['Administrador', 'Auxiliar'])
    ).distinct()


class Command(BaseCommand):
    help = 'Revisa stock actual y crea/recrea notificaciones de alerta'

    def handle(self, *args, **options):
        destinatarios = _destinatarios()

        if not destinatarios.exists():
            self.stderr.write('No hay Administradores ni Auxiliares activos.')
            return

        stocks    = Stock.objects.select_related('producto').all()
        creadas   = 0
        limpiadas = 0

        for stock in stocks:
            nombre   = stock.producto.nombre
            cantidad = stock.cantidad_actual

            if cantidad <= 0:
                # ── Stock cero: SIEMPRE recrea ───────────────────────────────
                titulo = f'Sin stock: {nombre}'
                for usuario in destinatarios:
                    Notificacion.objects.filter(
                        destinatario=usuario,
                        titulo=titulo,
                    ).delete()
                    Notificacion.objects.create(
                        destinatario=usuario,
                        titulo=titulo,
                        mensaje=(
                            f'El producto "{nombre}" tiene 0 unidades disponibles. '
                            f'Reabastece urgentemente.'
                        ),
                        tipo='danger',
                        urgente=True,
                    )
                    creadas += 1

            elif 1 <= cantidad <= UMBRAL_BAJO:
                # ── Stock bajo: solo si no hay una no leída ──────────────────
                titulo = f'Stock bajo: {nombre}'
                for usuario in destinatarios:
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
                                f'unidad{"es" if cantidad != 1 else ""} disponible{"s" if cantidad != 1 else ""}.'
                            ),
                            tipo='warning',
                            urgente=False,
                        )
                        creadas += 1

            else:
                # ── Stock OK: limpiar alertas anteriores ─────────────────────
                eliminadas = Notificacion.objects.filter(
                    djmodels.Q(titulo=f'Sin stock: {nombre}') |
                    djmodels.Q(titulo=f'Stock bajo: {nombre}')
                ).delete()[0]
                limpiadas += eliminadas

        self.stdout.write(self.style.SUCCESS(
            f'✓ {creadas} notificaciones creadas/recreadas. '
            f'{limpiadas} notificaciones obsoletas eliminadas.'
        ))