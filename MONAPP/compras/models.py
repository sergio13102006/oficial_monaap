from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from Proveedores.models import Proveedor
from Productos.models import Producto


class Compra(models.Model):
    fecha = models.DateField(auto_now_add=True)
    fecha_anulada = models.DateField(null=True, blank=True)
    proveedor = models.ForeignKey(
        Proveedor,
        on_delete=models.PROTECT,
        related_name="compras",
    )
    precio_total = models.DecimalField(max_digits=18, decimal_places=0)

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    anulada = models.BooleanField(default=False)
    anulada_en = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(precio_total__gte=0),
                name="compras_compra_precio_total_no_negativo",
            ),
        ]

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Compra #{self.id} - {self.proveedor.nombre_proveedor}"


class DetalleCompra(models.Model):
    compra = models.ForeignKey(
        Compra,
        on_delete=models.PROTECT,
        related_name="detalles",
    )

    producto = models.ForeignKey(
        Producto,
        on_delete=models.PROTECT,
        related_name="detalles_compra",
    )

    cantidad = models.IntegerField()
    precio_unitario = models.DecimalField(max_digits=16, decimal_places=0)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(cantidad__gt=0),
                name="compras_detallecompra_cantidad_mayor_cero",
            ),
            models.CheckConstraint(
                condition=models.Q(precio_unitario__gt=0),
                name="compras_detallecompra_precio_unitario_mayor_cero",
            ),
        ]

    def clean(self):
        super().clean()

        if self.cantidad is None or self.precio_unitario is None or self.producto_id is None:
            return

        if self.cantidad <= 0:
            raise ValidationError({"cantidad": _("La cantidad debe ser mayor que 0.")})

        if self.precio_unitario <= 0:
            raise ValidationError({"precio_unitario": _("El precio unitario debe ser mayor que 0.")})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.producto.nombre} x {self.cantidad}"

    @property
    def subtotal(self):
        return (self.cantidad or 0) * (self.precio_unitario or 0)


class DevolucionCompra(models.Model):
    fecha = models.DateField(auto_now_add=True)

    compra = models.ForeignKey(
        Compra,
        on_delete=models.PROTECT,
        related_name="devoluciones",
    )

    proveedor = models.ForeignKey(
        Proveedor,
        on_delete=models.PROTECT,
        related_name="devoluciones_compra",
    )

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    motivo = models.CharField(max_length=150, blank=True)
    observacion = models.TextField(blank=True)

    total = models.DecimalField(max_digits=18, decimal_places=0, default=0)

    anulada = models.BooleanField(default=False)
    fecha_anulada = models.DateField(null=True, blank=True)
    anulada_en = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(total__gte=0),
                name="compras_devolucioncompra_total_no_negativo",
            ),
        ]

    def clean(self):
        super().clean()

        errores = {}

        if self.compra_id and self.proveedor_id:
            compra_proveedor_id = getattr(self.compra, "proveedor_id", None)
            if compra_proveedor_id is None:
                compra_proveedor_id = (
                    Compra.objects.filter(pk=self.compra_id)
                    .values_list("proveedor_id", flat=True)
                    .first()
                )

            if compra_proveedor_id and self.proveedor_id != compra_proveedor_id:
                errores["proveedor"] = _(
                    "El proveedor de la devolucion debe coincidir con el proveedor de la compra."
                )

        if self.total is not None and self.total < 0:
            errores["total"] = _("El total de la devolucion no puede ser negativo.")

        if errores:
            raise ValidationError(errores)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Devolucion compra #{self.id} - Compra #{self.compra.id}"


class DetalleDevolucionCompra(models.Model):
    devolucion = models.ForeignKey(
        DevolucionCompra,
        on_delete=models.PROTECT,
        related_name="detalles",
    )

    detalle_compra = models.ForeignKey(
        DetalleCompra,
        on_delete=models.PROTECT,
        related_name="detalles_devolucion",
    )

    producto = models.ForeignKey(
        Producto,
        on_delete=models.PROTECT,
        related_name="detalles_devolucion_compra",
    )

    cantidad = models.IntegerField()
    precio_unitario = models.DecimalField(max_digits=16, decimal_places=0)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(cantidad__gt=0),
                name="compras_detalledevolucioncompra_cantidad_mayor_cero",
            ),
            models.CheckConstraint(
                condition=models.Q(precio_unitario__gt=0),
                name="compras_detalledevolucioncompra_precio_unitario_mayor_cero",
            ),
        ]

    def clean(self):
        super().clean()

        errores = {}

        if self.cantidad is not None and self.cantidad <= 0:
            errores["cantidad"] = _("La cantidad debe ser mayor que 0.")

        if self.precio_unitario is not None and self.precio_unitario <= 0:
            errores["precio_unitario"] = _("El precio unitario debe ser mayor que 0.")

        if self.detalle_compra_id and self.producto_id:
            detalle_producto_id = getattr(self.detalle_compra, "producto_id", None)
            if detalle_producto_id is None:
                detalle_producto_id = (
                    DetalleCompra.objects.filter(pk=self.detalle_compra_id)
                    .values_list("producto_id", flat=True)
                    .first()
                )

            if detalle_producto_id and self.producto_id != detalle_producto_id:
                errores["producto"] = _(
                    "El producto de la devolucion debe coincidir con el producto del detalle de compra."
                )

        if self.devolucion_id and self.detalle_compra_id:
            compra_devolucion_id = getattr(self.devolucion, "compra_id", None)
            detalle_compra_compra_id = getattr(self.detalle_compra, "compra_id", None)

            if compra_devolucion_id is None:
                compra_devolucion_id = (
                    DevolucionCompra.objects.filter(pk=self.devolucion_id)
                    .values_list("compra_id", flat=True)
                    .first()
                )

            if detalle_compra_compra_id is None:
                detalle_compra_compra_id = (
                    DetalleCompra.objects.filter(pk=self.detalle_compra_id)
                    .values_list("compra_id", flat=True)
                    .first()
                )

            if (
                compra_devolucion_id
                and detalle_compra_compra_id
                and compra_devolucion_id != detalle_compra_compra_id
            ):
                errores["detalle_compra"] = _(
                    "El detalle de compra debe pertenecer a la misma compra de la devolucion."
                )

        if errores:
            raise ValidationError(errores)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.producto.nombre} x {self.cantidad}"

    @property
    def subtotal(self):
        return (self.cantidad or 0) * (self.precio_unitario or 0)
