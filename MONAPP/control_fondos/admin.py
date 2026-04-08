from django.contrib import admin

from .models import BaseDiariaCuenta, CuentaFinanciera, JornadaDiaria, MovimientoCuenta, TransferenciaCuenta


@admin.register(CuentaFinanciera)
class CuentaFinancieraAdmin(admin.ModelAdmin):
    list_display = ("nombre", "tipo", "activa", "orden_visual")
    list_filter = ("tipo", "activa")
    search_fields = ("nombre",)
    ordering = ("orden_visual", "nombre")


@admin.register(JornadaDiaria)
class JornadaDiariaAdmin(admin.ModelAdmin):
    list_display = ("fecha", "estado", "creada_por", "fecha_creacion", "fecha_cierre_auto")
    list_filter = ("estado", "fecha")
    search_fields = ("fecha",)


@admin.register(BaseDiariaCuenta)
class BaseDiariaCuentaAdmin(admin.ModelAdmin):
    list_display = ("jornada", "cuenta", "base_inicial", "registrada_por", "fecha_registro")
    list_filter = ("jornada__fecha", "cuenta")
    search_fields = ("cuenta__nombre", "observacion")


@admin.register(MovimientoCuenta)
class MovimientoCuentaAdmin(admin.ModelAdmin):
    list_display = ("id", "jornada", "cuenta", "tipo", "clase", "valor", "estado", "fecha_hora")
    list_filter = ("tipo", "clase", "estado", "jornada__fecha", "cuenta")
    search_fields = ("concepto", "referencia", "request_uid")
    autocomplete_fields = ("compra", "servicio", "movimiento_origen")


@admin.register(TransferenciaCuenta)
class TransferenciaCuentaAdmin(admin.ModelAdmin):
    list_display = ("id", "cuenta_origen", "cuenta_destino", "valor", "usuario", "fecha_hora")
    list_filter = ("cuenta_origen", "cuenta_destino")
