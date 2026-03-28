from datetime import date
from pathlib import Path

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.conf import settings
from django.http import FileResponse, JsonResponse
from django.shortcuts import redirect, render
from django.db.models import Sum

from usuarios.forms import LoginForm

from clientes.models import Cliente
from servicios.models import Servicio
from promociones.models import Promocion
from productos_web.models import ProductoWeb


def index(request):
    show_login_modal = request.GET.get("login") == "1" or bool(request.GET.get("next"))

    if request.method == "POST":
        form = LoginForm(request, data=request.POST)

        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect(request.POST.get("next") or "core:dashboard")

        messages.error(request, "Usuario o contraseña incorrectos.")
        show_login_modal = True

    servicios = Servicio.objects.filter(activo=True)
    promociones = Promocion.objects.filter(activa=True)
    productos_web = ProductoWeb.objects.filter(visible=True)

    return render(
        request,
        "core/index.html",
        {
            "show_login_modal": show_login_modal,
            "servicios": servicios,
            "promociones": promociones,
            "productos_web": productos_web,
        },
    )


def handler404(request, exception):
    return render(request, "404.html", status=404)


def pretty_404_view(request, *args, **kwargs):
    """Fallback para mostrar el 404 personalizado incluso con DEBUG=True."""
    return render(request, "404.html", status=404)


@login_required
def dashboard_view(request):
    hoy = date.today()
    mes_actual = hoy.month
    anio_actual = hoy.year

    # ── KPIs ────────────────────────────────────────────────────────────────
    total_usuarios = User.objects.count()
    usuarios_activos = User.objects.filter(is_active=True).count()
    nuevos_usuarios_mes = User.objects.filter(
        date_joined__month=mes_actual, date_joined__year=anio_actual
    ).count()

    try:
        from Productos.models import Producto

        total_productos = Producto.objects.filter(activo=True).count()
    except Exception:
        total_productos = 0

    try:
        total_clientes = Cliente.objects.count()
    except Exception:
        total_clientes = 0

    try:
        from ventas.models import Venta

        total_ventas = Venta.objects.filter(estado="activa").count()
    except Exception:
        total_ventas = 0

    try:
        from inventario.models import Stock

        productos_sin_stock = Stock.objects.filter(cantidad_actual__lte=0).count()
    except Exception:
        productos_sin_stock = 0

    # ── Total montos ventas y compras (para la gráfica) ─────────────────────
    total_monto_ventas = 0
    try:
        from ventas.models import DetalleVenta

        total_monto_ventas = (
            DetalleVenta.objects.filter(venta__estado="activa").aggregate(t=Sum("subtotal"))[
                "t"
            ]
            or 0
        )
    except Exception:
        pass

    total_monto_compras = 0
    total_compras_count = 0
    try:
        from compras.models import Compra as CompraModel

        compras_qs = CompraModel.objects.filter(anulada=False)
        total_monto_compras = compras_qs.aggregate(t=Sum("precio_total"))["t"] or 0
        total_compras_count = compras_qs.count()
    except Exception:
        pass

    # ── Cumpleaños hoy (clientes) ───────────────────────────────────────────
    cumpleanios_hoy = []
    try:
        clientes_bday = Cliente.objects.filter(
            fecha_nacimiento__day=hoy.day, fecha_nacimiento__month=hoy.month
        )
        for c in clientes_bday:
            edad = hoy.year - c.fecha_nacimiento.year
            nombre = (
                f"{c.nombre} {c.apellido}"
                if hasattr(c, "apellido")
                else getattr(c, "nombre", str(c))
            )
            cumpleanios_hoy.append({"nombre": nombre, "cargo": "Cliente", "edad": edad})
    except Exception:
        pass

    # ── Productos críticos (stock ≤ 5) ──────────────────────────────────────
    productos_criticos = []
    try:
        from inventario.models import Stock

        stocks_criticos = (
            Stock.objects.filter(cantidad_actual__lte=5)
            .select_related("producto")
            .order_by("cantidad_actual")[:8]
        )

        for s in stocks_criticos:
            porcentaje = (
                min(int((s.cantidad_actual / 5) * 100), 100) if s.cantidad_actual > 0 else 0
            )
            productos_criticos.append(
                {
                    "nombre": s.producto.nombre,
                    "cantidad": s.cantidad_actual,
                    "porcentaje": porcentaje,
                }
            )
    except Exception:
        pass

    # ── Últimos usuarios ────────────────────────────────────────────────────
    ultimos_usuarios = User.objects.prefetch_related("groups").order_by("-date_joined")[:5]

    # ── Últimas ventas ──────────────────────────────────────────────────────
    ultimas_ventas = []
    try:
        from ventas.models import Venta

        ultimas_ventas = Venta.objects.select_related("cliente").order_by("-fecha")[:5]
    except Exception:
        pass

    # ── Últimas compras ─────────────────────────────────────────────────────
    ultimas_compras = []
    try:
        from compras.models import Compra

        ultimas_compras = Compra.objects.select_related("proveedor").order_by("-fecha")[:5]
    except Exception:
        pass

    return render(
        request,
        "core/dashboard.html",
        {
            # KPIs
            "total_productos": total_productos,
            "total_clientes": total_clientes,
            "total_ventas": total_ventas,
            "productos_sin_stock": productos_sin_stock,
            "total_usuarios": total_usuarios,
            "usuarios_activos": usuarios_activos,
            "nuevos_usuarios_mes": nuevos_usuarios_mes,
            # Gráfica ventas vs compras
            "total_monto_ventas": total_monto_ventas,
            "total_monto_compras": total_monto_compras,
            "total_compras_count": total_compras_count,
            # Cards
            "cumpleanios_hoy": cumpleanios_hoy,
            "productos_criticos": productos_criticos,
            "ultimos_usuarios": ultimos_usuarios,
            "ultimas_ventas": ultimas_ventas,
            "ultimas_compras": ultimas_compras,
        },
    )


@login_required
def gestion_datos_view(request):
    if request.method == "POST":
        try:
            nombre = request.POST.get("nombre")
            categoria = request.POST.get("categoria")
            descripcion = request.POST.get("descripcion")
            fecha = request.POST.get("fecha")
            estado = request.POST.get("estado")

            _ = (nombre, categoria, descripcion, fecha, estado)
            return JsonResponse({"success": True, "message": "Datos guardados correctamente"})
        except Exception as e:
            return JsonResponse({"success": False, "message": str(e)}, status=400)

    return render(request, "core/gestion_datos.html", {"titulo": "Gestión de Datos"})


@login_required
def ayuda_view(request):
    documentos = [
        {
            "titulo": "Manual MONAPP",
            "descripcion": "Documento principal del sistema.",
            "icono": "bi-journal-bookmark-fill",
            "archivo": "core/docs/ayuda/monapp.pdf",
        },
        {
            "titulo": "Manual de usuario (Personal y aliados)",
            "descripcion": "Gestión de personal, proveedores y clientes.",
            "icono": "bi-people-fill",
            "archivo": "core/docs/ayuda/manual_personal_y_aliados.pdf",
        },
        {
            "titulo": "Manual de usuario (Productos, ventas y servicios)",
            "descripcion": "Operación diaria: productos, ventas y servicios.",
            "icono": "bi-bag-check-fill",
            "archivo": "core/docs/ayuda/manual_productos_ventas_y_servicios.pdf",
        },
        {
            "titulo": "Catálogo",
            "descripcion": "Catálogo general en PDF.",
            "icono": "bi-journals",
            "archivo": "core/docs/ayuda/catalogo.pdf",
        },
        {
            "titulo": "Copia de seguridad (Base de datos)",
            "descripcion": "Guía/archivo relacionado con backups de la BD.",
            "icono": "bi-shield-lock-fill",
            "archivo": "core/docs/ayuda/copia_seguridad_base_datos.pdf",
        },
        {
            "titulo": "MONAPP (copia)",
            "descripcion": "Documento adicional (copia).",
            "icono": "bi-files",
            "archivo": "core/docs/ayuda/monapp_copia.pdf",
        },
    ]

    documento_principal = documentos[0] if documentos else None

    return render(
        request,
        "core/ayuda.html",
        {"documentos": documentos, "documento_principal": documento_principal},
    )


@login_required
def ayuda_pdf_view(request):
    pdf_path = Path(settings.BASE_DIR) / "core" / "static" / "core" / "docs" / "ayuda" / "monapp.pdf"
    return FileResponse(
        pdf_path.open("rb"),
        content_type="application/pdf",
        as_attachment=True,
        filename="manual_usuario_monapp.pdf",
    )


def solo_admin(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_staff:
            messages.error(request, "No tienes permisos para realizar esta acción.")
            return redirect("core:dashboard")
        return view_func(request, *args, **kwargs)

    return wrapper

