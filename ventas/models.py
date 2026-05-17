from django.db import models
from django.db.models import Sum
from django.utils.timezone import now
from clientes.models import Cliente
from Productos.models import Producto
from servicios.models import Servicio


class Venta(models.Model):
    codigo_venta = models.CharField(max_length=10, unique=True, editable=False)
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name="ventas")
    codigo_producto = models.CharField(max_length=50, verbose_name="Código producto / servicio")
    codigo_colaborador = models.CharField(max_length=20, verbose_name="Código colaborador")
    nombre_colaborador = models.CharField(max_length=150, verbose_name="Nombre colaborador")
    fecha = models.DateTimeField(default=now)

    ESTADOS = [
        ('activa', 'Activa'),
        ('anulada', 'Anulada'),
    ]
    estado = models.CharField(max_length=10, choices=ESTADOS, default='activa')

    class Meta:
        verbose_name = "Venta"
        verbose_name_plural = "Ventas"
        ordering = ["-fecha"]

    def save(self, *args, **kwargs):
        if not self.codigo_venta:
            ultima = Venta.objects.order_by("-id").first()
            numero = (int(ultima.codigo_venta.replace("V", "")) + 1) if ultima else 1
            self.codigo_venta = f"V{numero:05d}"
        super().save(*args, **kwargs)

    @property
    def total(self):
        return self.detalles.aggregate(total=Sum("subtotal"))["total"] or 0

    @property
    def total_devuelto(self):
        from django.apps import apps
        DetalleDevolucion = apps.get_model("ventas", "DetalleDevolucion")
        return (
            DetalleDevolucion.objects
            .filter(detalle_venta__venta=self)
            .aggregate(total=Sum("subtotal_devuelto"))["total"] or 0
        )

    @property
    def tiene_devoluciones(self):
        from django.apps import apps
        DetalleDevolucion = apps.get_model("ventas", "DetalleDevolucion")
        return DetalleDevolucion.objects.filter(detalle_venta__venta=self).exists()

    def __str__(self):
        return f"{self.codigo_venta} - {self.cliente}"


class DetalleVenta(models.Model):
    venta = models.ForeignKey(Venta, on_delete=models.CASCADE, related_name='detalles')
    producto = models.ForeignKey("Productos.Producto", on_delete=models.PROTECT, null=True, blank=True)
    servicio = models.ForeignKey(Servicio, on_delete=models.PROTECT, null=True, blank=True)
    colaborador_servicio = models.ForeignKey(
        "personal.Personal", on_delete=models.CASCADE,
        null=True, blank=True, related_name="detalles_ventas_servicio"
    )
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=2)
    cantidad = models.PositiveIntegerField(default=1)
    subtotal = models.DecimalField(max_digits=14, decimal_places=2)

    @property
    def cantidad_devuelta(self):
        return self.devoluciones.aggregate(total=Sum("cantidad_devuelta"))["total"] or 0

    @property
    def cantidad_disponible_devolver(self):
        return self.cantidad - self.cantidad_devuelta

    def __str__(self):
        return f"{self.producto} x {self.cantidad}"


# ============================================================
# DEVOLUCIÓN
# ============================================================

class DevolucionVenta(models.Model):
    codigo_devolucion = models.CharField(max_length=12, unique=True, editable=False)
    venta = models.ForeignKey(Venta, on_delete=models.PROTECT, related_name="devoluciones")
    fecha = models.DateTimeField(default=now)
    motivo = models.TextField(verbose_name="Motivo de devolución")
    total_devuelto = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    class Meta:
        verbose_name = "Devolución de venta"
        verbose_name_plural = "Devoluciones de ventas"
        ordering = ["-fecha"]

    def save(self, *args, **kwargs):
        if not self.codigo_devolucion:
            ultima = DevolucionVenta.objects.order_by("-id").first()
            numero = (int(ultima.codigo_devolucion.replace("DEV", "")) + 1) if ultima else 1
            self.codigo_devolucion = f"DEV{numero:05d}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.codigo_devolucion} -> {self.venta.codigo_venta}"


class DetalleDevolucion(models.Model):
    devolucion = models.ForeignKey(DevolucionVenta, on_delete=models.CASCADE, related_name="detalles")
    detalle_venta = models.ForeignKey(DetalleVenta, on_delete=models.PROTECT, related_name="devoluciones")
    cantidad_devuelta = models.PositiveIntegerField()
    subtotal_devuelto = models.DecimalField(max_digits=14, decimal_places=2)

    def __str__(self):
        return f"{self.devolucion.codigo_devolucion} - línea {self.detalle_venta_id}"