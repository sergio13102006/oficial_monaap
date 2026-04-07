import hashlib
import json

from django.utils import timezone

from servicios.models import Servicio

from ..models import AtencionServicio, GestionAlisado, TratamientoDatosFirmado
from .realtime_notifications import notify_back_to_waiting, notify_signature_completed


TRATAMIENTO_DATOS_TEXTO_VIGENTE = """
Consentimiento informado del tratamiento de alisado. El cliente declara haber leido y comprendido
las recomendaciones, advertencias, cuidados, compromisos del tratamiento y terminos de aceptacion
mostrados en pantalla al momento de la firma. El soporte firmado corresponde a esa atencion puntual
y conserva una copia historica de los datos del cliente vigentes al momento del consentimiento.
""".strip()
TRATAMIENTO_DATOS_VERSION_VIGENTE = "v1"


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


def save_gestion_form(form, *, usuario=None, tablet_utilizada="", sede=""):
    gestion = form.save()
    if gestion.cliente:
        atencion = create_atencion_from_gestion(
            gestion,
            usuario=usuario,
            sede=sede,
            estado=AtencionServicio.ESTADO_COMPLETADA,
        )
        create_tratamiento_from_gestion(
            gestion,
            atencion=atencion,
            usuario_inicio=usuario,
            usuario_cierre=usuario,
            tablet_utilizada=tablet_utilizada,
            sede=sede,
            estado=TratamientoDatosFirmado.ESTADO_FIRMADA,
            firmado_en=timezone.now(),
        )
    return gestion


def build_cliente_snapshot(cliente_obj):
    if not cliente_obj:
        return {}

    return {
        "tipo_documento": cliente_obj.tipo_documento,
        "numero_documento": cliente_obj.numero_documento,
        "nombre": cliente_obj.nombre,
        "apellido": cliente_obj.apellido,
        "telefono": cliente_obj.telefono or "",
        "correo": cliente_obj.correo or "",
        "direccion": getattr(cliente_obj, "direccion", "") or "",
        "ciudad": getattr(cliente_obj, "ciudad", "") or "",
        "fecha_nacimiento": cliente_obj.fecha_nacimiento.isoformat() if cliente_obj.fecha_nacimiento else "",
        "observaciones_generales": getattr(cliente_obj, "observaciones_generales", "") or "",
    }


def build_tratamiento_integrity_hash(*, cliente_snapshot, texto_tratamiento, version_tratamiento, firmado_en, atencion_id):
    payload = {
        "atencion_id": str(atencion_id),
        "cliente_snapshot": cliente_snapshot,
        "firmado_en": firmado_en.isoformat() if firmado_en else "",
        "texto_tratamiento": texto_tratamiento,
        "version_tratamiento": version_tratamiento,
    }
    serialized = json.dumps(payload, sort_keys=True, ensure_ascii=True)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def create_atencion_from_gestion(gestion, *, usuario=None, sede="", estado=AtencionServicio.ESTADO_COMPLETADA):
    atencion = getattr(gestion, "atencion", None)
    if atencion:
        return atencion

    atencion = AtencionServicio.objects.create(
        cliente=gestion.cliente,
        fecha_atencion=gestion.fecha_hora,
        sede=sede or "",
        profesional_o_asesor=gestion.procedimiento_realizado_por,
        tipo_servicio=gestion.tipo_alisado,
        estado_atencion=estado,
        observaciones_atencion=gestion.recomendaciones_post_cuidados or "",
        usuario_registro=usuario,
        tratamiento_completado=False,
    )
    gestion.atencion = atencion
    gestion.save(update_fields=["atencion"])
    return atencion


def create_tratamiento_from_gestion(
    gestion,
    *,
    atencion,
    usuario_inicio=None,
    usuario_cierre=None,
    tablet_utilizada="default-tablet",
    sede="",
    estado=TratamientoDatosFirmado.ESTADO_FIRMADA,
    firmado_en=None,
):
    tratamiento = getattr(gestion, "tratamiento_firmado", None)
    if tratamiento:
        update_fields = []
        if usuario_inicio and tratamiento.usuario_inicio_proceso_id is None:
            tratamiento.usuario_inicio_proceso = usuario_inicio
            update_fields.append("usuario_inicio_proceso")
        if usuario_cierre and tratamiento.usuario_cierre_proceso_id is None:
            tratamiento.usuario_cierre_proceso = usuario_cierre
            update_fields.append("usuario_cierre_proceso")
        if tablet_utilizada and not tratamiento.tablet_utilizada:
            tratamiento.tablet_utilizada = tablet_utilizada
            update_fields.append("tablet_utilizada")
        if sede and not tratamiento.sede:
            tratamiento.sede = sede
            update_fields.append("sede")
        if estado == TratamientoDatosFirmado.ESTADO_FIRMADA and not tratamiento.fecha_hora_firma:
            tratamiento.fecha_hora_firma = firmado_en or timezone.now()
            tratamiento.estado = estado
            update_fields.extend(["fecha_hora_firma", "estado"])
        if update_fields:
            update_fields.append("actualizado_en")
            tratamiento.save(update_fields=update_fields)
        return tratamiento

    firmado_en = firmado_en or timezone.now()
    cliente_snapshot = build_cliente_snapshot(gestion.cliente)
    ruta_archivo_firma = ""
    if getattr(gestion, "firma_consentimiento", None):
        ruta_archivo_firma = gestion.firma_consentimiento.name or ""

    tratamiento = TratamientoDatosFirmado.objects.create(
        cliente=gestion.cliente,
        atencion=atencion,
        fecha_hora_firma=firmado_en if estado == TratamientoDatosFirmado.ESTADO_FIRMADA else None,
        estado=estado,
        texto_tratamiento=TRATAMIENTO_DATOS_TEXTO_VIGENTE,
        version_tratamiento=TRATAMIENTO_DATOS_VERSION_VIGENTE,
        ruta_archivo_firma=ruta_archivo_firma,
        hash_integridad=build_tratamiento_integrity_hash(
            cliente_snapshot=cliente_snapshot,
            texto_tratamiento=TRATAMIENTO_DATOS_TEXTO_VIGENTE,
            version_tratamiento=TRATAMIENTO_DATOS_VERSION_VIGENTE,
            firmado_en=firmado_en,
            atencion_id=atencion.pk,
        ),
        sede=sede or "",
        tablet_utilizada=tablet_utilizada or "",
        usuario_inicio_proceso=usuario_inicio,
        usuario_cierre_proceso=usuario_cierre,
        snapshot_cliente=cliente_snapshot,
    )
    gestion.tratamiento_firmado = tratamiento
    gestion.save(update_fields=["tratamiento_firmado"])
    atencion.tratamiento_completado = tratamiento.esta_firmado
    atencion.estado_atencion = AtencionServicio.ESTADO_COMPLETADA if tratamiento.esta_firmado else atencion.estado_atencion
    atencion.save(update_fields=["tratamiento_completado", "estado_atencion", "actualizado_en"])
    return tratamiento


def complete_tablet_capture(form, token_obj):
    gestion = save_gestion_form(
        form,
        usuario=token_obj.creado_por,
        tablet_utilizada='default-tablet',
    )
    firmado_en = timezone.now()
    atencion = create_atencion_from_gestion(
        gestion,
        usuario=token_obj.creado_por,
        estado=AtencionServicio.ESTADO_COMPLETADA,
    )
    tratamiento = create_tratamiento_from_gestion(
        gestion,
        atencion=atencion,
        usuario_inicio=token_obj.creado_por,
        usuario_cierre=token_obj.creado_por,
        tablet_utilizada='default-tablet',
        estado=TratamientoDatosFirmado.ESTADO_FIRMADA,
        firmado_en=firmado_en,
    )
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
        payload={
            "gestion_id": str(gestion.pk),
            "atencion_id": str(atencion.pk),
            "tratamiento_id": str(tratamiento.pk),
            "signed_at": firmado_en.isoformat(),
        },
    )
    notify_back_to_waiting(
        'default-tablet',
        session_id=str(token_obj.token),
        payload={"gestion_id": str(gestion.pk)},
    )
    return gestion
