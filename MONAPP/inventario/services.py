from django.db import transaction, IntegrityError
from django.core.exceptions import ValidationError
from .models import Stock, MovimientoStock


def aplicar_movimiento_stock(
    *,
    producto,
    delta,
    tipo_movimiento,
    usuario=None,
    compra=None,
    devolucion=None,
    observacion=""
):
    if delta == 0:
        return Stock.objects.filter(producto=producto).first()

    try:
        stock_obj, _ = Stock.objects.get_or_create(
            producto=producto,
            defaults={"cantidad_actual": 0}
        )
    except IntegrityError:
        stock_obj = Stock.objects.get(producto=producto)

    stock_obj = Stock.objects.select_for_update().get(pk=stock_obj.pk)

    stock_anterior = stock_obj.cantidad_actual or 0
    stock_posterior = stock_anterior + delta

    if stock_posterior < 0:
        raise ValidationError(
            f"El stock no puede quedar negativo para {producto.nombre}. "
            f"Actual: {stock_anterior}, movimiento: {delta}."
        )

    stock_obj.cantidad_actual = stock_posterior
    stock_obj.save(update_fields=["cantidad_actual", "actualizado_en"])

    MovimientoStock.objects.create(
        producto=producto,
        stock=stock_obj,
        tipo_movimiento=tipo_movimiento,
        cantidad=delta,
        stock_anterior=stock_anterior,
        stock_posterior=stock_posterior,
        usuario=usuario,
        compra=compra,
        devolucion=devolucion,
        observacion=observacion,
    )

    return stock_obj