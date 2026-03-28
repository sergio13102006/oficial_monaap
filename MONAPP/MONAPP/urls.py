"""
URL configuration for MONAPP project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from core import views as core_views

handler404 = "core.views.handler404"

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls')),
    path('auth/', include('usuarios.urls')),
    path('Productos/', include('Productos.urls')),
    path('Proveedores/', include('Proveedores.urls')),
    path('clientes/', include('clientes.urls')),
    path('ventas/', include('ventas.urls')),
    path('personal/', include('personal.urls')),
    path('inventario/', include('inventario.urls')),
    path('servicios/', include('servicios.urls')),
    path('gestion-alisados/', include('gestion_alisados.urls')),
    path('productos-web/', include('productos_web.urls')),
    path("compras/", include("compras.urls")),
    path('promociones/', include('promociones.urls')),
    path('servicios_web/', include('servicios_web.urls')),
    path('notificaciones/', include('notificaciones.urls')),
    path('backup/', include('backup.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Catch-all al final: permite mostrar el 404 personalizado aun con DEBUG=True
urlpatterns += [
    re_path(r"^.*$", core_views.pretty_404_view, name="pretty_404"),
]
