from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from .forms import BaseDiariaCuentaForm, CuentaFinancieraForm, TransferenciaCuentaForm
from .models import CuentaFinanciera, MovimientoCuenta
from .services import (
    ControlFondosError,
    asegurar_cuentas_base,
    detalle_cuenta,
    listar_movimientos,
    obtener_destacados_dashboard,
    registrar_base_diaria,
    registrar_transferencia,
    resumen_jornada,
)


def _can_view(request):
    return request.user.is_authenticated


def _can_manage(request):
    return request.user.is_superuser or request.user.has_perm("compras.change_compra")


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
    return render(request, "control_fondos/dashboard.html", context)


@login_required
@require_http_methods(["GET", "POST"])
def apertura(request):
    if not _can_manage(request):
        return HttpResponseForbidden("No tienes permisos para cargar bases diarias.")
    asegurar_cuentas_base()

    if request.method == "POST":
        form = BaseDiariaCuentaForm(request.POST)
        if form.is_valid():
            try:
                registrar_base_diaria(
                    cuenta=form.cleaned_data["cuenta"],
                    base_inicial=form.cleaned_data["base_inicial"],
                    usuario=request.user,
                    fecha=form.cleaned_data["fecha"],
                    observacion=form.cleaned_data["observacion"],
                )
            except ControlFondosError as exc:
                form.add_error(None, str(exc))
            else:
                messages.success(request, "Base diaria registrada correctamente.")
                return redirect(f"{reverse('control_fondos:apertura')}?fecha={form.cleaned_data['fecha']:%Y-%m-%d}")
    else:
        form = BaseDiariaCuentaForm(initial={"fecha": request.GET.get("fecha") or timezone.localdate()})

    fecha = form.initial.get("fecha") or form.data.get("fecha") or timezone.localdate()
    if isinstance(fecha, str):
        try:
            fecha = timezone.datetime.strptime(fecha, "%Y-%m-%d").date()
        except ValueError:
            fecha = timezone.localdate()

    context = resumen_jornada(fecha=fecha)
    context["form"] = form
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
@require_http_methods(["GET"])
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
    q = (request.GET.get("q") or "").strip()
    solo_correcciones = request.GET.get("solo_correcciones") == "1"

    context = listar_movimientos(
        fecha=fecha,
        cuenta_id=cuenta_id,
        tipo=tipo,
        clase=clase,
        usuario_id=usuario_id,
        estado=estado,
        q=q,
        solo_correcciones=solo_correcciones,
    )
    paginator = Paginator(context["movimientos"], 20)
    page_obj = paginator.get_page(request.GET.get("page"))
    context.update({
        "fecha_consulta": fecha,
        "cuentas": CuentaFinanciera.objects.filter(activa=True).order_by("orden_visual", "nombre"),
        "tipos": MovimientoCuenta.TIPOS,
        "clases": MovimientoCuenta.CLASES,
        "estados": MovimientoCuenta.ESTADOS,
        "tipo_actual": tipo or "",
        "clase_actual": clase or "",
        "cuenta_actual": cuenta_id or "",
        "usuario_actual": usuario_id or "",
        "estado_actual": estado or "",
        "q_actual": q,
        "solo_correcciones": solo_correcciones,
        "usuarios": [],
        "page_obj": page_obj,
        "movimientos": page_obj.object_list,
    })
    return render(request, "control_fondos/movimientos.html", context)


@login_required
@require_http_methods(["GET", "POST"])
def transferencias(request):
    if not _can_manage(request):
        return HttpResponseForbidden("No tienes permisos para registrar transferencias.")
    asegurar_cuentas_base()

    if request.method == "POST":
        form = TransferenciaCuentaForm(request.POST)
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
