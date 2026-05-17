from django.contrib import admin

from .models import BaseDiariaCuenta, BitacoraFondos, CuentaFinanciera, JornadaDiaria, MovimientoCuenta, TransferenciaCuenta


@admin.register(CuentaFinanciera)
class CuentaFinancieraAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre", "tipo", "activa", "orden_visual")
    list_filter = ("tipo", "activa")
    search_fields = ("codigo", "nombre", "nombre_normalizado")
    ordering = ("orden_visual", "nombre")


@admin.register(JornadaDiaria)
class JornadaDiariaAdmin(admin.ModelAdmin):
    list_display = ("fecha", "sede", "estado", "responsable_apertura", "usuario_cierre", "fecha_creacion", "fecha_cierre")
    list_filter = ("estado", "fecha")
    search_fields = ("fecha",)


@admin.register(BaseDiariaCuenta)
class BaseDiariaCuentaAdmin(admin.ModelAdmin):
    list_display = ("jornada", "cuenta", "base_inicial", "registrada_por", "fecha_registro")
    list_filter = ("jornada__fecha", "cuenta")
    search_fields = ("cuenta__nombre", "observacion")


@admin.register(MovimientoCuenta)
class MovimientoCuentaAdmin(admin.ModelAdmin):
    list_display = ("id", "jornada", "cuenta", "tipo", "clase", "tipo_movimiento", "valor", "estado", "estado_validacion", "fecha_hora")
    list_filter = ("tipo", "clase", "tipo_movimiento", "estado", "estado_validacion", "jornada__fecha", "cuenta")
    search_fields = ("concepto", "procedimiento", "producto_servicio", "referencia", "comprobante", "request_uid")
    autocomplete_fields = ("compra", "servicio", "movimiento_origen")


@admin.register(TransferenciaCuenta)
class TransferenciaCuentaAdmin(admin.ModelAdmin):
    list_display = ("id", "cuenta_origen", "cuenta_destino", "valor", "estado", "usuario", "fecha_hora")
    list_filter = ("estado", "cuenta_origen", "cuenta_destino")


@admin.register(BitacoraFondos)
class BitacoraFondosAdmin(admin.ModelAdmin):
    list_display = ("fecha_hora", "accion", "modelo", "objeto_id", "usuario")
    list_filter = ("accion", "modelo", "fecha_hora")
    search_fields = ("accion", "modelo", "objeto_id", "motivo")
