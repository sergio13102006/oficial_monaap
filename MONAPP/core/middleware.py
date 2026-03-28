from django.conf import settings
from django.http import HttpResponseForbidden
from django.shortcuts import redirect, resolve_url, render

from .permisos import (
    PUBLIC_USER_URLS,
    USER_PROFILE_URLS,
    accion_desde_url,
    permisos_para_modulo,
    tiene_rol,
)


RUTAS_ADMIN_PUBLICAS = {
    "admin",
}

MODULOS_PROTEGIDOS = {
    "productos",
    "proveedores",
    "clientes",
    "ventas",
    "personal",
    "inventario",
    "compras",
    "servicios",
    "productos_web",
    "promociones",
    "servicios_web",
    "usuarios",
    "notificaciones",
    "backup",
    "gestion_alisados",
}


class RolePermissionMiddleware:
    """Aplica la matriz de permisos por rol definida para el proyecto."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        path = (request.path_info or "").lower()
        resolver = getattr(request, "resolver_match", None)
        # Si no hay coincidencia de URL, dejar que Django resuelva el 404.
        if resolver is None:
            return None
        namespace = getattr(resolver, "namespace", "") or ""
        url_name = getattr(resolver, "url_name", "") or ""

        if path.startswith((settings.STATIC_URL.lower(), settings.MEDIA_URL.lower())):
            return None

        if namespace in RUTAS_ADMIN_PUBLICAS or path.startswith("/admin/"):
            return None

        # Rutas pÃºblicas (no requieren sesiÃ³n)
        if namespace == "core" and url_name == "index":
            return None

        if namespace == "usuarios" and (url_name in PUBLIC_USER_URLS or url_name == "logout"):
            return None

        if not getattr(request.user, "is_authenticated", False):
            login_url = resolve_url(settings.LOGIN_URL)
            return redirect(f"{login_url}?next={request.get_full_path()}")

        if namespace == "usuarios" and url_name in USER_PROFILE_URLS:
            return None

        modulo = namespace
        if modulo not in MODULOS_PROTEGIDOS:
            return None

        accion = accion_desde_url(url_name)
        roles_permitidos = permisos_para_modulo(modulo, accion)

        if roles_permitidos is None:
            return None

        if tiene_rol(request.user, *roles_permitidos):
            return None

        return HttpResponseForbidden("No tienes permisos para realizar esta acción.")


class Pretty404Middleware:
    """
    Renderiza una página 404 personalizada incluso con DEBUG=True.

    En modo debug Django muestra la página técnica de 404 y no usa `handler404`.
    Este middleware intercepta respuestas 404 (HTML) y devuelve `templates/404.html`.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if getattr(response, "status_code", None) != 404:
            return response

        path = (request.path_info or "").lower()
        if path.startswith((settings.STATIC_URL.lower(), settings.MEDIA_URL.lower())):
            return response

        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return response

        accept = (request.headers.get("accept") or "").lower()
        if accept and ("text/html" not in accept and "*/*" not in accept):
            return response

        try:
            return render(request, "404.html", status=404)
        except Exception:
            return response


class SecurityHeadersMiddleware:
    """
    Cabeceras defensivas adicionales.

    Nota: se evitan políticas CSP estrictas porque el proyecto usa scripts/estilos inline
    y recursos CDN; una CSP estricta rompería la UI. Aun así, esto añade hardening útil.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        response.headers.setdefault(
            "Permissions-Policy",
            "camera=(), microphone=(), geolocation=(), payment=(), usb=(), "
            "accelerometer=(), gyroscope=(), magnetometer=()",
        )
        response.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
        response.headers.setdefault("Cross-Origin-Resource-Policy", "same-site")
        response.headers.setdefault("X-Permitted-Cross-Domain-Policies", "none")

        return response
