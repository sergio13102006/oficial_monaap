from io import BytesIO

from openpyxl import Workbook
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseForbidden
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from core.permisos import es_admin, es_auxiliar, es_colaborador

from .forms import (
    AperturaJornadaForm,
    BaseDiariaCuentaForm,
    CierreJornadaForm,
    CuentaFinancieraForm,
    MovimientoControladoForm,
    ReaperturaJornadaForm,
    TransferenciaCuentaForm,
)
from .models import BitacoraFondos, CuentaFinanciera, JornadaDiaria, MovimientoCuenta
from .services import (
    ControlFondosError,
    abrir_jornada,
    asegurar_cuentas_base,
    detalle_cuenta,
    listar_movimientos,
    obtener_destacados_dashboard,
    registrar_cierre_jornada,
    registrar_base_diaria,
    registrar_movimiento_controlado,
    registrar_transferencia,
    reabrir_jornada,
    resumen_jornada,
)


def _can_view(request):
    return request.user.is_authenticated


def _can_manage(request):
    return es_admin(request.user) or es_auxiliar(request.user) or request.user.is_superuser


def _puede_exportar(request):
    return _can_manage(request) or es_colaborador(request.user)


def _contexto_operativo(fecha):
    destacados = obtener_destacados_dashboard(fecha=fecha)
    estado_jornada = destacados.get("estado_jornada")
    apertura_completa = bool(destacados.get("apertura_completa"))
    return {
        "estado_jornada": estado_jornada,
        "estado_jornada_display": destacados.get("estado_jornada_display"),
        "apertura_completa": apertura_completa,
        "operacion_bloqueada": estado_jornada == JornadaDiaria.ESTADO_APERTURA_INCOMPLETA or not apertura_completa,
        "puede_nuevo_movimiento": apertura_completa and estado_jornada in {"ABIERTO", "REABIERTO_CON_AUTORIZACION", "EN_REVISION"},
        "puede_transferir": apertura_completa and estado_jornada in {"ABIERTO", "REABIERTO_CON_AUTORIZACION", "EN_REVISION"},
        "puede_conciliar": apertura_completa and estado_jornada in {"ABIERTO", "REABIERTO_CON_AUTORIZACION", "EN_REVISION"},
        "puede_cerrar": apertura_completa and estado_jornada in {"ABIERTO", "REABIERTO_CON_AUTORIZACION", "EN_REVISION"},
    }


@login_required
@require_http_methods(["GET"])
def dashboard(request):
    asegurar_cuentas_base()
    fecha_str = request.GET.get("fecha", "").strip()
    fecha = timezone.localdate()
    if fecha_str:
        try:
            fecha = timezone.datetime.strptime(fecha_str, "%Y-%m-%d").date()
        except ValueError:
            fecha = timezone.localdate()
    context = resumen_jornada(fecha=fecha)
    context["fecha_consulta"] = fecha
    context.update(obtener_destacados_dashboard(fecha=fecha))
    context["puede_gestionar_cuentas"] = _can_manage(request)
    context["puede_ver_bitacora"] = _can_view(request)
    context["puede_exportar_reportes"] = _puede_exportar(request)
    context.update(_contexto_operativo(fecha))
    return render(request, "control_fondos/dashboard.html", context)


@login_required
@require_http_methods(["GET", "POST"])
def apertura(request):
    if not _can_manage(request):
        return HttpResponseForbidden("No tienes permisos para cargar bases diarias.")
    asegurar_cuentas_base()

    if request.method == "POST":
        apertura_form = AperturaJornadaForm(request.POST)
        base_form = BaseDiariaCuentaForm(request.POST)
        accion = request.POST.get("accion", "base")
        if accion == "apertura" and apertura_form.is_valid():
            try:
                abrir_jornada(
                    fecha=apertura_form.cleaned_data["fecha"],
                    usuario=request.user,
                    sede=apertura_form.cleaned_data["sede"],
                    base_inicial_caja=apertura_form.cleaned_data["base_inicial_caja"],
                    base_inicial_caja_fuerte=apertura_form.cleaned_data["base_inicial_caja_fuerte"],
                    observacion=apertura_form.cleaned_data["observacion_apertura"],
                )
            except ControlFondosError as exc:
                apertura_form.add_error(None, str(exc))
            else:
                messages.success(request, "Jornada abierta correctamente.")
                return redirect(f"{reverse('control_fondos:apertura')}?fecha={apertura_form.cleaned_data['fecha']:%Y-%m-%d}")
        elif accion == "base" and base_form.is_valid():
            try:
                registrar_base_diaria(
                    cuenta=base_form.cleaned_data["cuenta"],
                    base_inicial=base_form.cleaned_data["base_inicial"],
                    usuario=request.user,
                    fecha=base_form.cleaned_data["fecha"],
                    observacion=base_form.cleaned_data["observacion"],
                )
            except ControlFondosError as exc:
                base_form.add_error(None, str(exc))
            else:
                messages.success(request, "Base diaria registrada correctamente.")
                return redirect(f"{reverse('control_fondos:apertura')}?fecha={base_form.cleaned_data['fecha']:%Y-%m-%d}")
    else:
        fecha_inicial = request.GET.get("fecha") or timezone.localdate()
        apertura_form = AperturaJornadaForm(initial={"fecha": fecha_inicial})
        base_form = BaseDiariaCuentaForm(initial={"fecha": fecha_inicial})

    fecha = (
        apertura_form.initial.get("fecha")
        or base_form.initial.get("fecha")
        or apertura_form.data.get("fecha")
        or base_form.data.get("fecha")
        or timezone.localdate()
    )
    if isinstance(fecha, str):
        try:
            fecha = timezone.datetime.strptime(fecha, "%Y-%m-%d").date()
        except ValueError:
            fecha = timezone.localdate()

    context = resumen_jornada(fecha=fecha)
    context["apertura_form"] = apertura_form
    context["base_form"] = base_form
    context["fecha_consulta"] = fecha
    return render(request, "control_fondos/apertura.html", context)


@login_required
@require_http_methods(["GET"])
def historico(request):
    asegurar_cuentas_base()
    fecha_str = request.GET.get("fecha", "").strip()
    fecha = timezone.localdate()
    if fecha_str:
        try:
            fecha = timezone.datetime.strptime(fecha_str, "%Y-%m-%d").date()
        except ValueError:
            fecha = timezone.localdate()
    context = resumen_jornada(fecha=fecha, incluir_inactivas=True)
    context.update(listar_movimientos(fecha=fecha))
    context["fecha_consulta"] = fecha
    return render(request, "control_fondos/historico.html", context)


@login_required
@require_http_methods(["GET"])
def bitacora(request):
    asegurar_cuentas_base()
    fecha_str = request.GET.get("fecha", "").strip()
    fecha = timezone.localdate()
    if fecha_str:
        try:
            fecha = timezone.datetime.strptime(fecha_str, "%Y-%m-%d").date()
        except ValueError:
            fecha = timezone.localdate()
    bitacoras = BitacoraFondos.objects.filter(fecha_hora__date=fecha).select_related("usuario")[:200]
    context = {
        "fecha_consulta": fecha,
        "bitacoras": bitacoras,
        "puede_exportar_reportes": _puede_exportar(request),
    }
    return render(request, "control_fondos/bitacora.html", context)


def _xlsx_response(filename, sheet_name, header, rows):
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = sheet_name[:31]
    worksheet.append(list(header))
    for row in rows:
        worksheet.append(list(row))
    buffer = BytesIO()
    workbook.save(buffer)
    response = HttpResponse(
        buffer.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@login_required
@require_http_methods(["GET"])
def exportar_movimientos_excel(request):
    asegurar_cuentas_base()
    if not _puede_exportar(request):
        return HttpResponseForbidden("No tienes permisos para exportar reportes.")
    fecha_str = request.GET.get("fecha", "").strip()
    fecha = timezone.localdate()
    if fecha_str:
        try:
            fecha = timezone.datetime.strptime(fecha_str, "%Y-%m-%d").date()
        except ValueError:
            fecha = timezone.localdate()
    data = listar_movimientos(fecha=fecha)["movimientos"].select_related("cuenta", "usuario")
    rows = (
        [
            movimiento.fecha_hora.strftime("%Y-%m-%d %H:%M"),
            movimiento.cuenta.nombre,
            movimiento.get_tipo_display(),
            movimiento.get_clase_display(),
            movimiento.valor,
            movimiento.concepto,
            movimiento.referencia or "",
            movimiento.usuario.get_username() if movimiento.usuario else "Sistema",
            movimiento.get_estado_display(),
        ]
        for movimiento in data
    )
    return _xlsx_response(
        f"movimientos_{fecha:%Y%m%d}.xlsx",
        "Movimientos",
        ["Fecha hora", "Cuenta", "Tipo", "Clase", "Valor", "Concepto", "Referencia", "Usuario", "Estado"],
        rows,
    )


@login_required
@require_http_methods(["GET"])
def exportar_bitacora_excel(request):
    asegurar_cuentas_base()
    if not _puede_exportar(request):
        return HttpResponseForbidden("No tienes permisos para exportar reportes.")
    fecha_str = request.GET.get("fecha", "").strip()
    fecha = timezone.localdate()
    if fecha_str:
        try:
            fecha = timezone.datetime.strptime(fecha_str, "%Y-%m-%d").date()
        except ValueError:
            fecha = timezone.localdate()
    rows = (
        [
            bitacora.fecha_hora.strftime("%Y-%m-%d %H:%M"),
            bitacora.accion,
            bitacora.modelo,
            bitacora.objeto_id,
            bitacora.usuario.get_username() if bitacora.usuario else "",
            bitacora.motivo,
        ]
        for bitacora in BitacoraFondos.objects.filter(fecha_hora__date=fecha).select_related("usuario")
    )
    return _xlsx_response(
        f"bitacora_{fecha:%Y%m%d}.xlsx",
        "Bitacora",
        ["Fecha hora", "Accion", "Modelo", "Objeto", "Usuario", "Motivo"],
        rows,
    )


@login_required
@require_http_methods(["GET"])
def exportar_cierre_excel(request):
    asegurar_cuentas_base()
    if not _puede_exportar(request):
        return HttpResponseForbidden("No tienes permisos para exportar reportes.")
    fecha_str = request.GET.get("fecha", "").strip()
    fecha = timezone.localdate()
    if fecha_str:
        try:
            fecha = timezone.datetime.strptime(fecha_str, "%Y-%m-%d").date()
        except ValueError:
            fecha = timezone.localdate()
    resumen = resumen_jornada(fecha=fecha)
    totales = resumen["totales"]
    rows = [
        ["Estado jornada", resumen["estado_jornada_display"]],
        ["Base caja principal", resumen["jornada"].base_inicial_caja],
        ["Base caja fuerte", resumen["jornada"].base_inicial_caja_fuerte],
        ["Total ingresos", totales["total_ingresos"]],
        ["Total egresos", totales["total_egresos"]],
        ["Caja esperada", totales["caja_esperada"] if totales["caja_esperada"] is not None else ""],
        ["Caja fuerte esperada", totales["caja_fuerte_esperada"] if totales["caja_fuerte_esperada"] is not None else ""],
        ["Diferencia caja", totales["diferencia_caja"] if totales["diferencia_caja"] is not None else ""],
        ["Diferencia caja fuerte", totales["diferencia_caja_fuerte"] if totales["diferencia_caja_fuerte"] is not None else ""],
        ["Diferencia transferencias", totales["diferencia_transferencias"] if totales["diferencia_transferencias"] is not None else ""],
        ["Diferencia datofono", totales["diferencia_datofono"] if totales["diferencia_datofono"] is not None else ""],
        ["Diferencia financiacion", totales["diferencia_financiacion"] if totales["diferencia_financiacion"] is not None else ""],
    ]
    return _xlsx_response(
        f"cierre_{fecha:%Y%m%d}.xlsx",
        "Cierre",
        ["Concepto", "Valor"],
        rows,
    )


@login_required
@require_http_methods(["GET", "POST"])
def cuentas(request):
    if not _can_manage(request):
        return HttpResponseForbidden("No tienes permisos para administrar cuentas financieras.")
    asegurar_cuentas_base()

    if request.method == "POST":
        form = CuentaFinancieraForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Cuenta financiera registrada correctamente.")
            return redirect("control_fondos:cuentas")
    else:
        form = CuentaFinancieraForm(initial={"activa": True})

    context = {
        "form": form,
        "cuentas": CuentaFinanciera.objects.order_by("orden_visual", "nombre"),
    }
    return render(request, "control_fondos/cuentas.html", context)


@login_required
@require_http_methods(["GET", "POST"])
def movimientos(request):
    asegurar_cuentas_base()
    fecha_str = request.GET.get("fecha", "").strip()
    fecha = timezone.localdate()
    if fecha_str:
        try:
            fecha = timezone.datetime.strptime(fecha_str, "%Y-%m-%d").date()
        except ValueError:
            fecha = timezone.localdate()

    cuenta_id = (request.GET.get("cuenta") or "").strip() or None
    tipo = (request.GET.get("tipo") or "").strip() or None
    clase = (request.GET.get("clase") or "").strip() or None
    usuario_id = (request.GET.get("usuario") or "").strip() or None
    estado = (request.GET.get("estado") or "").strip() or None
    tipo_movimiento = (request.GET.get("tipo_movimiento") or "").strip() or None
    profesional = (request.GET.get("profesional") or "").strip() or None
    cliente = (request.GET.get("cliente") or "").strip() or None
    medio_pago = (request.GET.get("medio_pago") or "").strip() or None
    q = (request.GET.get("q") or "").strip()
    solo_correcciones = request.GET.get("solo_correcciones") == "1"

    if request.method == "POST":
        form = MovimientoControladoForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                registrar_movimiento_controlado(
                    cuenta=form.cleaned_data["cuenta"],
                    tipo_movimiento=form.cleaned_data["tipo_movimiento"],
                    valor_total=form.cleaned_data["valor_total"],
                    usuario=request.user,
                    fecha=form.cleaned_data["fecha"],
                    procedimiento=form.cleaned_data.get("procedimiento", ""),
                    producto_servicio=form.cleaned_data.get("producto_servicio", ""),
                    profesional=str(form.cleaned_data["profesional"]) if form.cleaned_data.get("profesional") else "",
                    cliente=str(form.cleaned_data["cliente"]) if form.cleaned_data.get("cliente") else "",
                    entrada_efectivo=form.cleaned_data.get("entrada_efectivo") or 0,
                    salida_efectivo=form.cleaned_data.get("salida_efectivo") or 0,
                    bancolombia=form.cleaned_data.get("bancolombia") or 0,
                    nequi=form.cleaned_data.get("nequi") or 0,
                    daviplata=form.cleaned_data.get("daviplata") or 0,
                    nubank=form.cleaned_data.get("nubank") or 0,
                    datofono=form.cleaned_data.get("datofono") or 0,
                    sistecredito_addi=form.cleaned_data.get("sistecredito_addi") or 0,
                    ingreso_caja_fuerte=form.cleaned_data.get("ingreso_caja_fuerte") or 0,
                    retiro_caja_fuerte=form.cleaned_data.get("retiro_caja_fuerte") or 0,
                    tarjeta_credito_compras=form.cleaned_data.get("tarjeta_credito_compras") or 0,
                    motivo_salida=form.cleaned_data.get("motivo_salida") or "",
                    referencia=form.cleaned_data.get("referencia") or "",
                    comprobante=form.cleaned_data.get("comprobante") or "",
                    soporte_adjunto=form.cleaned_data.get("soporte_adjunto"),
                    observacion=form.cleaned_data.get("observacion") or "",
                    request_uid=None,
                    descuento=form.cleaned_data.get("descuento") or 0,
                    valor_neto=form.cleaned_data.get("valor_neto"),
                )
            except ControlFondosError as exc:
                form.add_error(None, str(exc))
            else:
                messages.success(request, "Movimiento registrado correctamente.")
                return redirect(f"{reverse('control_fondos:movimientos')}?fecha={form.cleaned_data['fecha']:%Y-%m-%d}")
    else:
        form = MovimientoControladoForm(initial={"fecha": fecha})

    context = listar_movimientos(
        fecha=fecha,
        cuenta_id=cuenta_id,
        tipo=tipo,
        clase=clase,
        tipo_movimiento=tipo_movimiento,
        usuario_id=usuario_id,
        estado=estado,
        profesional=profesional,
        cliente=cliente,
        medio_pago=medio_pago,
        q=q,
        solo_correcciones=solo_correcciones,
    )
    paginator = Paginator(context["movimientos"], 20)
    page_obj = paginator.get_page(request.GET.get("page"))
    context.update({
        "fecha_consulta": fecha,
        **_contexto_operativo(fecha),
        "cuentas": CuentaFinanciera.objects.filter(activa=True).order_by("orden_visual", "nombre"),
        "tipos": MovimientoCuenta.TIPOS,
        "clases": MovimientoCuenta.CLASES,
        "tipos_movimiento": MovimientoCuenta.TIPOS_MOVIMIENTO,
        "estados": MovimientoCuenta.ESTADOS,
        "tipo_actual": tipo or "",
        "clase_actual": clase or "",
        "tipo_movimiento_actual": tipo_movimiento or "",
        "cuenta_actual": cuenta_id or "",
        "usuario_actual": usuario_id or "",
        "estado_actual": estado or "",
        "profesional_actual": profesional or "",
        "cliente_actual": cliente or "",
        "medio_pago_actual": medio_pago or "",
        "q_actual": q,
        "solo_correcciones": solo_correcciones,
        "usuarios": [],
        "page_obj": page_obj,
        "movimientos": page_obj.object_list,
        "form": form,
    })
    return render(request, "control_fondos/movimientos.html", context)


@login_required
@require_http_methods(["GET", "POST"])
def transferencias(request):
    if not _can_manage(request):
        return HttpResponseForbidden("No tienes permisos para registrar transferencias.")
    asegurar_cuentas_base()

    if request.method == "POST":
        form = TransferenciaCuentaForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                registrar_transferencia(
                    cuenta_origen=form.cleaned_data["cuenta_origen"],
                    cuenta_destino=form.cleaned_data["cuenta_destino"],
                    valor=form.cleaned_data["valor"],
                    usuario=request.user,
                    fecha=form.cleaned_data["fecha"],
                    request_uid=form.cleaned_data.get("request_uid"),
                    observacion=form.cleaned_data.get("observacion"),
                    referencia=form.cleaned_data.get("referencia"),
                    comprobante=form.cleaned_data.get("comprobante"),
                    soporte_adjunto=form.cleaned_data.get("soporte_adjunto"),
                )
            except ControlFondosError as exc:
                form.add_error(None, str(exc))
            else:
                messages.success(request, "Transferencia registrada correctamente.")
                return redirect(
                    f"{reverse('control_fondos:transferencias')}?fecha={form.cleaned_data['fecha']:%Y-%m-%d}"
                    f"&ultima_transferencia=1&request_uid={form.cleaned_data.get('request_uid')}"
                )
    else:
        form = TransferenciaCuentaForm(initial={"fecha": request.GET.get("fecha") or timezone.localdate()})

    fecha = form.initial.get("fecha") or form.data.get("fecha") or timezone.localdate()
    if isinstance(fecha, str):
        try:
            fecha = timezone.datetime.strptime(fecha, "%Y-%m-%d").date()
        except ValueError:
            fecha = timezone.localdate()

    context = listar_movimientos(fecha=fecha, clase=MovimientoCuenta.CLASE_TRANSFERENCIA)
    context["form"] = form
    context["fecha_consulta"] = fecha
    context.update(_contexto_operativo(fecha))
    request_uid = (request.GET.get("request_uid") or "").strip()
    if request.GET.get("ultima_transferencia") == "1" and request_uid:
        salida = MovimientoCuenta.objects.filter(request_uid=f"{request_uid}:salida").select_related("cuenta", "usuario").first()
        entrada = MovimientoCuenta.objects.filter(request_uid=f"{request_uid}:entrada").select_related("cuenta", "usuario").first()
        context["ultima_transferencia"] = {
            "salida": salida,
            "entrada": entrada,
        } if salida and entrada else None
    return render(request, "control_fondos/transferencias.html", context)


@login_required
@require_http_methods(["GET"])
def detalle_cuenta_view(request, pk):
    asegurar_cuentas_base()
    fecha_str = request.GET.get("fecha", "").strip()
    fecha = timezone.localdate()
    if fecha_str:
        try:
            fecha = timezone.datetime.strptime(fecha_str, "%Y-%m-%d").date()
        except ValueError:
            fecha = timezone.localdate()

    cuenta = get_object_or_404(CuentaFinanciera, pk=pk)
    context = detalle_cuenta(cuenta=cuenta, fecha=fecha)
    paginator = Paginator(context["movimientos_cuenta"], 20)
    page_obj = paginator.get_page(request.GET.get("page"))
    context.update({
        "cuenta": cuenta,
        "fecha_consulta": fecha,
        "page_obj": page_obj,
        "movimientos_cuenta": page_obj.object_list,
    })
    return render(request, "control_fondos/detalle_cuenta.html", context)


@login_required
@require_http_methods(["GET", "POST"])
def cierre(request):
    asegurar_cuentas_base()

    if request.method == "POST":
        form = CierreJornadaForm(request.POST)
        if form.is_valid():
            try:
                jornada = registrar_cierre_jornada(
                    fecha=form.cleaned_data["fecha"],
                    efectivo_contado_real=form.cleaned_data["efectivo_contado_real"],
                    caja_fuerte_contada_real=form.cleaned_data["caja_fuerte_contada_real"],
                    transferencias_verificadas=form.cleaned_data.get("transferencias_verificadas"),
                    datofono_verificado=form.cleaned_data.get("datofono_verificado"),
                    financiacion_verificada=form.cleaned_data.get("financiacion_verificada"),
                    observacion_cierre=form.cleaned_data.get("observacion_cierre"),
                    usuario=request.user,
                    autorizacion_supervisor=form.cleaned_data.get("autorizacion_supervisor", False),
                )
            except ControlFondosError as exc:
                form.add_error(None, str(exc))
            else:
                messages.success(request, f"Jornada {jornada.fecha:%Y-%m-%d} cerrada correctamente.")
                return redirect(f"{reverse('control_fondos:cierre')}?fecha={jornada.fecha:%Y-%m-%d}")
    else:
        form = CierreJornadaForm(initial={"fecha": request.GET.get("fecha") or timezone.localdate()})

    fecha = form.initial.get("fecha") or form.data.get("fecha") or timezone.localdate()
    if isinstance(fecha, str):
        try:
            fecha = timezone.datetime.strptime(fecha, "%Y-%m-%d").date()
        except ValueError:
            fecha = timezone.localdate()

    context = resumen_jornada(fecha=fecha)
    movimientos_context = listar_movimientos(fecha=fecha)
    context["form"] = form
    context["fecha_consulta"] = fecha
    context["jornada_actual"] = context["jornada"]
    context["movimientos"] = movimientos_context["movimientos"]
    context["totales"] = context["totales"]
    context["caja_esperada"] = context["totales"]["caja_esperada"]
    context["caja_fuerte_esperada"] = context["totales"]["caja_fuerte_esperada"]
    context["diferencia_caja"] = context["totales"]["diferencia_caja"]
    context["diferencia_caja_fuerte"] = context["totales"]["diferencia_caja_fuerte"]
    context["diferencia_transferencias"] = context["totales"]["diferencia_transferencias"]
    context["diferencia_datofono"] = context["totales"]["diferencia_datofono"]
    context["diferencia_financiacion"] = context["totales"]["diferencia_financiacion"]
    context.update(_contexto_operativo(fecha))
    if request.method == "POST":
        context["form"] = form
    return render(request, "control_fondos/cierre.html", context)


@login_required
@require_http_methods(["POST"])
def reabrir(request):
    if not _can_manage(request):
        return HttpResponseForbidden("No tienes permisos para reabrir la jornada.")

    form = ReaperturaJornadaForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Revisa la información para reabrir la jornada.")
        return redirect("control_fondos:dashboard")

    try:
        reabrir_jornada(
            fecha=form.cleaned_data["fecha"],
            usuario=request.user,
            motivo=form.cleaned_data["motivo"],
        )
    except ControlFondosError as exc:
        messages.error(request, str(exc))
    else:
        messages.success(request, "Jornada reabierta con autorización.")
    return redirect(f"{reverse('control_fondos:dashboard')}?fecha={form.cleaned_data['fecha']:%Y-%m-%d}")
