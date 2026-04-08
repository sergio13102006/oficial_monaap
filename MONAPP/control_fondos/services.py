from decimal import Decimal

from django.db import models, transaction
from django.db.models import Sum
from django.db.models.functions import Coalesce
from django.utils import timezone

from .models import (
    BaseDiariaCuenta,
    CuentaFinanciera,
    JornadaDiaria,
    MovimientoCuenta,
    TransferenciaCuenta,
)


ZERO = Decimal("0")
DEFAULT_CUENTAS = (
    {
        "nombre": "Caja Principal",
        "tipo": CuentaFinanciera.TIPO_EFECTIVO,
        "orden_visual": 1,
    },
    {
        "nombre": "Bancolombia",
        "tipo": CuentaFinanciera.TIPO_BANCO,
        "orden_visual": 2,
    },
)


class ControlFondosError(Exception):
    pass


def asegurar_cuentas_base():
    cuentas = []
    for data in DEFAULT_CUENTAS:
        cuenta, _ = CuentaFinanciera.objects.get_or_create(
            nombre=data["nombre"],
            defaults={
                "tipo": data["tipo"],
                "activa": True,
                "orden_visual": data["orden_visual"],
            },
        )
        changed = False
        if cuenta.tipo != data["tipo"]:
            cuenta.tipo = data["tipo"]
            changed = True
        if not cuenta.activa:
            cuenta.activa = True
            changed = True
        if cuenta.orden_visual != data["orden_visual"]:
            cuenta.orden_visual = data["orden_visual"]
            changed = True
        if changed:
            cuenta.save(update_fields=["tipo", "activa", "orden_visual"])
        cuentas.append(cuenta)
    return cuentas


def _normalize_request_uid(request_uid):
    value = (request_uid or "").strip()
    return value or None


def _request_uid_with_suffix(request_uid, suffix):
    request_uid = _normalize_request_uid(request_uid)
    if not request_uid:
        return None
    return f"{request_uid}:{suffix}"


def cerrar_jornadas_previas(fecha_actual=None):
    fecha_actual = fecha_actual or timezone.localdate()
    JornadaDiaria.objects.filter(
        fecha__lt=fecha_actual,
        estado=JornadaDiaria.ESTADO_ABIERTA,
    ).update(
        estado=JornadaDiaria.ESTADO_CERRADA_AUTO,
        fecha_cierre_auto=timezone.now(),
    )


def obtener_o_crear_jornada(*, fecha=None, usuario=None):
    fecha = fecha or timezone.localdate()
    with transaction.atomic():
        cerrar_jornadas_previas(fecha)
        jornada, created = JornadaDiaria.objects.get_or_create(
            fecha=fecha,
            defaults={"creada_por": usuario},
        )
        return jornada, created


def obtener_base_diaria(*, cuenta, fecha=None, lock=False):
    fecha = fecha or timezone.localdate()
    jornada, _ = obtener_o_crear_jornada(fecha=fecha)
    qs = BaseDiariaCuenta.objects.filter(jornada=jornada, cuenta=cuenta)
    if lock:
        qs = qs.select_for_update()
    base = qs.first()
    if not base:
        raise ControlFondosError(
            f"La cuenta {cuenta.nombre} no tiene base inicial registrada para {fecha:%Y-%m-%d}."
        )
    return base


def registrar_base_diaria(*, cuenta, base_inicial, usuario=None, fecha=None, observacion=""):
    fecha = fecha or timezone.localdate()
    base_inicial = Decimal(base_inicial or 0)
    if base_inicial < 0:
        raise ControlFondosError("La base inicial no puede ser negativa.")

    with transaction.atomic():
        jornada, _ = obtener_o_crear_jornada(fecha=fecha, usuario=usuario)
        base, created = BaseDiariaCuenta.objects.select_for_update().get_or_create(
            jornada=jornada,
            cuenta=cuenta,
            defaults={
                "base_inicial": base_inicial,
                "registrada_por": usuario,
                "observacion": observacion or "",
            },
        )
        if created:
            return base

        tiene_movimientos = MovimientoCuenta.objects.select_for_update().filter(
            jornada=jornada,
            cuenta=cuenta,
            estado=MovimientoCuenta.ESTADO_ACTIVO,
        ).exists()
        if tiene_movimientos and base.base_inicial != base_inicial:
            raise ControlFondosError(
                "No puedes editar la base inicial porque la cuenta ya tiene movimientos registrados ese día."
            )

        changed = False
        if base.base_inicial != base_inicial:
            base.base_inicial = base_inicial
            changed = True
        if observacion is not None and base.observacion != (observacion or ""):
            base.observacion = observacion or ""
            changed = True
        if usuario and base.registrada_por_id is None:
            base.registrada_por = usuario
            changed = True
        if changed:
            base.save(update_fields=["base_inicial", "observacion", "registrada_por"])
        return base


def _aggregate_movimientos_activos(*, jornada, cuenta):
    aggregates = MovimientoCuenta.objects.filter(
        jornada=jornada,
        cuenta=cuenta,
        estado=MovimientoCuenta.ESTADO_ACTIVO,
    ).aggregate(
        entradas=Coalesce(Sum("valor", filter=models.Q(tipo=MovimientoCuenta.TIPO_ENTRADA)), ZERO),
        salidas=Coalesce(Sum("valor", filter=models.Q(tipo=MovimientoCuenta.TIPO_SALIDA)), ZERO),
    )
    return aggregates["entradas"] or ZERO, aggregates["salidas"] or ZERO


def calcular_saldo_cuenta(*, cuenta, fecha=None):
    fecha = fecha or timezone.localdate()
    jornada, _ = obtener_o_crear_jornada(fecha=fecha)
    try:
        base = BaseDiariaCuenta.objects.get(jornada=jornada, cuenta=cuenta)
    except BaseDiariaCuenta.DoesNotExist:
        return {
            "jornada": jornada,
            "cuenta": cuenta,
            "base_inicial": ZERO,
            "entradas": ZERO,
            "salidas": ZERO,
            "saldo_actual": ZERO,
            "tiene_base": False,
        }

    entradas, salidas = _aggregate_movimientos_activos(jornada=jornada, cuenta=cuenta)
    saldo_actual = (base.base_inicial or ZERO) + entradas - salidas
    return {
        "jornada": jornada,
        "cuenta": cuenta,
        "base_inicial": base.base_inicial or ZERO,
        "entradas": entradas,
        "salidas": salidas,
        "saldo_actual": saldo_actual,
        "tiene_base": True,
    }


def resumen_jornada(*, fecha=None, incluir_inactivas=False):
    fecha = fecha or timezone.localdate()
    jornada, _ = obtener_o_crear_jornada(fecha=fecha)
    asegurar_cuentas_base()
    cuentas = CuentaFinanciera.objects.all()
    if not incluir_inactivas:
        cuentas = cuentas.filter(activa=True)
    resumen = [calcular_saldo_cuenta(cuenta=cuenta, fecha=fecha) for cuenta in cuentas.order_by("orden_visual", "nombre")]
    return {
        "jornada": jornada,
        "resumen": resumen,
        "total_general": sum((item["saldo_actual"] for item in resumen), ZERO),
    }


def obtener_destacados_dashboard(*, fecha=None):
    fecha = fecha or timezone.localdate()
    resumen_data = resumen_jornada(fecha=fecha)
    resumen = resumen_data["resumen"]

    def _find_by_tipo(tipo):
        for item in resumen:
            if item["cuenta"].tipo == tipo:
                return item
        return None

    caja = _find_by_tipo(CuentaFinanciera.TIPO_EFECTIVO)
    banco = _find_by_tipo(CuentaFinanciera.TIPO_BANCO)
    pendientes_base = sum(1 for item in resumen if not item["tiene_base"])
    cuentas_abiertas = sum(1 for item in resumen if item["tiene_base"])

    return {
        "caja_principal": caja,
        "banco_principal": banco,
        "total_disponible": resumen_data["total_general"],
        "cuentas_pendientes_base": pendientes_base,
        "cuentas_abiertas_hoy": cuentas_abiertas,
        "total_cuentas_activas": len(resumen),
    }


def listar_movimientos(
    *,
    fecha=None,
    cuenta_id=None,
    tipo=None,
    clase=None,
    usuario_id=None,
    estado=None,
    q=None,
    solo_relevantes=False,
    solo_correcciones=False,
):
    fecha = fecha or timezone.localdate()
    jornada, _ = obtener_o_crear_jornada(fecha=fecha)
    qs = (
        MovimientoCuenta.objects
        .filter(jornada=jornada)
        .select_related("cuenta", "usuario", "movimiento_origen", "compra", "servicio", "colaborador")
        .order_by("-fecha_hora", "-id")
    )

    if cuenta_id:
        qs = qs.filter(cuenta_id=cuenta_id)
    if tipo:
        qs = qs.filter(tipo=tipo)
    if clase:
        qs = qs.filter(clase=clase)
    if usuario_id:
        qs = qs.filter(usuario_id=usuario_id)
    if estado:
        qs = qs.filter(estado=estado)
    if q:
        q = q.strip()
        if q:
            qs = qs.filter(
                models.Q(concepto__icontains=q)
                | models.Q(referencia__icontains=q)
            )
    if solo_relevantes:
        qs = qs.exclude(estado=MovimientoCuenta.ESTADO_ANULADO, movimientos_reversa__isnull=False)
    if solo_correcciones:
        qs = qs.filter(
            models.Q(clase__in=[MovimientoCuenta.CLASE_REVERSA, MovimientoCuenta.CLASE_ANULACION])
            | models.Q(movimiento_origen__isnull=False)
            | models.Q(movimientos_reversa__isnull=False)
        ).distinct()

    totales_por_clase = list(
        qs.filter(estado=MovimientoCuenta.ESTADO_ACTIVO)
        .values("clase")
        .annotate(total=Coalesce(Sum("valor"), ZERO))
        .order_by("clase")
    )

    resumen = qs.aggregate(
        entradas=Coalesce(Sum("valor", filter=models.Q(tipo=MovimientoCuenta.TIPO_ENTRADA, estado=MovimientoCuenta.ESTADO_ACTIVO)), ZERO),
        salidas=Coalesce(Sum("valor", filter=models.Q(tipo=MovimientoCuenta.TIPO_SALIDA, estado=MovimientoCuenta.ESTADO_ACTIVO)), ZERO),
        total_movimientos=Coalesce(models.Count("id"), 0),
        reversas_anulaciones=Coalesce(
            models.Count(
                "id",
                filter=models.Q(
                    clase__in=[MovimientoCuenta.CLASE_REVERSA, MovimientoCuenta.CLASE_ANULACION]
                ),
            ),
            0,
        ),
    )
    resumen["saldo_neto"] = (resumen["entradas"] or ZERO) - (resumen["salidas"] or ZERO)

    return {
        "jornada": jornada,
        "movimientos": qs,
        "totales_por_clase": totales_por_clase,
        "resumen_movimientos": resumen,
    }


def detalle_cuenta(*, cuenta, fecha=None):
    fecha = fecha or timezone.localdate()
    saldo = calcular_saldo_cuenta(cuenta=cuenta, fecha=fecha)
    movimientos_data = listar_movimientos(fecha=fecha, cuenta_id=cuenta.pk)
    transferencias_enviadas = movimientos_data["movimientos"].filter(
        clase=MovimientoCuenta.CLASE_TRANSFERENCIA,
        tipo=MovimientoCuenta.TIPO_SALIDA,
    ).count()
    transferencias_recibidas = movimientos_data["movimientos"].filter(
        clase=MovimientoCuenta.CLASE_TRANSFERENCIA,
        tipo=MovimientoCuenta.TIPO_ENTRADA,
    ).count()
    return {
        "detalle_cuenta": saldo,
        "movimientos_cuenta": movimientos_data["movimientos"],
        "resumen_movimientos": movimientos_data["resumen_movimientos"],
        "totales_por_clase": movimientos_data["totales_por_clase"],
        "transferencias_enviadas": transferencias_enviadas,
        "transferencias_recibidas": transferencias_recibidas,
    }


def crear_movimiento(
    *,
    cuenta,
    tipo,
    clase,
    valor,
    concepto,
    usuario=None,
    fecha=None,
    referencia="",
    compra=None,
    servicio=None,
    colaborador=None,
    request_uid=None,
    movimiento_origen=None,
):
    request_uid = _normalize_request_uid(request_uid)
    if request_uid:
        existing = MovimientoCuenta.objects.filter(request_uid=request_uid).first()
        if existing:
            return existing, False

    valor = Decimal(valor or 0)
    if valor <= 0:
        raise ControlFondosError("El valor del movimiento debe ser mayor que cero.")

    fecha = fecha or timezone.localdate()
    with transaction.atomic():
        jornada, _ = obtener_o_crear_jornada(fecha=fecha, usuario=usuario)
        base = obtener_base_diaria(cuenta=cuenta, fecha=fecha, lock=True)
        if base.jornada_id != jornada.pk:
            raise ControlFondosError("La base del día no coincide con la jornada activa de la cuenta.")

        if request_uid:
            existing = MovimientoCuenta.objects.select_for_update().filter(request_uid=request_uid).first()
            if existing:
                return existing, False

        movimiento = MovimientoCuenta.objects.create(
            jornada=jornada,
            cuenta=cuenta,
            tipo=tipo,
            clase=clase,
            valor=valor,
            concepto=concepto,
            referencia=referencia or "",
            usuario=usuario,
            movimiento_origen=movimiento_origen,
            compra=compra,
            servicio=servicio,
            colaborador=colaborador,
            request_uid=request_uid,
        )
        return movimiento, True


def reversar_movimiento(
    movimiento,
    *,
    usuario=None,
    request_uid=None,
    concepto=None,
    clase_reversa=MovimientoCuenta.CLASE_REVERSA,
):
    request_uid = _normalize_request_uid(request_uid)
    with transaction.atomic():
        movimiento = MovimientoCuenta.objects.select_for_update().select_related(
            "cuenta", "jornada", "compra", "servicio", "colaborador"
        ).get(pk=movimiento.pk)

        if request_uid:
            existing = MovimientoCuenta.objects.select_for_update().filter(request_uid=request_uid).first()
            if existing:
                return existing, False

        if movimiento.estado == MovimientoCuenta.ESTADO_ANULADO:
            existente = movimiento.movimientos_reversa.order_by("-id").first()
            if existente:
                return existente, False
            raise ControlFondosError("El movimiento ya se encuentra anulado.")

        obtener_base_diaria(cuenta=movimiento.cuenta, fecha=movimiento.jornada.fecha, lock=True)
        reverse_tipo = MovimientoCuenta.TIPO_SALIDA if movimiento.tipo == MovimientoCuenta.TIPO_ENTRADA else MovimientoCuenta.TIPO_ENTRADA
        reversa = MovimientoCuenta.objects.create(
            jornada=movimiento.jornada,
            cuenta=movimiento.cuenta,
            tipo=reverse_tipo,
            clase=clase_reversa,
            valor=movimiento.valor,
            concepto=concepto or f"Reversa de movimiento #{movimiento.pk}",
            referencia=movimiento.referencia,
            usuario=usuario,
            movimiento_origen=movimiento,
            compra=movimiento.compra,
            servicio=movimiento.servicio,
            colaborador=movimiento.colaborador,
            request_uid=request_uid,
        )
        movimiento.estado = MovimientoCuenta.ESTADO_ANULADO
        movimiento.save(update_fields=["estado"])
        return reversa, True


def registrar_salida_por_compra(*, compra, request_uid=None, user=None):
    if not compra.cuenta_financiera:
        raise ControlFondosError("Debes seleccionar una cuenta financiera para registrar la compra.")
    return crear_movimiento(
        cuenta=compra.cuenta_financiera,
        tipo=MovimientoCuenta.TIPO_SALIDA,
        clase=MovimientoCuenta.CLASE_COMPRA,
        valor=compra.precio_total,
        concepto=f"Salida por compra #{compra.pk}",
        usuario=user,
        fecha=compra.fecha,
        referencia=f"COMPRA-{compra.pk}",
        compra=compra,
        request_uid=request_uid,
    )


def sincronizar_movimientos_compra(*, compra, request_uid=None, user=None):
    with transaction.atomic():
        compra = compra.__class__.objects.select_for_update().get(pk=compra.pk)
        activos = list(MovimientoCuenta.objects.select_for_update().filter(
            compra=compra,
            clase=MovimientoCuenta.CLASE_COMPRA,
            estado=MovimientoCuenta.ESTADO_ACTIVO,
        ))
        for idx, movimiento in enumerate(activos, start=1):
            reversar_movimiento(
                movimiento,
                usuario=user,
                request_uid=_request_uid_with_suffix(request_uid, f"rev-{idx}"),
                concepto=f"Corrección de compra #{compra.pk}",
                clase_reversa=MovimientoCuenta.CLASE_REVERSA,
            )
        return registrar_salida_por_compra(
            compra=compra,
            request_uid=_request_uid_with_suffix(request_uid, "nuevo"),
            user=user,
        )


def anular_movimientos_compra(*, compra, request_uid=None, user=None):
    with transaction.atomic():
        activos = list(MovimientoCuenta.objects.select_for_update().filter(
            compra=compra,
            clase=MovimientoCuenta.CLASE_COMPRA,
            estado=MovimientoCuenta.ESTADO_ACTIVO,
        ))
        reversas = []
        for idx, movimiento in enumerate(activos, start=1):
            reversa, _ = reversar_movimiento(
                movimiento,
                usuario=user,
                request_uid=_request_uid_with_suffix(request_uid, f"anulacion-{idx}"),
                concepto=f"Anulación de compra #{compra.pk}",
                clase_reversa=MovimientoCuenta.CLASE_ANULACION,
            )
            reversas.append(reversa)
        return reversas


def registrar_ingreso_por_servicio(*, servicio, request_uid=None, user=None, valor=None, cuenta=None, colaborador=None):
    cuenta = cuenta or getattr(servicio, "cuenta_financiera", None)
    if not cuenta:
        raise ControlFondosError("Debes seleccionar una cuenta financiera para registrar el cobro del servicio.")
    valor = Decimal(valor if valor is not None else (servicio.precio_alisado or 0) - (servicio.saldo_pendiente or 0))
    if valor <= 0:
        raise ControlFondosError("El servicio no tiene un valor cobrado válido para registrar como entrada.")
    return crear_movimiento(
        cuenta=cuenta,
        tipo=MovimientoCuenta.TIPO_ENTRADA,
        clase=MovimientoCuenta.CLASE_SERVICIO,
        valor=valor,
        concepto=f"Ingreso por servicio #{servicio.pk}",
        usuario=user,
        fecha=(servicio.fecha_hora.date() if getattr(servicio, "fecha_hora", None) else timezone.localdate()),
        referencia=f"SERVICIO-{servicio.pk}",
        servicio=servicio,
        colaborador=colaborador,
        request_uid=request_uid,
    )


def registrar_transferencia(*, cuenta_origen, cuenta_destino, valor, usuario=None, fecha=None, request_uid=None, observacion=""):
    if cuenta_origen.pk == cuenta_destino.pk:
        raise ControlFondosError("La cuenta origen y la cuenta destino deben ser distintas.")
    observacion = (observacion or "").strip()
    with transaction.atomic():
        salida, _ = crear_movimiento(
            cuenta=cuenta_origen,
            tipo=MovimientoCuenta.TIPO_SALIDA,
            clase=MovimientoCuenta.CLASE_TRANSFERENCIA,
            valor=valor,
            concepto=f"Transferencia hacia {cuenta_destino.nombre}" + (f" | {observacion}" if observacion else ""),
            usuario=usuario,
            fecha=fecha,
            referencia=f"TRANSFER-{cuenta_origen.pk}-{cuenta_destino.pk}",
            request_uid=_request_uid_with_suffix(request_uid, "salida"),
        )
        entrada, _ = crear_movimiento(
            cuenta=cuenta_destino,
            tipo=MovimientoCuenta.TIPO_ENTRADA,
            clase=MovimientoCuenta.CLASE_TRANSFERENCIA,
            valor=valor,
            concepto=f"Transferencia desde {cuenta_origen.nombre}" + (f" | {observacion}" if observacion else ""),
            usuario=usuario,
            fecha=fecha,
            referencia=f"TRANSFER-{cuenta_origen.pk}-{cuenta_destino.pk}",
            request_uid=_request_uid_with_suffix(request_uid, "entrada"),
        )
        transferencia = TransferenciaCuenta.objects.filter(
            movimiento_salida=salida,
            movimiento_entrada=entrada,
        ).first()
        if transferencia:
            return transferencia
        return TransferenciaCuenta.objects.create(
            cuenta_origen=cuenta_origen,
            cuenta_destino=cuenta_destino,
            valor=Decimal(valor or 0),
            movimiento_salida=salida,
            movimiento_entrada=entrada,
            usuario=usuario,
        )
