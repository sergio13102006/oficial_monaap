from __future__ import annotations

from datetime import timedelta

from django.contrib.auth.models import User
from django.db import models as djmodels
from django.db import transaction
from django.utils import timezone

from clientes.models import Cliente
from promociones.models import Promocion
from usuarios.models import PerfilUsuario

from .models import Notificacion


GRUPO_PERMITIDO = ["Administrador", "Auxiliar"]


def _es_admin_o_auxiliar(user: User) -> bool:
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return user.groups.filter(name__in=GRUPO_PERMITIDO).exists()


def _marker_promo(promo_id, dias: int) -> str:
    return f"[#PROMO_VENCE:{promo_id}:{dias}]"


def _marker_cumple(cliente_id, when: str) -> str:
    return f"[#CUMPLE:{cliente_id}:{when}]"


def destinatarios_admin_aux() -> list[User]:
    return list(
        User.objects.filter(is_active=True)
        .filter(
            djmodels.Q(is_superuser=True)
            | djmodels.Q(groups__name__in=GRUPO_PERMITIDO)
        )
        .distinct()
    )


@transaction.atomic
def generar_alertas_para_usuario(user: User, fecha_base=None) -> None:
    """
    Crea notificaciones (idempotentes) para:
    - Promociones por vencer: 7 y 1 día antes de fecha_fin
    - Cumpleaños: hoy y mañana (clientes)

    Se ejecuta por usuario para evitar recrear masivamente en cada polling.
    """
    if not _es_admin_o_auxiliar(user):
        return

    hoy = fecha_base or timezone.localdate()
    manana = hoy + timedelta(days=1)

    # ========= Promociones por vencer (7 y 1 día) =========
    alertas_promo = []
    for dias, tipo, urgente in [
        (7, "warning", False),
        (1, "danger", True),
    ]:
        objetivo = hoy + timedelta(days=dias)
        promos = Promocion.objects.filter(activa=True, fecha_fin=objetivo)
        for p in promos:
            marker = _marker_promo(p.id, dias)
            titulo = "Promoción por vencer"
            mensaje = (
                f'Tu promoción "{p.nombre}" vence el {p.fecha_fin.strftime("%d/%m/%Y")} '
                f"(en {dias} día{'s' if dias != 1 else ''}). {marker}"
            )
            alertas_promo.append((marker, titulo, mensaje, tipo, urgente))

    # limpiar alertas promo obsoletas (solo no leídas)
    esperados_promo = {m for (m, *_rest) in alertas_promo}
    existentes_promo = Notificacion.objects.filter(
        destinatario=user,
        leida=False,
        mensaje__contains="[#PROMO_VENCE:",
    )
    for n in existentes_promo:
        keep = any(marker in n.mensaje for marker in esperados_promo)
        if not keep:
            n.delete()

    # crear las nuevas (si no existen)
    for marker, titulo, mensaje, tipo, urgente in alertas_promo:
        if Notificacion.objects.filter(destinatario=user, leida=False, mensaje__contains=marker).exists():
            continue
        Notificacion.objects.create(
            destinatario=user,
            titulo=titulo,
            mensaje=mensaje,
            tipo=tipo,
            urgente=urgente,
        )

    # ========= Cumpleaños hoy / mañana =========
    def _rol_de_usuario(u: User) -> str:
        if not u:
            return "colaborador"
        if u.groups.filter(name="Auxiliar").exists():
            return "auxiliar"
        if u.groups.filter(name="Colaborador").exists():
            return "colaborador"
        # Administrador/superuser se reporta como colaborador (según solicitud)
        return "colaborador"

    def _nombre_usuario(u: User) -> str:
        if not u:
            return ""
        full = f"{(u.first_name or '').strip()} {(u.last_name or '').strip()}".strip()
        return full or (u.username or "Usuario")

    cumples = []
    for when, fecha_obj in [("hoy", hoy), ("manana", manana)]:
        # Clientes
        qs_clientes = Cliente.objects.filter(
            fecha_nacimiento__month=fecha_obj.month,
            fecha_nacimiento__day=fecha_obj.day,
        )
        for c in qs_clientes:
            marker = _marker_cumple(c.id, when)
            nombre = f"{c.nombre} {getattr(c, 'apellido', '')}".strip()
            edad = fecha_obj.year - c.fecha_nacimiento.year if c.fecha_nacimiento else None
            titulo = "Cumpleaños"
            if when == "hoy":
                msg = f"Hoy cumple tu cliente {nombre} {edad} años. {marker}"
                tipo = "success"
            else:
                msg = f"Mañana cumple tu cliente {nombre} {edad} años. {marker}"
                tipo = "info"
            cumples.append((marker, titulo, msg, tipo, False))

        # Usuarios/Colaboradores/Auxiliares (PerfilUsuario)
        perfiles = (
            PerfilUsuario.objects.select_related("user")
            .filter(
                fecha_nacimiento__isnull=False,
                fecha_nacimiento__month=fecha_obj.month,
                fecha_nacimiento__day=fecha_obj.day,
            )
        )
        for p in perfiles:
            u = p.user
            rol = _rol_de_usuario(u)
            nombre = _nombre_usuario(u)
            edad = fecha_obj.year - p.fecha_nacimiento.year if p.fecha_nacimiento else None
            marker = _marker_cumple(f"user-{u.id}", when)
            titulo = "Cumpleaños"
            if when == "hoy":
                msg = f"Hoy cumple tu {rol} {nombre} {edad} años. {marker}"
                tipo = "success"
            else:
                msg = f"Mañana cumple tu {rol} {nombre} {edad} años. {marker}"
                tipo = "info"
            cumples.append((marker, titulo, msg, tipo, False))

    esperados_cumple = {m for (m, *_rest) in cumples}
    existentes_cumple = Notificacion.objects.filter(
        destinatario=user,
        leida=False,
        mensaje__contains="[#CUMPLE:",
    )
    for n in existentes_cumple:
        keep = any(marker in n.mensaje for marker in esperados_cumple)
        if not keep:
            n.delete()

    for marker, titulo, mensaje, tipo, urgente in cumples:
        if Notificacion.objects.filter(destinatario=user, leida=False, mensaje__contains=marker).exists():
            continue
        Notificacion.objects.create(
            destinatario=user,
            titulo=titulo,
            mensaje=mensaje,
            tipo=tipo,
            urgente=urgente,
        )
