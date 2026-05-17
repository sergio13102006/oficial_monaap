from decimal import Decimal

from django.db import models, transaction
from django.db.models import Sum
from django.db.models.functions import Coalesce
from django.utils import timezone

from .models import (
    BaseDiariaCuenta,
    BitacoraFondos,
    CuentaFinanciera,
    JornadaDiaria,
    MovimientoCuenta,
    TransferenciaCuenta,
)


ZERO = Decimal("0")
DEFAULT_CUENTAS = (
    {
        "codigo": "CAJA_PRINCIPAL",
        "nombre": "Caja Principal",
        "tipo": CuentaFinanciera.TIPO_EFECTIVO,
        "categoria_operativa": CuentaFinanciera.CATEGORIA_CAJA,
        "obligatoria_apertura": True,
        "requiere_base_inicial": True,
        "requiere_referencia": False,
        "permite_entradas": True,
        "permite_salidas": True,
        "orden_visual": 1,
    },
    {
        "codigo": "CAJA_FUERTE",
        "nombre": "Caja Fuerte",
        "tipo": CuentaFinanciera.TIPO_CAJA_FUERTE,
        "categoria_operativa": CuentaFinanciera.CATEGORIA_CAJA_FUERTE,
        "obligatoria_apertura": True,
        "requiere_base_inicial": True,
        "requiere_referencia": False,
        "permite_entradas": True,
        "permite_salidas": True,
        "orden_visual": 2,
    },
    {
        "codigo": "BANCOLOMBIA",
        "nombre": "Bancolombia",
        "tipo": CuentaFinanciera.TIPO_BANCO,
        "categoria_operativa": CuentaFinanciera.CATEGORIA_BANCO,
        "obligatoria_apertura": True,
        "requiere_base_inicial": True,
        "requiere_referencia": True,
        "permite_entradas": True,
        "permite_salidas": True,
        "orden_visual": 3,
    },
    {
        "codigo": "NEQUI",
        "nombre": "Nequi",
        "tipo": CuentaFinanciera.TIPO_BILLETERA,
        "categoria_operativa": CuentaFinanciera.CATEGORIA_BILLETERA,
        "obligatoria_apertura": True,
        "requiere_base_inicial": True,
        "requiere_referencia": True,
        "permite_entradas": True,
        "permite_salidas": True,
        "orden_visual": 4,
    },
    {
        "codigo": "DAVIPLATA",
        "nombre": "Daviplata",
        "tipo": CuentaFinanciera.TIPO_BILLETERA,
        "categoria_operativa": CuentaFinanciera.CATEGORIA_BILLETERA,
        "obligatoria_apertura": True,
        "requiere_base_inicial": True,
        "requiere_referencia": True,
        "permite_entradas": True,
        "permite_salidas": True,
        "orden_visual": 5,
    },
    {
        "codigo": "NU_BANK",
        "nombre": "Nu Bank",
        "tipo": CuentaFinanciera.TIPO_BANCO,
        "categoria_operativa": CuentaFinanciera.CATEGORIA_BANCO,
        "obligatoria_apertura": True,
        "requiere_base_inicial": True,
        "requiere_referencia": True,
        "permite_entradas": True,
        "permite_salidas": True,
        "orden_visual": 6,
    },
    {
        "codigo": "DATAFONO",
        "nombre": "Datáfono",
        "tipo": CuentaFinanciera.TIPO_DATAFONO,
        "categoria_operativa": CuentaFinanciera.CATEGORIA_MEDIO_PAGO,
        "obligatoria_apertura": False,
        "requiere_base_inicial": False,
        "requiere_referencia": True,
        "permite_entradas": True,
        "permite_salidas": False,
        "orden_visual": 7,
    },
    {
        "codigo": "SISTECREDITO_ADDI",
        "nombre": "Sistecrédito / Addi",
        "tipo": CuentaFinanciera.TIPO_FINANCIACION,
        "categoria_operativa": CuentaFinanciera.CATEGORIA_FINANCIACION,
        "obligatoria_apertura": False,
        "requiere_base_inicial": False,
        "requiere_referencia": True,
        "permite_entradas": True,
        "permite_salidas": False,
        "orden_visual": 8,
    },
    {
        "codigo": "TARJETA_CREDITO_COMPRAS",
        "nombre": "Tarjeta Crédito Compras",
        "tipo": CuentaFinanciera.TIPO_TARJETA,
        "categoria_operativa": CuentaFinanciera.CATEGORIA_EGRESO,
        "obligatoria_apertura": False,
        "requiere_base_inicial": False,
        "requiere_referencia": True,
        "permite_entradas": False,
        "permite_salidas": True,
        "orden_visual": 9,
    },
)


class ControlFondosError(Exception):
    pass


def _normalize_request_uid(request_uid):
    value = (request_uid or "").strip()
    return value or None


def _request_uid_with_suffix(request_uid, suffix):
    request_uid = _normalize_request_uid(request_uid)
    if not request_uid:
        return None
    return f"{request_uid}:{suffix}"


def _decimal(value):
    return Decimal(value or 0)


def _registrar_bitacora(*, accion, modelo="", objeto_id="", datos_anteriores=None, datos_nuevos=None, motivo="", ip=None, dispositivo="", usuario=None):
    BitacoraFondos.objects.create(
        accion=accion,
        modelo=modelo,
        objeto_id=str(objeto_id or ""),
        datos_anteriores=datos_anteriores or {},
        datos_nuevos=datos_nuevos or {},
        motivo=motivo or "",
        ip=ip,
        dispositivo=dispositivo or "",
        usuario=usuario,
    )


def asegurar_cuentas_base():
    cuentas = []
    for data in DEFAULT_CUENTAS:
        cuenta, _ = CuentaFinanciera.objects.get_or_create(
            codigo=data["codigo"],
            defaults={
                "nombre": data["nombre"],
                "tipo": data["tipo"],
                "categoria_operativa": data["categoria_operativa"],
                "activa": True,
                "obligatoria_apertura": data["obligatoria_apertura"],
                "requiere_base_inicial": data["requiere_base_inicial"],
                "requiere_referencia": data["requiere_referencia"],
                "permite_entradas": data["permite_entradas"],
                "permite_salidas": data["permite_salidas"],
                "orden_visual": data["orden_visual"],
            },
        )
        changed = False
        if cuenta.nombre != data["nombre"]:
            cuenta.nombre = data["nombre"]
            changed = True
        if cuenta.tipo != data["tipo"]:
            cuenta.tipo = data["tipo"]
            changed = True
        if cuenta.categoria_operativa != data["categoria_operativa"]:
            cuenta.categoria_operativa = data["categoria_operativa"]
            changed = True
        if not cuenta.activa:
            cuenta.activa = True
            changed = True
        if cuenta.obligatoria_apertura != data["obligatoria_apertura"]:
            cuenta.obligatoria_apertura = data["obligatoria_apertura"]
            changed = True
        if cuenta.requiere_base_inicial != data["requiere_base_inicial"]:
            cuenta.requiere_base_inicial = data["requiere_base_inicial"]
            changed = True
        if cuenta.requiere_referencia != data["requiere_referencia"]:
            cuenta.requiere_referencia = data["requiere_referencia"]
            changed = True
        if cuenta.permite_entradas != data["permite_entradas"]:
            cuenta.permite_entradas = data["permite_entradas"]
            changed = True
        if cuenta.permite_salidas != data["permite_salidas"]:
            cuenta.permite_salidas = data["permite_salidas"]
            changed = True
        if cuenta.orden_visual != data["orden_visual"]:
            cuenta.orden_visual = data["orden_visual"]
            changed = True
        if not cuenta.codigo:
            cuenta.codigo = data["codigo"]
            changed = True
        if changed:
            cuenta.save(update_fields=[
                "codigo",
                "nombre",
                "tipo",
                "categoria_operativa",
                "activa",
                "obligatoria_apertura",
                "requiere_base_inicial",
                "requiere_referencia",
                "permite_entradas",
                "permite_salidas",
                "orden_visual",
            ])
        cuentas.append(cuenta)
    return cuentas


def _jornada_estado_desde_bases(*, jornada):
    cuentas_obligatorias = CuentaFinanciera.objects.filter(activa=True, requiere_base_inicial=True)
    if not cuentas_obligatorias.exists():
        return JornadaDiaria.ESTADO_ABIERTO
    bases_registradas = BaseDiariaCuenta.objects.filter(jornada=jornada).values_list("cuenta_id", flat=True)
    faltantes = cuentas_obligatorias.exclude(id__in=bases_registradas).count()
    if faltantes == 0:
        return JornadaDiaria.ESTADO_ABIERTO
    return JornadaDiaria.ESTADO_APERTURA_INCOMPLETA


def cerrar_jornadas_previas(fecha_actual=None):
    fecha_actual = fecha_actual or timezone.localdate()
    JornadaDiaria.objects.filter(
        fecha__lt=fecha_actual,
        estado__in=[
            JornadaDiaria.ESTADO_PENDIENTE_APERTURA,
            JornadaDiaria.ESTADO_ABIERTO,
            JornadaDiaria.ESTADO_EN_REVISION,
            JornadaDiaria.ESTADO_REABIERTO,
        ],
    ).update(
        estado=JornadaDiaria.ESTADO_CERRADA_AUTO,
        fecha_cierre=timezone.now(),
    )


def obtener_o_crear_jornada(*, fecha=None, usuario=None):
    fecha = fecha or timezone.localdate()
    with transaction.atomic():
        cerrar_jornadas_previas(fecha)
        jornada, created = JornadaDiaria.objects.get_or_create(
            fecha=fecha,
            defaults={
                "responsable_apertura": usuario,
                "estado": JornadaDiaria.ESTADO_PENDIENTE_APERTURA,
            },
        )
        return jornada, created


def abrir_jornada(*, fecha=None, usuario=None, sede="", base_inicial_caja=None, base_inicial_caja_fuerte=None, observacion=""):
    fecha = fecha or timezone.localdate()
    with transaction.atomic():
        jornada, _ = obtener_o_crear_jornada(fecha=fecha, usuario=usuario)
        jornada.sede = sede or jornada.sede
        jornada.responsable_apertura = usuario or jornada.responsable_apertura
        if base_inicial_caja is not None:
            jornada.base_inicial_caja = _decimal(base_inicial_caja)
        if base_inicial_caja_fuerte is not None:
            jornada.base_inicial_caja_fuerte = _decimal(base_inicial_caja_fuerte)
        if observacion is not None:
            jornada.observacion_apertura = observacion or jornada.observacion_apertura
        jornada.estado = _jornada_estado_desde_bases(jornada=jornada)
        jornada.save(
            update_fields=[
                "sede",
                "responsable_apertura",
                "base_inicial_caja",
                "base_inicial_caja_fuerte",
                "observacion_apertura",
                "estado",
            ]
        )
        _registrar_bitacora(
            accion="ABRIR_JORNADA",
            modelo="JornadaDiaria",
            objeto_id=jornada.pk,
            datos_nuevos={
                "fecha": str(jornada.fecha),
                "sede": jornada.sede,
                "estado": jornada.estado,
            },
            usuario=usuario,
        )
        return jornada


def obtener_base_diaria(*, cuenta, fecha=None, lock=False):
    fecha = fecha or timezone.localdate()
    if not getattr(cuenta, "requiere_base_inicial", True):
        return None
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
    base_inicial = _decimal(base_inicial)
    if base_inicial < 0:
        raise ControlFondosError("La base inicial no puede ser negativa.")
    if not getattr(cuenta, "requiere_base_inicial", True):
        raise ControlFondosError(f"La cuenta {cuenta.nombre} no requiere base inicial.")

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
            if cuenta.codigo == "CAJA_PRINCIPAL":
                jornada.base_inicial_caja = base_inicial
            elif cuenta.codigo == "CAJA_FUERTE":
                jornada.base_inicial_caja_fuerte = base_inicial
            jornada.estado = _jornada_estado_desde_bases(jornada=jornada)
            jornada.save(update_fields=["base_inicial_caja", "base_inicial_caja_fuerte", "estado"])
            _registrar_bitacora(
                accion="REGISTRAR_BASE",
                modelo="BaseDiariaCuenta",
                objeto_id=base.pk,
                datos_nuevos={
                    "jornada": jornada.pk,
                    "cuenta": cuenta.nombre,
                    "base_inicial": str(base_inicial),
                },
                usuario=usuario,
            )
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

        datos_anteriores = {
            "base_inicial": str(base.base_inicial),
            "observacion": base.observacion,
        }
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
        if cuenta.codigo == "CAJA_PRINCIPAL":
            jornada.base_inicial_caja = base_inicial
        elif cuenta.codigo == "CAJA_FUERTE":
            jornada.base_inicial_caja_fuerte = base_inicial
        jornada.estado = _jornada_estado_desde_bases(jornada=jornada)
        jornada.save(update_fields=["base_inicial_caja", "base_inicial_caja_fuerte", "estado"])
        _registrar_bitacora(
            accion="ACTUALIZAR_BASE",
            modelo="BaseDiariaCuenta",
            objeto_id=base.pk,
            datos_anteriores=datos_anteriores,
            datos_nuevos={
                "base_inicial": str(base.base_inicial),
                "observacion": base.observacion,
            },
            usuario=usuario,
        )
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
        entradas, salidas = _aggregate_movimientos_activos(jornada=jornada, cuenta=cuenta)
        if not cuenta.requiere_base_inicial:
            saldo_actual = entradas - salidas
            return {
                "jornada": jornada,
                "cuenta": cuenta,
                "base_inicial": None,
                "entradas": entradas,
                "salidas": salidas,
                "saldo_actual": saldo_actual,
                "tiene_base": True,
                "requiere_base_inicial": False,
            }
        return {
            "jornada": jornada,
            "cuenta": cuenta,
            "base_inicial": None,
            "entradas": entradas,
            "salidas": salidas,
            "saldo_actual": entradas - salidas,
            "tiene_base": False,
            "requiere_base_inicial": True,
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
        "requiere_base_inicial": True,
    }


def _agregar_totales_generales(jornada):
    movimientos = MovimientoCuenta.objects.filter(jornada=jornada, estado=MovimientoCuenta.ESTADO_ACTIVO)
    resumen = movimientos.aggregate(
        entradas_efectivo=Coalesce(Sum("entrada_efectivo"), ZERO),
        salidas_efectivo=Coalesce(Sum("salida_efectivo"), ZERO),
        bancolombia=Coalesce(Sum("bancolombia"), ZERO),
        nequi=Coalesce(Sum("nequi"), ZERO),
        daviplata=Coalesce(Sum("daviplata"), ZERO),
        nubank=Coalesce(Sum("nubank"), ZERO),
        datofono=Coalesce(Sum("datofono"), ZERO),
        sistecredito_addi=Coalesce(Sum("sistecredito_addi"), ZERO),
        ingreso_caja_fuerte=Coalesce(Sum("ingreso_caja_fuerte"), ZERO),
        retiro_caja_fuerte=Coalesce(Sum("retiro_caja_fuerte"), ZERO),
        tarjeta_credito_compras=Coalesce(Sum("tarjeta_credito_compras"), ZERO),
        valor_total=Coalesce(Sum("valor_total"), ZERO),
        valor_neto=Coalesce(Sum("valor_neto"), ZERO),
        descuento=Coalesce(Sum("descuento"), ZERO),
        total_movimientos=models.Count("id"),
        pendientes_validacion=models.Count(
            "id",
            filter=models.Q(estado=MovimientoCuenta.ESTADO_PENDIENTE_VALIDACION),
        ),
    )
    total_transferencias = (
        resumen["bancolombia"]
        + resumen["nequi"]
        + resumen["daviplata"]
        + resumen["nubank"]
    )
    total_datofono = resumen["datofono"]
    total_financiacion = resumen["sistecredito_addi"]
    total_ingresos = (
        resumen["entradas_efectivo"]
        + resumen["bancolombia"]
        + resumen["nequi"]
        + resumen["daviplata"]
        + resumen["nubank"]
        + resumen["datofono"]
        + resumen["sistecredito_addi"]
    )
    total_egresos = (
        resumen["salidas_efectivo"]
        + resumen["tarjeta_credito_compras"]
        + resumen["retiro_caja_fuerte"]
    )
    caja_esperada = (
        jornada.base_inicial_caja
        + resumen["entradas_efectivo"]
        - resumen["salidas_efectivo"]
        - resumen["ingreso_caja_fuerte"]
        + resumen["retiro_caja_fuerte"]
    )
    caja_fuerte_esperada = (
        jornada.base_inicial_caja_fuerte
        + resumen["ingreso_caja_fuerte"]
        - resumen["retiro_caja_fuerte"]
    )
    return {
        "entradas_efectivo": resumen["entradas_efectivo"],
        "salidas_efectivo": resumen["salidas_efectivo"],
        "total_transferencias": total_transferencias,
        "total_datofono": total_datofono,
        "total_financiacion": total_financiacion,
        "total_ingresos": total_ingresos,
        "total_egresos": total_egresos,
        "caja_esperada": caja_esperada,
        "caja_fuerte_esperada": caja_fuerte_esperada,
        "diferencia_caja": None if jornada.efectivo_contado_real is None else (jornada.efectivo_contado_real - caja_esperada),
        "diferencia_caja_fuerte": None if jornada.caja_fuerte_contada_real is None else (jornada.caja_fuerte_contada_real - caja_fuerte_esperada),
        "diferencia_transferencias": None if jornada.transferencias_verificadas is None else (jornada.transferencias_verificadas - total_transferencias),
        "diferencia_datofono": None if jornada.datofono_verificado is None else (jornada.datofono_verificado - total_datofono),
        "diferencia_financiacion": None if jornada.financiacion_verificada is None else (jornada.financiacion_verificada - total_financiacion),
        "valor_total": resumen["valor_total"],
        "valor_neto": resumen["valor_neto"],
        "descuento": resumen["descuento"],
        "total_movimientos": resumen["total_movimientos"],
        "pendientes_validacion": resumen["pendientes_validacion"],
    }


def resumen_jornada(*, fecha=None, incluir_inactivas=False):
    fecha = fecha or timezone.localdate()
    jornada, _ = obtener_o_crear_jornada(fecha=fecha)
    asegurar_cuentas_base()
    cuentas = CuentaFinanciera.objects.all()
    if not incluir_inactivas:
        cuentas = cuentas.filter(activa=True)
    resumen = [calcular_saldo_cuenta(cuenta=cuenta, fecha=fecha) for cuenta in cuentas.order_by("orden_visual", "nombre")]
    totales = _agregar_totales_generales(jornada)
    cuentas_obligatorias = [item for item in resumen if item["requiere_base_inicial"]]
    cuentas_abiertas = [item for item in cuentas_obligatorias if item["tiene_base"]]
    pendientes_base = [item for item in cuentas_obligatorias if not item["tiene_base"]]
    estado_derived = _jornada_estado_desde_bases(jornada=jornada)
    apertura_completa = estado_derived == JornadaDiaria.ESTADO_ABIERTO
    return {
        "jornada": jornada,
        "resumen": resumen,
        "totales": totales,
        "total_general": sum((item["saldo_actual"] for item in resumen), ZERO) if apertura_completa else None,
        "cuentas_obligatorias": cuentas_obligatorias,
        "cuentas_abiertas": cuentas_abiertas,
        "cuentas_pendientes_base": pendientes_base,
        "apertura_completa": apertura_completa,
        "apertura_incompleta": not apertura_completa,
        "bases_obligatorias_totales": len(cuentas_obligatorias),
        "bases_obligatorias_cargadas": len(cuentas_abiertas),
        "nombres_bases_pendientes": [item["cuenta"].nombre for item in pendientes_base],
        "estado_jornada_derived": estado_derived,
    }


def obtener_destacados_dashboard(*, fecha=None):
    fecha = fecha or timezone.localdate()
    resumen_data = resumen_jornada(fecha=fecha)
    jornada = resumen_data["jornada"]
    resumen = resumen_data["resumen"]
    totales = resumen_data["totales"]

    def _find_by_codigo(codigo):
        for item in resumen:
            if getattr(item["cuenta"], "codigo", "") == codigo:
                return item
        return None

    caja = _find_by_codigo("CAJA_PRINCIPAL")
    caja_fuerte = _find_by_codigo("CAJA_FUERTE")
    banco_principal = _find_by_codigo("BANCOLOMBIA")
    cuentas_obligatorias = [item for item in resumen if item["requiere_base_inicial"]]
    cuentas_banco_like = [
        item for item in cuentas_obligatorias
        if item["cuenta"].categoria_operativa in {CuentaFinanciera.CATEGORIA_BANCO, CuentaFinanciera.CATEGORIA_BILLETERA}
    ]
    pendientes_base = sum(1 for item in cuentas_obligatorias if not item["tiene_base"])
    cuentas_abiertas = sum(1 for item in cuentas_obligatorias if item["tiene_base"])
    bancos_pendientes = [item for item in cuentas_banco_like if not item["tiene_base"]]
    apertura_completa = resumen_data["apertura_completa"]
    estado_jornada = resumen_data["estado_jornada_derived"]
    total_disponible = resumen_data["total_general"] if apertura_completa else None
    caja_esperada = totales["caja_esperada"] if apertura_completa else None
    caja_fuerte_esperada = totales["caja_fuerte_esperada"] if apertura_completa else None

    return {
        "caja_principal": caja,
        "banco_principal": banco_principal,
        "caja_fuerte": caja_fuerte,
        "total_disponible": total_disponible,
        "cuentas_pendientes_base": pendientes_base,
        "cuentas_abiertas_hoy": cuentas_abiertas,
        "total_cuentas_activas": len(cuentas_obligatorias),
        "total_cuentas_mostradas": len(resumen),
        "bancos_totales": len(cuentas_banco_like),
        "bancos_cargados": len(cuentas_banco_like) - len(bancos_pendientes),
        "nombres_bancos_pendientes": [item["cuenta"].nombre for item in bancos_pendientes],
        "total_entradas_efectivo": totales["entradas_efectivo"],
        "total_salidas_efectivo": totales["salidas_efectivo"],
        "total_transferencias": totales["total_transferencias"],
        "total_datofono": totales["total_datofono"],
        "total_financiacion": totales["total_financiacion"],
        "total_ingresos": totales["total_ingresos"],
        "total_egresos": totales["total_egresos"],
        "caja_esperada": caja_esperada,
        "caja_fuerte_esperada": caja_fuerte_esperada,
        "diferencia_caja": totales["diferencia_caja"],
        "diferencia_caja_fuerte": totales["diferencia_caja_fuerte"],
        "pendientes_validacion": totales["pendientes_validacion"],
        "estado_jornada": estado_jornada,
        "estado_jornada_display": "Apertura incompleta" if estado_jornada == JornadaDiaria.ESTADO_APERTURA_INCOMPLETA else jornada.get_estado_display(),
        "apertura_completa": apertura_completa,
    }


def listar_movimientos(
    *,
    fecha=None,
    cuenta_id=None,
    tipo=None,
    clase=None,
    tipo_movimiento=None,
    usuario_id=None,
    estado=None,
    profesional=None,
    cliente=None,
    medio_pago=None,
    q=None,
    solo_relevantes=False,
    solo_correcciones=False,
):
    fecha = fecha or timezone.localdate()
    jornada, _ = obtener_o_crear_jornada(fecha=fecha)
    qs = (
        MovimientoCuenta.objects
        .filter(jornada=jornada)
        .select_related("cuenta", "usuario", "movimiento_origen", "compra", "servicio", "colaborador", "usuario_validacion")
        .order_by("-fecha_hora", "-id")
    )

    if cuenta_id:
        qs = qs.filter(cuenta_id=cuenta_id)
    if tipo:
        qs = qs.filter(tipo=tipo)
    if clase:
        qs = qs.filter(clase=clase)
    if tipo_movimiento:
        qs = qs.filter(tipo_movimiento=tipo_movimiento)
    if usuario_id:
        qs = qs.filter(usuario_id=usuario_id)
    if estado:
        qs = qs.filter(estado=estado)
    if profesional:
        qs = qs.filter(profesional__icontains=profesional)
    if cliente:
        qs = qs.filter(cliente__icontains=cliente)
    if medio_pago:
        medio_pago = medio_pago.strip().upper()
        medio_pago_map = {
            "BANCOLOMBIA": "bancolombia__gt",
            "NEQUI": "nequi__gt",
            "DAVIPLATA": "daviplata__gt",
            "NUBANK": "nubank__gt",
            "DATAFONO": "datofono__gt",
            "SISTECREDITO_ADDI": "sistecredito_addi__gt",
        }
        if medio_pago in medio_pago_map:
            qs = qs.filter(**{medio_pago_map[medio_pago]: 0})
    if q:
        q = q.strip()
        if q:
            qs = qs.filter(
                models.Q(procedimiento__icontains=q)
                | models.Q(producto_servicio__icontains=q)
                | models.Q(concepto__icontains=q)
                | models.Q(referencia__icontains=q)
                | models.Q(comprobante__icontains=q)
                | models.Q(observacion__icontains=q)
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
        total_movimientos=models.Count("id"),
        reversas_anulaciones=models.Count(
            "id",
            filter=models.Q(
                clase__in=[MovimientoCuenta.CLASE_REVERSA, MovimientoCuenta.CLASE_ANULACION]
            ),
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


def _asegurar_jornada_abierta(*, jornada):
    if _jornada_estado_desde_bases(jornada=jornada) == JornadaDiaria.ESTADO_APERTURA_INCOMPLETA:
        raise ControlFondosError("Completa la apertura antes de registrar movimientos.")
    if jornada.estado not in {
        JornadaDiaria.ESTADO_ABIERTO,
        JornadaDiaria.ESTADO_REABIERTO,
        JornadaDiaria.ESTADO_EN_REVISION,
    }:
        raise ControlFondosError("La jornada no está abierta para registrar movimientos.")


def _preparar_movimiento_kwargs(**kwargs):
    tipo_movimiento = kwargs.pop("tipo_movimiento", "")
    valor_total = _decimal(kwargs.pop("valor_total", kwargs.get("valor", 0)))
    descuento = _decimal(kwargs.pop("descuento", 0))
    valor_neto = kwargs.pop("valor_neto", None)
    if valor_neto is None:
        valor_neto = valor_total - descuento if valor_total else _decimal(kwargs.get("valor", 0))
    valor_neto = _decimal(valor_neto)
    if not valor_total:
        valor_total = valor_neto
    kwargs["tipo_movimiento"] = tipo_movimiento
    kwargs["valor_total"] = valor_total
    kwargs["descuento"] = descuento
    kwargs["valor_neto"] = valor_neto
    kwargs["valor"] = _decimal(kwargs.get("valor", valor_neto))
    return kwargs


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
    tipo_movimiento="",
    valor_total=None,
    descuento=0,
    valor_neto=None,
    procedimiento="",
    producto_servicio="",
    profesional="",
    cliente="",
    entrada_efectivo=0,
    salida_efectivo=0,
    bancolombia=0,
    nequi=0,
    daviplata=0,
    nubank=0,
    datofono=0,
    sistecredito_addi=0,
    ingreso_caja_fuerte=0,
    retiro_caja_fuerte=0,
    tarjeta_credito_compras=0,
    motivo_salida="",
    comprobante="",
    soporte_adjunto=None,
    observacion="",
    estado=None,
    estado_validacion=None,
):
    request_uid = _normalize_request_uid(request_uid)
    if request_uid:
        existing = MovimientoCuenta.objects.filter(request_uid=request_uid).first()
        if existing:
            return existing, False

    fecha = fecha or timezone.localdate()
    valor = _decimal(valor)
    if valor <= 0:
        raise ControlFondosError("El valor del movimiento debe ser mayor que cero.")
    if not getattr(cuenta, "permite_entradas", True) and tipo == MovimientoCuenta.TIPO_ENTRADA:
        raise ControlFondosError(f"La cuenta {cuenta.nombre} no permite entradas.")
    if not getattr(cuenta, "permite_salidas", True) and tipo == MovimientoCuenta.TIPO_SALIDA:
        raise ControlFondosError(f"La cuenta {cuenta.nombre} no permite salidas.")
    if getattr(cuenta, "requiere_referencia", False) and not (referencia or "").strip():
        raise ControlFondosError(f"La cuenta {cuenta.nombre} requiere referencia.")

    fecha = fecha or timezone.localdate()
    with transaction.atomic():
        jornada, _ = obtener_o_crear_jornada(fecha=fecha, usuario=usuario)
        _asegurar_jornada_abierta(jornada=jornada)
        base = obtener_base_diaria(cuenta=cuenta, fecha=fecha, lock=True)
        if base and base.jornada_id != jornada.pk:
            raise ControlFondosError("La base del día no coincide con la jornada activa de la cuenta.")

        if request_uid:
            existing = MovimientoCuenta.objects.select_for_update().filter(request_uid=request_uid).first()
            if existing:
                return existing, False

        kwargs = _preparar_movimiento_kwargs(
            valor=valor,
            tipo_movimiento=tipo_movimiento,
            valor_total=valor_total if valor_total is not None else valor,
            descuento=descuento,
            valor_neto=valor_neto if valor_neto is not None else valor,
        )
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
            procedimiento=procedimiento or "",
            producto_servicio=producto_servicio or "",
            profesional=profesional or "",
            cliente=cliente or "",
            entrada_efectivo=_decimal(entrada_efectivo),
            salida_efectivo=_decimal(salida_efectivo),
            bancolombia=_decimal(bancolombia),
            nequi=_decimal(nequi),
            daviplata=_decimal(daviplata),
            nubank=_decimal(nubank),
            datofono=_decimal(datofono),
            sistecredito_addi=_decimal(sistecredito_addi),
            ingreso_caja_fuerte=_decimal(ingreso_caja_fuerte),
            retiro_caja_fuerte=_decimal(retiro_caja_fuerte),
            tarjeta_credito_compras=_decimal(tarjeta_credito_compras),
            motivo_salida=motivo_salida or "",
            comprobante=comprobante or "",
            observacion=observacion or "",
            soporte_adjunto=soporte_adjunto,
            estado=estado or MovimientoCuenta.ESTADO_ACTIVO,
            estado_validacion=estado_validacion or MovimientoCuenta.ESTADO_PENDIENTE_VALIDACION,
            valor_total=kwargs["valor_total"],
            descuento=kwargs["descuento"],
            valor_neto=kwargs["valor_neto"],
            tipo_movimiento=kwargs["tipo_movimiento"],
        )
        _registrar_bitacora(
            accion="CREAR_MOVIMIENTO",
            modelo="MovimientoCuenta",
            objeto_id=movimiento.pk,
            datos_nuevos={
                "cuenta": cuenta.nombre,
                "tipo": tipo,
                "clase": clase,
                "valor": str(valor),
                "tipo_movimiento": movimiento.tipo_movimiento,
            },
            usuario=usuario,
        )
        return movimiento, True


def registrar_movimiento_controlado(*, cuenta, tipo_movimiento, valor_total, usuario=None, fecha=None, request_uid=None, **kwargs):
    tipo = MovimientoCuenta.TIPO_ENTRADA if tipo_movimiento == MovimientoCuenta.TIPO_MOVIMIENTO_INGRESO else MovimientoCuenta.TIPO_SALIDA
    clase = {
        MovimientoCuenta.TIPO_MOVIMIENTO_INGRESO: MovimientoCuenta.CLASE_SERVICIO,
        MovimientoCuenta.TIPO_MOVIMIENTO_SALIDA: MovimientoCuenta.CLASE_COMPRA,
        MovimientoCuenta.TIPO_MOVIMIENTO_TRANSFERENCIA: MovimientoCuenta.CLASE_TRANSFERENCIA,
        MovimientoCuenta.TIPO_MOVIMIENTO_AJUSTE: MovimientoCuenta.CLASE_AJUSTE,
        MovimientoCuenta.TIPO_MOVIMIENTO_ANULACION: MovimientoCuenta.CLASE_ANULACION,
        MovimientoCuenta.TIPO_MOVIMIENTO_COMPRA_TARJETA: MovimientoCuenta.CLASE_COMPRA,
    }.get(tipo_movimiento, MovimientoCuenta.CLASE_AJUSTE)
    return crear_movimiento(
        cuenta=cuenta,
        tipo=tipo,
        clase=clase,
        valor=valor_total,
        concepto=kwargs.get("observacion") or kwargs.get("procedimiento") or "Movimiento controlado",
        usuario=usuario,
        fecha=fecha,
        referencia=kwargs.get("referencia", ""),
        compra=kwargs.get("compra"),
        servicio=kwargs.get("servicio"),
        colaborador=kwargs.get("colaborador"),
        request_uid=request_uid,
        tipo_movimiento=tipo_movimiento,
        valor_total=valor_total,
        descuento=kwargs.get("descuento", 0),
        valor_neto=kwargs.get("valor_neto", valor_total),
        procedimiento=kwargs.get("procedimiento", ""),
        producto_servicio=kwargs.get("producto_servicio", ""),
        profesional=kwargs.get("profesional", ""),
        cliente=kwargs.get("cliente", ""),
        entrada_efectivo=kwargs.get("entrada_efectivo", 0),
        salida_efectivo=kwargs.get("salida_efectivo", 0),
        bancolombia=kwargs.get("bancolombia", 0),
        nequi=kwargs.get("nequi", 0),
        daviplata=kwargs.get("daviplata", 0),
        nubank=kwargs.get("nubank", 0),
        datofono=kwargs.get("datofono", 0),
        sistecredito_addi=kwargs.get("sistecredito_addi", 0),
        ingreso_caja_fuerte=kwargs.get("ingreso_caja_fuerte", 0),
        retiro_caja_fuerte=kwargs.get("retiro_caja_fuerte", 0),
        tarjeta_credito_compras=kwargs.get("tarjeta_credito_compras", 0),
        motivo_salida=kwargs.get("motivo_salida", ""),
        comprobante=kwargs.get("comprobante", ""),
        soporte_adjunto=kwargs.get("soporte_adjunto"),
        observacion=kwargs.get("observacion", ""),
    )


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
            tipo_movimiento=MovimientoCuenta.TIPO_MOVIMIENTO_ANULACION,
            valor=movimiento.valor,
            valor_total=movimiento.valor_total,
            descuento=movimiento.descuento,
            valor_neto=movimiento.valor_neto,
            procedimiento=movimiento.procedimiento,
            producto_servicio=movimiento.producto_servicio,
            profesional=movimiento.profesional,
            cliente=movimiento.cliente,
            entrada_efectivo=movimiento.salida_efectivo,
            salida_efectivo=movimiento.entrada_efectivo,
            bancolombia=movimiento.bancolombia,
            nequi=movimiento.nequi,
            daviplata=movimiento.daviplata,
            nubank=movimiento.nubank,
            datofono=movimiento.datofono,
            sistecredito_addi=movimiento.sistecredito_addi,
            ingreso_caja_fuerte=movimiento.ingreso_caja_fuerte,
            retiro_caja_fuerte=movimiento.retiro_caja_fuerte,
            tarjeta_credito_compras=movimiento.tarjeta_credito_compras,
            motivo_salida=movimiento.motivo_salida,
            concepto=concepto or f"Reversa de movimiento #{movimiento.pk}",
            referencia=movimiento.referencia,
            comprobante=movimiento.comprobante,
            observacion=movimiento.observacion,
            usuario=usuario,
            movimiento_origen=movimiento,
            compra=movimiento.compra,
            servicio=movimiento.servicio,
            colaborador=movimiento.colaborador,
            request_uid=request_uid,
            estado=MovimientoCuenta.ESTADO_ACTIVO,
            estado_validacion=MovimientoCuenta.ESTADO_PENDIENTE_VALIDACION,
        )
        movimiento.estado = MovimientoCuenta.ESTADO_ANULADO
        movimiento.estado_validacion = MovimientoCuenta.ESTADO_RECHAZADO
        movimiento.save(update_fields=["estado", "estado_validacion"])
        _registrar_bitacora(
            accion="REVERSAR_MOVIMIENTO",
            modelo="MovimientoCuenta",
            objeto_id=movimiento.pk,
            datos_anteriores={"estado": MovimientoCuenta.ESTADO_ACTIVO},
            datos_nuevos={"estado": MovimientoCuenta.ESTADO_ANULADO, "reversa": reversa.pk},
            usuario=usuario,
        )
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
        tipo_movimiento=MovimientoCuenta.TIPO_MOVIMIENTO_SALIDA,
        valor_total=compra.precio_total,
        valor_neto=compra.precio_total,
        salida_efectivo=compra.precio_total,
        motivo_salida="COMPRA_DE_INSUMOS",
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
    valor = _decimal(valor if valor is not None else (servicio.precio_alisado or 0) - (servicio.saldo_pendiente or 0))
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
        tipo_movimiento=MovimientoCuenta.TIPO_MOVIMIENTO_INGRESO,
        valor_total=valor,
        valor_neto=valor,
        entrada_efectivo=valor,
    )


def registrar_transferencia(*, cuenta_origen, cuenta_destino, valor, usuario=None, fecha=None, request_uid=None, observacion="", referencia="", comprobante="", soporte_adjunto=None):
    if cuenta_origen.pk == cuenta_destino.pk:
        raise ControlFondosError("La cuenta origen y la cuenta destino deben ser distintas.")
    observacion = (observacion or "").strip()
    referencia = (referencia or "").strip()
    comprobante = (comprobante or "").strip()
    with transaction.atomic():
        salida, _ = crear_movimiento(
            cuenta=cuenta_origen,
            tipo=MovimientoCuenta.TIPO_SALIDA,
            clase=MovimientoCuenta.CLASE_TRANSFERENCIA,
            valor=valor,
            concepto=f"Transferencia hacia {cuenta_destino.nombre}" + (f" | {observacion}" if observacion else ""),
            usuario=usuario,
            fecha=fecha,
            referencia=referencia or f"TRANSFER-{cuenta_origen.pk}-{cuenta_destino.pk}",
            request_uid=_request_uid_with_suffix(request_uid, "salida"),
            tipo_movimiento=MovimientoCuenta.TIPO_MOVIMIENTO_TRANSFERENCIA,
            valor_total=valor,
            valor_neto=valor,
            comprobante=comprobante,
            soporte_adjunto=soporte_adjunto,
            observacion=observacion,
        )
        entrada, _ = crear_movimiento(
            cuenta=cuenta_destino,
            tipo=MovimientoCuenta.TIPO_ENTRADA,
            clase=MovimientoCuenta.CLASE_TRANSFERENCIA,
            valor=valor,
            concepto=f"Transferencia desde {cuenta_origen.nombre}" + (f" | {observacion}" if observacion else ""),
            usuario=usuario,
            fecha=fecha,
            referencia=referencia or f"TRANSFER-{cuenta_origen.pk}-{cuenta_destino.pk}",
            request_uid=_request_uid_with_suffix(request_uid, "entrada"),
            tipo_movimiento=MovimientoCuenta.TIPO_MOVIMIENTO_TRANSFERENCIA,
            valor_total=valor,
            valor_neto=valor,
            comprobante=comprobante,
            soporte_adjunto=soporte_adjunto,
            observacion=observacion,
        )
        transferencia = TransferenciaCuenta.objects.filter(
            movimiento_salida=salida,
            movimiento_entrada=entrada,
        ).first()
        if transferencia:
            return transferencia
        transferencia = TransferenciaCuenta.objects.create(
            cuenta_origen=cuenta_origen,
            cuenta_destino=cuenta_destino,
            valor=_decimal(valor),
            referencia=referencia or f"TRANSFER-{cuenta_origen.pk}-{cuenta_destino.pk}",
            comprobante=comprobante,
            soporte_adjunto=soporte_adjunto,
            observacion=observacion,
            movimiento_salida=salida,
            movimiento_entrada=entrada,
            usuario=usuario,
        )
        _registrar_bitacora(
            accion="REGISTRAR_TRANSFERENCIA",
            modelo="TransferenciaCuenta",
            objeto_id=transferencia.pk,
            datos_nuevos={
                "origen": cuenta_origen.nombre,
                "destino": cuenta_destino.nombre,
                "valor": str(valor),
            },
            usuario=usuario,
        )
        return transferencia


def registrar_cierre_jornada(
    *,
    fecha=None,
    efectivo_contado_real,
    caja_fuerte_contada_real,
    transferencias_verificadas=None,
    datofono_verificado=None,
    financiacion_verificada=None,
    observacion_cierre="",
    usuario=None,
    autorizacion_supervisor=False,
):
    fecha = fecha or timezone.localdate()
    with transaction.atomic():
        jornada, _ = obtener_o_crear_jornada(fecha=fecha, usuario=usuario)
        resumen = _agregar_totales_generales(jornada)
        cuentas_obligatorias = CuentaFinanciera.objects.filter(activa=True, requiere_base_inicial=True)
        bases_registradas = BaseDiariaCuenta.objects.filter(jornada=jornada).values_list("cuenta_id", flat=True)
        faltantes = cuentas_obligatorias.exclude(id__in=bases_registradas).count()
        pendientes = MovimientoCuenta.objects.filter(
            jornada=jornada,
            estado=MovimientoCuenta.ESTADO_PENDIENTE_VALIDACION,
        ).count()
        if pendientes:
            raise ControlFondosError("No puedes cerrar la jornada con movimientos pendientes de validación.")
        if faltantes:
            raise ControlFondosError("No puedes cerrar la jornada mientras existan cuentas obligatorias sin base inicial.")

        jornada.estado = JornadaDiaria.ESTADO_EN_REVISION
        jornada.efectivo_contado_real = _decimal(efectivo_contado_real)
        jornada.caja_fuerte_contada_real = _decimal(caja_fuerte_contada_real)
        jornada.transferencias_verificadas = _decimal(transferencias_verificadas or resumen["total_transferencias"])
        jornada.datofono_verificado = _decimal(datofono_verificado or resumen["total_datofono"])
        jornada.financiacion_verificada = _decimal(financiacion_verificada or resumen["total_financiacion"])
        jornada.observacion_cierre = observacion_cierre or ""
        jornada.diferencia_caja = jornada.efectivo_contado_real - resumen["caja_esperada"]
        jornada.diferencia_caja_fuerte = jornada.caja_fuerte_contada_real - resumen["caja_fuerte_esperada"]
        jornada.diferencia_transferencias = jornada.transferencias_verificadas - resumen["total_transferencias"]
        jornada.diferencia_datofono = jornada.datofono_verificado - resumen["total_datofono"]
        jornada.diferencia_financiacion = jornada.financiacion_verificada - resumen["total_financiacion"]
        jornada.usuario_cierre = usuario
        jornada.fecha_cierre = timezone.now()
        if any(
            value != ZERO
            for value in [
                jornada.diferencia_caja,
                jornada.diferencia_caja_fuerte,
                jornada.diferencia_transferencias,
                jornada.diferencia_datofono,
                jornada.diferencia_financiacion,
            ]
        ) and not autorizacion_supervisor:
            raise ControlFondosError("Hay diferencias de cierre y se requiere autorización de supervisor.")
        if any(
            value != ZERO
            for value in [
                jornada.diferencia_caja,
                jornada.diferencia_caja_fuerte,
                jornada.diferencia_transferencias,
                jornada.diferencia_datofono,
                jornada.diferencia_financiacion,
            ]
        ):
            jornada.autorizado_por = usuario
        jornada.estado = JornadaDiaria.ESTADO_CERRADO
        jornada.save(
            update_fields=[
                "estado",
                "efectivo_contado_real",
                "caja_fuerte_contada_real",
                "transferencias_verificadas",
                "datofono_verificado",
                "financiacion_verificada",
                "observacion_cierre",
                "diferencia_caja",
                "diferencia_caja_fuerte",
                "diferencia_transferencias",
                "diferencia_datofono",
                "diferencia_financiacion",
                "usuario_cierre",
                "fecha_cierre",
                "autorizado_por",
            ]
        )
        _registrar_bitacora(
            accion="CERRAR_JORNADA",
            modelo="JornadaDiaria",
            objeto_id=jornada.pk,
            datos_nuevos={
                "estado": jornada.estado,
                "diferencia_caja": str(jornada.diferencia_caja),
                "diferencia_caja_fuerte": str(jornada.diferencia_caja_fuerte),
            },
            usuario=usuario,
        )
        return jornada


def reabrir_jornada(*, fecha=None, usuario=None, motivo=""):
    fecha = fecha or timezone.localdate()
    with transaction.atomic():
        jornada, _ = obtener_o_crear_jornada(fecha=fecha, usuario=usuario)
        if jornada.estado not in {JornadaDiaria.ESTADO_CERRADO, JornadaDiaria.ESTADO_CERRADA_AUTO}:
            raise ControlFondosError("Solo puedes reabrir una jornada cerrada.")
        jornada.estado = JornadaDiaria.ESTADO_REABIERTO
        jornada.fecha_reapertura = timezone.now()
        jornada.motivo_reapertura = motivo or ""
        jornada.autorizado_por = usuario
        jornada.save(update_fields=["estado", "fecha_reapertura", "motivo_reapertura", "autorizado_por"])
        _registrar_bitacora(
            accion="REABRIR_JORNADA",
            modelo="JornadaDiaria",
            objeto_id=jornada.pk,
            datos_nuevos={"estado": jornada.estado, "motivo": motivo or ""},
            usuario=usuario,
        )
        return jornada
