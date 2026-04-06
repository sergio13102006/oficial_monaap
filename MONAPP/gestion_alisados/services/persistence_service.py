from django.utils import timezone

from servicios.models import Servicio

from ..models import GestionAlisado
from .realtime_notifications import notify_back_to_waiting, notify_signature_completed


def get_valid_alisado_service_name(nombre_servicio):
    nombre = (nombre_servicio or "").strip()
    if not nombre:
        return ""
    if Servicio.objects.filter(nombre__iexact=nombre, activo=True).exists():
        return nombre
    return ""


def get_last_gestion_values(cliente_obj):
    if not cliente_obj:
        return {}

    ultima = GestionAlisado.objects.filter(cliente=cliente_obj).order_by("-fecha_hora").first()
    if not ultima:
        return {"cliente": cliente_obj}

    return {
        "cliente": cliente_obj,
        "precio_alisado": ultima.precio_alisado,
        "es_oferta_especial": ultima.es_oferta_especial,
        "descripcion_oferta": ultima.descripcion_oferta or "",
        "anticipo_cliente": ultima.anticipo_cliente,
        "medio_pago": ultima.medio_pago,
        "saldo_pendiente": ultima.saldo_pendiente,
        "procedimiento_realizado_por": ultima.procedimiento_realizado_por,
        "tipo_alisado": get_valid_alisado_service_name(ultima.tipo_alisado),
        "requiere_resellado": ultima.requiere_resellado,
        "porcentaje_alisado": ultima.porcentaje_alisado,
        "porosidad": ultima.porosidad,
        "textura": ultima.textura,
        "forma_natural": ultima.forma_natural,
        "elasticidad": ultima.elasticidad,
        "longitud": ultima.longitud,
        "densidad": ultima.densidad,
        "piel_cabelludo": ultima.piel_cabelludo,
        "alopecia": ultima.alopecia,
        "caida_cabello": ultima.caida_cabello,
        "lactante": ultima.lactante,
        "gestante": ultima.gestante,
        "caspa": ultima.caspa,
        "procesos_tintura": ultima.procesos_tintura,
        "procesos_decoloracion": ultima.procesos_decoloracion,
        "procesos_ondulados": ultima.procesos_ondulados,
        "procesos_extracciones": ultima.procesos_extracciones,
        "procesos_alisados": ultima.procesos_alisados,
        "procesos_super_aclarante": ultima.procesos_super_aclarante,
        "procesos_otro": ultima.procesos_otro or "",
        "cuenta_con_secador": ultima.cuenta_con_secador,
        "frecuencia_recoge_cabello": ultima.frecuencia_recoge_cabello,
        "realiza_ejercicio": ultima.realiza_ejercicio,
        "frecuencia_ejercicio": ultima.frecuencia_ejercicio or "",
        "usa_casco": ultima.usa_casco,
        "productos_capilares": ultima.productos_capilares,
        "se_bana_agua_caliente": ultima.se_bana_agua_caliente,
        "requiere_refuerzo_15dias": ultima.requiere_refuerzo_15dias,
        "sufre_tiroides": ultima.sufre_tiroides,
        "medicamento_tiroides": ultima.medicamento_tiroides or "",
        "despunte_hoy": ultima.despunte_hoy,
        "recomendaciones_post_cuidados": ultima.recomendaciones_post_cuidados,
    }


def get_last_gestion_payload(cliente_obj):
    if not cliente_obj:
        return {}

    ultima = GestionAlisado.objects.filter(cliente=cliente_obj).order_by("-fecha_hora").first()
    if not ultima:
        return {}

    return {
        "cliente": str(cliente_obj.pk),
        "cliente_nombre": f"{cliente_obj.nombre} {cliente_obj.apellido}",
        "cliente_documento": cliente_obj.numero_documento,
        "precio_alisado": ultima.precio_alisado,
        "es_oferta_especial": ultima.es_oferta_especial,
        "descripcion_oferta": ultima.descripcion_oferta or "",
        "anticipo_cliente": ultima.anticipo_cliente,
        "medio_pago": ultima.medio_pago,
        "saldo_pendiente": ultima.saldo_pendiente,
        "procedimiento_realizado_por": ultima.procedimiento_realizado_por,
        "tipo_alisado": get_valid_alisado_service_name(ultima.tipo_alisado),
        "requiere_resellado": ultima.requiere_resellado,
        "porcentaje_alisado": ultima.porcentaje_alisado,
        "porosidad": ultima.porosidad,
        "textura": ultima.textura,
        "forma_natural": ultima.forma_natural,
        "elasticidad": ultima.elasticidad,
        "longitud": ultima.longitud,
        "densidad": ultima.densidad,
        "piel_cabelludo": ultima.piel_cabelludo,
        "alopecia": ultima.alopecia,
        "caida_cabello": ultima.caida_cabello,
        "lactante": ultima.lactante,
        "gestante": ultima.gestante,
        "caspa": ultima.caspa,
        "procesos_tintura": ultima.procesos_tintura,
        "procesos_decoloracion": ultima.procesos_decoloracion,
        "procesos_ondulados": ultima.procesos_ondulados,
        "procesos_extracciones": ultima.procesos_extracciones,
        "procesos_alisados": ultima.procesos_alisados,
        "procesos_super_aclarante": ultima.procesos_super_aclarante,
        "procesos_otro": ultima.procesos_otro or "",
        "cuenta_con_secador": ultima.cuenta_con_secador,
        "frecuencia_recoge_cabello": ultima.frecuencia_recoge_cabello,
        "realiza_ejercicio": ultima.realiza_ejercicio,
        "frecuencia_ejercicio": ultima.frecuencia_ejercicio or "",
        "usa_casco": ultima.usa_casco,
        "productos_capilares": ultima.productos_capilares,
        "se_bana_agua_caliente": ultima.se_bana_agua_caliente,
        "requiere_refuerzo_15dias": ultima.requiere_refuerzo_15dias,
        "sufre_tiroides": ultima.sufre_tiroides,
        "medicamento_tiroides": ultima.medicamento_tiroides or "",
        "despunte_hoy": ultima.despunte_hoy,
        "recomendaciones_post_cuidados": ultima.recomendaciones_post_cuidados,
    }


def get_cliente_nombre_gestion(gestion_obj):
    cliente_obj = getattr(gestion_obj, "cliente", None)
    if not cliente_obj:
        return "Sin cliente"
    return f"{cliente_obj.nombre} {cliente_obj.apellido}"


def save_gestion_form(form):
    return form.save()


def complete_tablet_capture(form, token_obj):
    gestion = save_gestion_form(form)
    firmado_en = timezone.now()
    token_obj.gestion = gestion
    token_obj.save(update_fields=["gestion"])
    token_obj.marcar_estado(
        token_obj.ESTADO_FIRMADA,
        activo=False,
        detalle='Consentimiento firmado correctamente.',
        usado_en=firmado_en,
    )
    notify_signature_completed(
        'default-tablet',
        str(token_obj.token),
        payload={"gestion_id": str(gestion.pk), "signed_at": firmado_en.isoformat()},
    )
    notify_back_to_waiting(
        'default-tablet',
        session_id=str(token_obj.token),
        payload={"gestion_id": str(gestion.pk)},
    )
    return gestion
