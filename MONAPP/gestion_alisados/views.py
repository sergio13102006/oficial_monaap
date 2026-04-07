from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db.models import Q, Count
from django.core.paginator import Paginator
from django.urls import reverse
from django.template.loader import render_to_string
from django.utils import timezone
from datetime import timedelta
import csv
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Spacer, Paragraph
from compras.comprobante import _get_logo_path, _get_watermark_path

from .models import GestionAlisado, TabletConsentToken, TabletKioskState
from .forms import GestionAlisadoForm
from .services import (
    build_admin_capture_context,
    build_invalid_tablet_context,
    build_modal_capture_context,
    build_tablet_capture_context,
    build_tablet_launch_payload,
    build_tablet_waiting_payload,
    build_tablet_websocket_url,
    build_websocket_url,
    complete_tablet_capture,
    get_cliente_nombre_gestion,
    get_kiosk_state,
    get_last_gestion_payload,
    get_last_gestion_values,
    get_valid_alisado_service_name,
    mark_kiosk_ready,
    mark_kiosk_waiting,
    mark_tablet_session_error,
    mark_tablet_session_opened,
    save_gestion_form,
    sync_token_process_state,
    start_tablet_session,
)
from clientes.models import Cliente
from promociones.models import Promocion
from servicios.models import Servicio


def es_staff(user):
    return user.is_staff


def _promociones_activas():
    return build_admin_capture_context(GestionAlisadoForm())["promociones_activas"]


def _servicio_alisado_valido(nombre_servicio):
    return get_valid_alisado_service_name(nombre_servicio)


def _iniciales_ultima_gestion(cliente_obj):
    return get_last_gestion_values(cliente_obj)


def _datos_ultima_gestion(cliente_obj):
    return get_last_gestion_payload(cliente_obj)


def _cliente_nombre_gestion(gestion_obj):
    return get_cliente_nombre_gestion(gestion_obj)


def _crear_token_tablet(cliente_obj, user=None, gestion=None, minutos_validos=120):
    return start_tablet_session(cliente_obj, user=user, minutos_validos=minutos_validos)


def _tablet_kiosk_state():
    return get_kiosk_state()


def _tablet_kiosk_waiting():
    return mark_kiosk_waiting()


def _tablet_kiosk_ready(cliente_obj, token_obj, gestion=None):
    return mark_kiosk_ready(cliente_obj, token_obj, gestion=gestion)


def _filtrar_gestiones_desde_request(request):
    gestiones = GestionAlisado.objects.select_related("cliente").all()
    buscar = request.GET.get("buscar", "")
    forma_natural = request.GET.get("forma_natural", "")
    porosidad = request.GET.get("porosidad", "")
    textura = request.GET.get("textura", "")
    estado_pago = request.GET.get("estado_pago", "")

    if buscar:
        gestiones = gestiones.filter(
            Q(cliente__nombre__icontains=buscar)
            | Q(cliente__apellido__icontains=buscar)
            | Q(procedimiento_realizado_por__icontains=buscar)
            | Q(tipo_alisado__icontains=buscar)
        )
    if forma_natural:
        gestiones = gestiones.filter(forma_natural=forma_natural)
    if porosidad:
        gestiones = gestiones.filter(porosidad=porosidad)
    if textura:
        gestiones = gestiones.filter(textura=textura)
    if estado_pago == "pagado":
        gestiones = gestiones.filter(saldo_pendiente=0)
    elif estado_pago == "pendiente":
        gestiones = gestiones.filter(saldo_pendiente__gt=0)

    return gestiones, buscar, forma_natural, porosidad, textura, estado_pago


@login_required
def form_gestion_alisado_modal_content(request):
    cliente_id = (request.GET.get("cliente") or "").strip()
    desde_clientes = (request.GET.get("desde_clientes") or "").strip() == "1"
    context = build_modal_capture_context(cliente_id=cliente_id, desde_clientes=desde_clientes)

    return render(
        request,
        "gestion_alisados/form_gestion_alisado_modal_content.html",
        context
    )


@login_required
def abrir_tablet_gestion_alisado(request, cliente_id):
    cliente_obj = get_object_or_404(Cliente, pk=cliente_id)
    token = _crear_token_tablet(cliente_obj, user=request.user, minutos_validos=120)
    _tablet_kiosk_ready(cliente_obj, token)
    payload = build_tablet_launch_payload(request, cliente_obj, token)
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.GET.get('format') == 'json':
        return JsonResponse(payload)
    messages.success(request, 'Proceso enviado a la tablet. La pantalla de espera recibirá el formulario.')
    return redirect('gestion_alisados:tablet_espera')


def tablet_espera(request):
    kiosk_state = _tablet_kiosk_state()
    token_obj = kiosk_state.token

    if kiosk_state.listo and token_obj:
        token_obj = sync_token_process_state(token_obj)
        if not token_obj.esta_vigente() or kiosk_state.estado != TabletKioskState.ESTADO_LISTO:
            _tablet_kiosk_waiting()
    else:
        _tablet_kiosk_waiting()

    context = build_tablet_waiting_payload(request)
    context["tablet_ws_url"] = build_tablet_websocket_url(request, "default-tablet")
    return render(request, 'gestion_alisados/tablet_espera.html', context)


def tablet_espera_estado(request):
    kiosk_state = _tablet_kiosk_state()
    token_obj = kiosk_state.token
    if not kiosk_state.listo or not token_obj:
        response = JsonResponse({'success': True, 'has_process': False})
    else:
        token_obj = sync_token_process_state(token_obj)
        if not token_obj.esta_vigente() or kiosk_state.estado != TabletKioskState.ESTADO_LISTO:
            _tablet_kiosk_waiting()
            response = JsonResponse({
                'success': True,
                'has_process': False,
                'process_state': token_obj.estado_proceso,
                'process_state_label': token_obj.get_estado_proceso_display(),
            })
        else:
            response = JsonResponse({
                'success': True,
                'has_process': True,
                'process_state': token_obj.estado_proceso,
                'process_state_label': token_obj.get_estado_proceso_display(),
                'cliente': {
                    'nombre': f'{token_obj.cliente.nombre} {token_obj.cliente.apellido}',
                    'documento': token_obj.cliente.numero_documento,
                },
                'tablet_process_url': request.build_absolute_uri(
                    reverse('gestion_alisados:tablet_gestion_alisado', kwargs={'token': token_obj.token})
                ),
            })
    response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response['Pragma'] = 'no-cache'
    return response


def _tablet_context_from_token(request, token_obj):
    return build_tablet_capture_context(token_obj)


def _tablet_template(request, context):
    return render(request, 'gestion_alisados/tablet_kiosk.html', context)


def _tablet_invalid(request, message='El enlace de la tablet no es válido o ya expiró.'):
    return render(
        request,
        'gestion_alisados/tablet_invalid.html',
        build_invalid_tablet_context(
            message=message,
            tablet_wait_url=request.build_absolute_uri(reverse('gestion_alisados:tablet_espera')),
        ),
        status=410,
    )


def tablet_gestion_alisado(request, token):
    token_obj = get_object_or_404(TabletConsentToken, token=token)
    token_obj = sync_token_process_state(token_obj)
    if not token_obj.esta_vigente():
        kiosk_state = _tablet_kiosk_state()
        if kiosk_state.token_id == token_obj.token:
            _tablet_kiosk_waiting()
        return _tablet_invalid(request)

    mark_tablet_session_opened(token_obj)
    context = _tablet_context_from_token(request, token_obj)

    if request.method == 'POST':
        form = GestionAlisadoForm(request.POST, request.FILES)
        form.fields["cliente"].widget.attrs["disabled"] = "disabled"
        if form.is_valid():
            try:
                gestion = complete_tablet_capture(form, token_obj)
                kiosk_state = _tablet_kiosk_state()
                if kiosk_state.token_id == token_obj.token:
                    _tablet_kiosk_waiting()
                return render(
                    request,
                    'gestion_alisados/tablet_success.html',
                    {
                        'gestion': gestion,
                        'cliente': token_obj.cliente,
                        'tablet_wait_url': request.build_absolute_uri(reverse('gestion_alisados:tablet_espera')),
                    },
                )
            except Exception:
                mark_tablet_session_error(token_obj, 'Ocurrio un error al guardar la captura en la tablet.')
                raise
        context['form'] = form

    return _tablet_template(request, context)

@login_required
def lista_gestion_alisados(request):
    gestiones = GestionAlisado.objects.select_related('cliente', 'tratamiento_firmado').annotate(
        historial_total=Count('cliente__tratamientos_datos', distinct=True)
    )

    buscar = request.GET.get('buscar', '').strip()
    fecha_desde = request.GET.get('fecha_desde', '').strip()
    fecha_hasta = request.GET.get('fecha_hasta', '').strip()
    per_page = request.GET.get('per_page', '20').strip()
    page_number = request.GET.get('page', '1').strip()
    current_sort = request.GET.get('sort', 'fecha').strip()
    current_dir = request.GET.get('dir', 'desc').strip().lower()
    if current_dir not in {'asc', 'desc'}:
        current_dir = 'desc'
    if per_page not in {'10', '20', '50'}:
        per_page = '20'

    if buscar:
        gestiones = gestiones.filter(
            Q(cliente__nombre__icontains=buscar) |
            Q(cliente__apellido__icontains=buscar) |
            Q(cliente__numero_documento__icontains=buscar) |
            Q(cliente__telefono__icontains=buscar) |
            Q(tipo_alisado__icontains=buscar)
        )
    if fecha_desde:
        gestiones = gestiones.filter(fecha_hora__date__gte=fecha_desde)
    if fecha_hasta:
        gestiones = gestiones.filter(fecha_hora__date__lte=fecha_hasta)

    sort_map = {
        'fecha': ('fecha_hora',),
        'cliente': ('cliente__nombre', 'cliente__apellido'),
        'profesional': ('procedimiento_realizado_por',),
        'tipo': ('tipo_alisado',),
        'precio': ('precio_alisado',),
        'saldo': ('saldo_pendiente',),
        'estado': ('tratamiento_firmado__estado', 'fecha_hora'),
        'historial': ('historial_total', 'cliente__nombre'),
    }

    if current_sort in sort_map:
        order_fields = []
        for field in sort_map[current_sort]:
            order_fields.append(field if current_dir == 'asc' else f'-{field}')
        gestiones = gestiones.order_by(*order_fields)
    else:
        current_sort = 'fecha'
        current_dir = 'desc'
        gestiones = gestiones.order_by('-fecha_hora')

    total_resultados = gestiones.count()
    paginator = Paginator(gestiones, int(per_page))
    page_obj = paginator.get_page(page_number)
    showing_from = ((page_obj.number - 1) * paginator.per_page) + 1 if total_resultados else 0
    showing_to = min(page_obj.number * paginator.per_page, total_resultados) if total_resultados else 0
    page_numbers = []
    if paginator.num_pages <= 7:
        page_numbers = list(paginator.page_range)
    else:
        current = page_obj.number
        candidates = {1, paginator.num_pages, current - 1, current, current + 1}
        candidates = sorted(num for num in candidates if 1 <= num <= paginator.num_pages)
        last = None
        for num in candidates:
            if last is not None and num - last > 1:
                page_numbers.append('ellipsis')
            page_numbers.append(num)
            last = num

    context = {
        'gestiones': page_obj.object_list,
        'page_obj': page_obj,
        'paginator': paginator,
        'page_numbers': page_numbers,
        'total_resultados': total_resultados,
        'showing_from': showing_from,
        'showing_to': showing_to,
        'buscar': buscar,
        'fecha_desde': fecha_desde,
        'fecha_hasta': fecha_hasta,
        'per_page': per_page,
        'current_sort': current_sort,
        'current_dir': current_dir,
        'admin_ws_url': build_websocket_url(request, "/ws/gestion-alisados/admin/"),
    }

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, 'gestion_alisados/lista_gestion_alisados_global.html', context)

    return render(request, 'gestion_alisados/lista_gestion_alisados.html', context)


@login_required
def reporte_gestion_preview(request):
    gestiones, buscar, forma_natural, porosidad, textura, estado_pago = _filtrar_gestiones_desde_request(request)

    filtros = []
    if buscar:
        filtros.append(f"Buscar: {buscar}")
    if forma_natural:
        filtros.append(f"Forma: {forma_natural.title()}")
    if porosidad:
        filtros.append(f"Porosidad: {porosidad.title()}")
    if textura:
        filtros.append(f"Textura: {textura.title()}")

    context = {
        "gestiones": gestiones.order_by("-fecha_hora"),
        "total_registros": gestiones.count(),
        "estado_texto": estado_pago.title() if estado_pago else "Todos",
        "filtros_texto": " | ".join(filtros) if filtros else "Sin filtros",
    }

    html = render_to_string(
        "gestion_alisados/comprobante_reporte_gestion_preview.html",
        context,
        request=request,
    )
    return JsonResponse({"success": True, "html": html})

@login_required
def crear_gestion_alisado(request):
    """
    Crea un nuevo registro de gestión de alisado
    - modal=1 o AJAX: devuelve JSON
    - normal: render/redirect normal
    """
    is_modal = request.GET.get('modal') == '1'
    es_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    if request.method == 'POST':
        form = GestionAlisadoForm(request.POST, request.FILES)

        if form.is_valid():
            gestion = save_gestion_form(form, usuario=request.user)
            if is_modal or es_ajax:
                return JsonResponse({
                    'success': True,
                    'message': 'Gestión de alisado registrada exitosamente.'
                }, status=201)

            messages.success(request, 'Gestión de alisado registrada exitosamente.')
            return redirect('gestion_alisados:lista_gestion_alisados')

        # inválido
        if is_modal or es_ajax:
            return JsonResponse({
                'success': False,
                'message': 'Por favor corrija los errores en el formulario.',
                'errors': form.errors
            }, status=400)

    else:
        # GET
        # Si vienen por link normal ?cliente=ID podemos precargar también
        cliente_id = (request.GET.get("cliente") or "").strip()
        if cliente_id:
            try:
                cliente_obj = Cliente.objects.get(id=int(cliente_id))
                form = GestionAlisadoForm(initial=_iniciales_ultima_gestion(cliente_obj))
            except (ValueError, Cliente.DoesNotExist):
                form = GestionAlisadoForm()
        else:
            form = GestionAlisadoForm()

    context = {
        'form': form,
        'titulo': 'Gestión de Alisado',
        'is_modal': is_modal,
        'action_url': request.get_full_path() if is_modal else request.path,
        'promociones_activas': build_admin_capture_context(form=form)['promociones_activas'],
    }

    # Si es modal, usar template simplificado
    if is_modal:
        return render(request, 'gestion_alisados/form_gestion_alisado_modal_content.html', context)

    if is_modal:
        return render(request, 'gestion_alisados/form_gestion_alisado_modal_content.html', context)
    return render(request, 'gestion_alisados/form_gestion_alisado.html', context)


@login_required
def ultima_gestion_cliente(request):
    cliente_id = (request.GET.get("cliente") or "").strip()
    if not cliente_id:
        return JsonResponse({"success": False, "message": "Cliente no indicado."}, status=400)

    try:
        cliente_obj = Cliente.objects.get(pk=int(cliente_id))
    except (ValueError, Cliente.DoesNotExist):
        return JsonResponse({"success": False, "message": "Cliente no válido."}, status=404)

    datos = _datos_ultima_gestion(cliente_obj)
    return JsonResponse({
        "success": True,
        "tiene_historial": bool(datos),
        "datos": datos,
    })


@login_required
@user_passes_test(es_staff)
def ver_gestion_alisado(request, pk):
    """Muestra los detalles de una gestión de alisado"""
    gestion = get_object_or_404(GestionAlisado, pk=pk)
    context = {
        'gestion': gestion
    }
    return render(request, 'gestion_alisados/detalle_gestion_alisado.html', context)


@login_required
@user_passes_test(es_staff)
def ver_gestion_alisado_modal_content(request, pk):
    gestion = get_object_or_404(GestionAlisado, pk=pk)
    return render(
        request,
        'gestion_alisados/detalle_gestion_alisado_modal_content.html',
        {'gestion': gestion},
    )


@login_required
def ver_historial_cliente_modal(request, cliente_id):
    cliente = get_object_or_404(Cliente, pk=cliente_id)
    gestiones = GestionAlisado.objects.select_related('tratamiento_firmado').filter(cliente=cliente).order_by('-fecha_hora')
    return render(
        request,
        'gestion_alisados/historial_cliente_modal_content.html',
        {
            'cliente': cliente,
            'gestiones': gestiones,
            'total_tratamientos': gestiones.count(),
        },
    )


@login_required
def editar_gestion_alisado(request, pk):
    """Edita una gestión de alisado existente"""
    gestion = get_object_or_404(GestionAlisado, pk=pk)
    tratamiento = getattr(gestion, "tratamiento_firmado", None)
    if tratamiento and tratamiento.esta_firmado:
        mensaje = 'Este tratamiento ya fue firmado y no se puede editar.'
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'message': mensaje}, status=403)
        messages.error(request, mensaje)
        return redirect('gestion_alisados:ver_gestion_alisado', pk=gestion.pk)
    is_modal = request.GET.get('modal') == '1'
    es_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    if request.method == 'POST':
        form = GestionAlisadoForm(request.POST, request.FILES, instance=gestion)
        if form.is_valid():
            gestion = save_gestion_form(form, usuario=request.user)
            messages.success(request, 'Gestión de alisado actualizada exitosamente.')
            if is_modal or es_ajax:
                return JsonResponse({
                    'success': True,
                    'message': 'GestiÃ³n de alisado actualizada exitosamente.',
                    'gestion_id': str(gestion.pk),
                }, status=200)
            return redirect('gestion_alisados:ver_gestion_alisado', pk=gestion.pk)
        if is_modal or es_ajax:
            return JsonResponse({
                'success': False,
                'message': 'Por favor corrija los errores en el formulario.',
                'errors': form.errors
            }, status=400)
    else:
        form = GestionAlisadoForm(instance=gestion)

    context = {
        'form': form,
        'titulo': 'Editar Gestión de Alisado',
        'gestion': gestion,
        'is_modal': is_modal,
        'action_url': request.get_full_path() if is_modal else request.path,
        'promociones_activas': build_admin_capture_context(form=form)['promociones_activas'],
    }
    if is_modal:
        return render(request, 'gestion_alisados/form_gestion_alisado_modal_content.html', context)
    return render(request, 'gestion_alisados/form_gestion_alisado.html', context)


@login_required
def eliminar_gestion_alisado(request, pk):
    """Elimina una gestión de alisado"""
    gestion = get_object_or_404(GestionAlisado, pk=pk)

    if request.method == 'POST':
        gestion.delete()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': 'Gestión de alisado eliminada exitosamente.'
            }, status=200)
        messages.success(request, 'Gestión de alisado eliminada exitosamente.')
        return redirect('gestion_alisados:lista_gestion_alisados')

    context = {
        'gestion': gestion
    }
    return render(request, 'gestion_alisados/eliminar_gestion_alisado.html', context)


@login_required
def exportar_reporte_gestion_csv(request):
    gestiones = GestionAlisado.objects.select_related("cliente").all()

    buscar = request.GET.get("buscar", "")
    forma_natural = request.GET.get("forma_natural", "")
    porosidad = request.GET.get("porosidad", "")
    textura = request.GET.get("textura", "")
    estado_pago = request.GET.get("estado_pago", "")

    if buscar:
        gestiones = gestiones.filter(
            Q(cliente__nombre__icontains=buscar) |
            Q(cliente__apellido__icontains=buscar) |
            Q(procedimiento_realizado_por__icontains=buscar) |
            Q(tipo_alisado__icontains=buscar)
        )
    if forma_natural:
        gestiones = gestiones.filter(forma_natural=forma_natural)
    if porosidad:
        gestiones = gestiones.filter(porosidad=porosidad)
    if textura:
        gestiones = gestiones.filter(textura=textura)
    if estado_pago == "pagado":
        gestiones = gestiones.filter(saldo_pendiente=0)
    elif estado_pago == "pendiente":
        gestiones = gestiones.filter(saldo_pendiente__gt=0)

    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="reporte_tratamiento_datos.csv"'
    response.write("\ufeff")

    writer = csv.writer(response)
    writer.writerow(
        [
            "Fecha y hora",
            "Cliente",
            "Profesional",
            "Tipo de alisado",
            "Precio alisado",
            "Saldo pendiente",
            "Forma natural",
            "Porosidad",
            "Textura",
        ]
    )

    for g in gestiones.order_by("-fecha_hora"):
        writer.writerow(
            [
                g.fecha_hora.strftime("%d/%m/%Y %H:%M"),
                _cliente_nombre_gestion(g),
                g.procedimiento_realizado_por,
                g.tipo_alisado,
                g.precio_alisado,
                g.saldo_pendiente,
                g.forma_natural,
                g.porosidad,
                g.textura,
            ]
        )

    return response


@login_required
def exportar_reporte_gestion_pdf(request):
    gestiones = GestionAlisado.objects.select_related("cliente").all()

    buscar = request.GET.get("buscar", "")
    forma_natural = request.GET.get("forma_natural", "")
    porosidad = request.GET.get("porosidad", "")
    textura = request.GET.get("textura", "")
    estado_pago = request.GET.get("estado_pago", "")

    if buscar:
        gestiones = gestiones.filter(
            Q(cliente__nombre__icontains=buscar) |
            Q(cliente__apellido__icontains=buscar) |
            Q(procedimiento_realizado_por__icontains=buscar) |
            Q(tipo_alisado__icontains=buscar)
        )
    if forma_natural:
        gestiones = gestiones.filter(forma_natural=forma_natural)
    if porosidad:
        gestiones = gestiones.filter(porosidad=porosidad)
    if textura:
        gestiones = gestiones.filter(textura=textura)
    if estado_pago == "pagado":
        gestiones = gestiones.filter(saldo_pendiente=0)
    elif estado_pago == "pendiente":
        gestiones = gestiones.filter(saldo_pendiente__gt=0)

    def _fmt_money(value):
        try:
            return f"${int(value):,}".replace(",", ".")
        except Exception:
            return "$0"

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=16 * mm,
        leftMargin=16 * mm,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
        title="Comprobante Gestión de Datos",
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "TitleStyleGestion",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#000000"),
        alignment=1,
        spaceAfter=2,
    )
    small_label_style = ParagraphStyle(
        "SmallLabelStyleGestion",
        parent=styles["BodyText"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=9,
        textColor=colors.HexColor("#333333"),
    )
    small_value_style = ParagraphStyle(
        "SmallValueStyleGestion",
        parent=styles["BodyText"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=13,
        textColor=colors.HexColor("#111111"),
    )
    text_style = ParagraphStyle(
        "TextStyleGestion",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=9,
        leading=11,
        textColor=colors.HexColor("#222222"),
    )
    footer_style = ParagraphStyle(
        "FooterStyleGestion",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#666666"),
        alignment=1,
    )

    elementos = []
    total_registros = gestiones.count()
    estado_texto = estado_pago.title() if estado_pago else "Todos"
    filtros_texto = []
    if buscar:
        filtros_texto.append(f"Buscar: {buscar}")
    if forma_natural:
        filtros_texto.append(f"Forma: {forma_natural.title()}")
    if porosidad:
        filtros_texto.append(f"Porosidad: {porosidad.title()}")
    if textura:
        filtros_texto.append(f"Textura: {textura.title()}")
    filtros_label = " | ".join(filtros_texto) if filtros_texto else "Sin filtros"

    logo_path = _get_logo_path()
    logo_flowable = ""
    if logo_path:
        try:
            from reportlab.platypus import Image as RLImage
            logo_flowable = RLImage(logo_path, width=34 * mm, height=16 * mm)
        except Exception:
            logo_flowable = ""

    header_table = Table(
        [[logo_flowable, Paragraph("Comprobante", title_style), ""]],
        colWidths=[42 * mm, 100 * mm, 26 * mm],
    )
    header_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (0, 0), "LEFT"),
        ("ALIGN", (1, 0), (1, 0), "CENTER"),
        ("LINEBELOW", (0, 0), (-1, 0), 1.2, colors.black),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    elementos.append(header_table)
    elementos.append(Spacer(1, 8))

    numero_box = Table([
        [Paragraph("REGISTROS", small_label_style)],
        [Paragraph(str(total_registros), small_value_style)],
    ], colWidths=[28 * mm])

    de_box = Table([
        [Paragraph("DE", small_label_style)],
        [Paragraph("Monakeratina", small_value_style)],
        [Paragraph("Sistema de gestión de datos", text_style)],
        [Paragraph("Tratamientos de alisado", text_style)],
    ], colWidths=[64 * mm])

    para_box = Table([
        [Paragraph("PARA", small_label_style)],
        [Paragraph("Reporte administrativo", small_value_style)],
        [Paragraph("Consolidado de gestiones registradas", text_style)],
    ], colWidths=[74 * mm])

    top_info = Table(
        [[numero_box, de_box, para_box]],
        colWidths=[30 * mm, 66 * mm, 76 * mm],
    )
    top_info.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEABOVE", (0, 0), (-1, -1), 1.0, colors.black),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
    ]))
    elementos.append(top_info)
    elementos.append(Spacer(1, 10))

    estado_box = Table([
        [Paragraph("ESTADO", small_label_style)],
        [Paragraph(estado_texto, small_value_style)],
    ], colWidths=[28 * mm])

    filtros_box = Table([
        [Paragraph("FILTROS", small_label_style)],
        [Paragraph(filtros_label, text_style)],
    ], colWidths=[84 * mm])

    modulo_box = Table([
        [Paragraph("MÓDULO", small_label_style)],
        [Paragraph("Gestión de Datos", small_value_style)],
    ], colWidths=[28 * mm])

    meta_table = Table(
        [[estado_box, filtros_box, modulo_box]],
        colWidths=[30 * mm, 86 * mm, 30 * mm],
    )
    meta_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEABOVE", (0, 0), (-1, -1), 1.0, colors.black),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
    ]))
    elementos.append(meta_table)
    elementos.append(Spacer(1, 10))

    table_data = [["Fecha", "Cliente", "Profesional", "Tipo de alisado", "Precio", "Saldo"]]

    for g in gestiones.order_by("-fecha_hora"):
        table_data.append([
            g.fecha_hora.strftime("%d/%m/%Y"),
            _cliente_nombre_gestion(g),
            g.procedimiento_realizado_por or "—",
            g.tipo_alisado or "—",
            _fmt_money(g.precio_alisado),
            _fmt_money(g.saldo_pendiente),
        ])

    if total_registros == 0:
        table_data.append(["No hay registros para los filtros aplicados.", "", "", "", "", ""])

    detail_table = Table(
        table_data,
        colWidths=[22 * mm, 44 * mm, 42 * mm, 42 * mm, 22 * mm, 22 * mm],
        repeatRows=1,
    )
    detail_table.setStyle(TableStyle([
        ("LINEABOVE", (0, 0), (-1, 0), 1.0, colors.black),
        ("LINEBELOW", (0, 0), (-1, 0), 0.6, colors.HexColor("#777777")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.black),
        ("ALIGN", (4, 1), (5, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("PADDING", (0, 0), (-1, -1), 6),
        ("LINEBELOW", (0, 1), (-1, -1), 0.35, colors.HexColor("#CFCFCF")),
    ]))
    elementos.append(detail_table)
    elementos.append(Spacer(1, 8))
    elementos.append(Paragraph("Generado por MonaApp / Monakeratina", footer_style))

    def _draw_fondo_gestion(canvas, doc_obj):
        page_width, page_height = A4
        canvas.saveState()
        canvas.setFillColor(colors.HexColor("#f5eee7"))
        canvas.rect(0, 0, page_width, page_height, stroke=0, fill=1)

        watermark_path = _get_watermark_path()
        if watermark_path:
            try:
                if hasattr(canvas, "setFillAlpha"):
                    canvas.setFillAlpha(0.13)
            except Exception:
                pass

            image_width = 24 * mm
            image_height = 24 * mm
            gap_x = 18 * mm
            gap_y = 18 * mm

            x = 8 * mm
            while x < page_width:
                y = 10 * mm
                while y < page_height:
                    canvas.drawImage(
                        watermark_path,
                        x,
                        y,
                        width=image_width,
                        height=image_height,
                        preserveAspectRatio=True,
                        mask="auto",
                    )
                    y += image_height + gap_y
                x += image_width + gap_x

        canvas.restoreState()

    doc.build(
        elementos,
        onFirstPage=_draw_fondo_gestion,
        onLaterPages=_draw_fondo_gestion,
    )
    buffer.seek(0)

    response = HttpResponse(buffer.read(), content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="reporte_gestion_datos.pdf"'
    return response


@login_required
def exportar_reporte_gestion_pdf_v2(request):
    gestiones = GestionAlisado.objects.select_related("cliente").all()

    buscar = request.GET.get("buscar", "")
    forma_natural = request.GET.get("forma_natural", "")
    porosidad = request.GET.get("porosidad", "")
    textura = request.GET.get("textura", "")
    estado_pago = request.GET.get("estado_pago", "")

    if buscar:
        gestiones = gestiones.filter(
            Q(cliente__nombre__icontains=buscar)
            | Q(cliente__apellido__icontains=buscar)
            | Q(procedimiento_realizado_por__icontains=buscar)
            | Q(tipo_alisado__icontains=buscar)
        )
    if forma_natural:
        gestiones = gestiones.filter(forma_natural=forma_natural)
    if porosidad:
        gestiones = gestiones.filter(porosidad=porosidad)
    if textura:
        gestiones = gestiones.filter(textura=textura)
    if estado_pago == "pagado":
        gestiones = gestiones.filter(saldo_pendiente=0)
    elif estado_pago == "pendiente":
        gestiones = gestiones.filter(saldo_pendiente__gt=0)

    def _fmt_money(value):
        try:
            return f"${int(value):,}".replace(",", ".")
        except Exception:
            return "$0"

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=16 * mm,
        leftMargin=16 * mm,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
        title="Comprobante Gestion de Datos",
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "TitleStyleGestionV2",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#2a211c"),
        alignment=1,
    )
    text_style = ParagraphStyle(
        "TextStyleGestionV2",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=9,
        leading=11,
        textColor=colors.HexColor("#2c2520"),
    )
    footer_style = ParagraphStyle(
        "FooterStyleGestionV2",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#777777"),
        alignment=1,
    )

    elementos = []
    total_registros = gestiones.count()
    estado_texto = estado_pago.title() if estado_pago else "Todos"

    filtros = []
    if buscar:
        filtros.append(f"Buscar: {buscar}")
    if forma_natural:
        filtros.append(f"Forma: {forma_natural.title()}")
    if porosidad:
        filtros.append(f"Porosidad: {porosidad.title()}")
    if textura:
        filtros.append(f"Textura: {textura.title()}")
    filtros_texto = " | ".join(filtros) if filtros else "Sin filtros"

    logo_path = _get_logo_path()
    if logo_path:
        try:
            from reportlab.platypus import Image as RLImage
            logo = RLImage(logo_path, width=34 * mm, height=25 * mm)
            logo.hAlign = "CENTER"
            elementos.append(logo)
        except Exception:
            pass

    elementos.append(Spacer(1, 4))
    elementos.append(Paragraph("Comprobante de gestion de datos", title_style))
    elementos.append(Spacer(1, 8))

    info_table = Table(
        [
            [
                Paragraph(f"<b>NUMERO</b><br/><font size='11'><b>{total_registros:04d}</b></font>", text_style),
                Paragraph("<b>DE</b><br/><b>Monakeratina</b><br/>Sistema de gestion de datos", text_style),
                Paragraph("<b>PARA</b><br/><b>Reporte administrativo</b><br/>Consolidado de gestiones", text_style),
            ],
            [
                Paragraph(f"<b>ESTADO</b><br/><b>{estado_texto}</b>", text_style),
                Paragraph("<b>MODULO</b><br/><b>Gestion de datos</b>", text_style),
                Paragraph("<b>FILTROS</b><br/>" + filtros_texto, text_style),
            ],
        ],
        colWidths=[35 * mm, 62 * mm, 83 * mm],
    )
    info_table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.7, colors.HexColor("#ccb9a9")),
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f7efe8")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    elementos.append(info_table)
    elementos.append(Spacer(1, 9))

    table_data = [["Descripcion", "Cliente", "Profesional", "Tipo de alisado", "Precio unidad", "Saldo"]]
    for g in gestiones.order_by("-fecha_hora"):
        table_data.append(
            [
                g.fecha_hora.strftime("%d/%m/%Y"),
                _cliente_nombre_gestion(g),
                g.procedimiento_realizado_por or "-",
                g.tipo_alisado or "-",
                _fmt_money(g.precio_alisado),
                _fmt_money(g.saldo_pendiente),
            ]
        )

    if total_registros == 0:
        table_data.append(["No hay registros para los filtros aplicados.", "", "", "", "", ""])

    detail_table = Table(
        table_data,
        colWidths=[24 * mm, 42 * mm, 41 * mm, 43 * mm, 20 * mm, 20 * mm],
        repeatRows=1,
    )
    detail_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e1d3c5")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#2a231f")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.7),
                ("TEXTCOLOR", (0, 1), (-1, -1), colors.HexColor("#2b2420")),
                ("ALIGN", (4, 1), (5, -1), "RIGHT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("GRID", (0, 0), (-1, -1), 0.6, colors.HexColor("#ccb9a9")),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#fbf7f2"), colors.HexColor("#f7efe8")]),
            ]
        )
    )
    elementos.append(detail_table)
    elementos.append(Spacer(1, 8))
    elementos.append(Paragraph("Generado por MonaApp / Monakeratina", footer_style))

    def _draw_fondo(canvas, doc_obj):
        page_width, page_height = A4
        canvas.saveState()
        canvas.setFillColor(colors.HexColor("#f5eee7"))
        canvas.rect(0, 0, page_width, page_height, stroke=0, fill=1)

        watermark_path = _get_watermark_path()
        if watermark_path:
            try:
                if hasattr(canvas, "setFillAlpha"):
                    canvas.setFillAlpha(0.14)
            except Exception:
                pass

            image_width = 16 * mm
            image_height = 16 * mm
            gap_x = 12 * mm
            gap_y = 12 * mm

            x = 8 * mm
            while x < page_width:
                y = 8 * mm
                while y < page_height:
                    canvas.drawImage(
                        watermark_path,
                        x,
                        y,
                        width=image_width,
                        height=image_height,
                        preserveAspectRatio=True,
                        mask="auto",
                    )
                    y += image_height + gap_y
                x += image_width + gap_x

        canvas.restoreState()

    doc.build(elementos, onFirstPage=_draw_fondo, onLaterPages=_draw_fondo)
    buffer.seek(0)

    response = HttpResponse(buffer.read(), content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="reporte_gestion_datos.pdf"'
    return response
