from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from Productos.models import Producto
from compras.models import Compra, DetalleCompra, DevolucionCompra
from inventario.services import aplicar_movimiento_stock


MAX_CANTIDAD_COMPRA_SERVICIO = 1000000


class CompraServiceError(Exception):
    pass


def _validar_proveedor_activo(proveedor):
    proveedor_db = (
        proveedor.__class__.objects
        .select_for_update()
        .get(pk=proveedor.pk)
    )

    if getattr(proveedor_db, "estado", None) != "activo":
        raise CompraServiceError(
            "Solo puedes registrar compras con proveedores activos."
        )

    return proveedor_db


def _extraer_lineas_compra_validas(formset):
    lineas = []
    productos_vistos = set()

    for form in formset.forms:
        if not getattr(form, "cleaned_data", None):
            continue

        if form.cleaned_data.get("DELETE"):
            continue

        producto_post = form.cleaned_data.get("producto")
        cantidad = form.cleaned_data.get("cantidad")
        precio_unitario = form.cleaned_data.get("precio_unitario")

        fila_vacia = not producto_post and not cantidad and not precio_unitario
        if fila_vacia:
            continue

        if not producto_post:
            raise CompraServiceError("Hay filas de compra incompletas o inválidas.")

        try:
            producto = Producto.objects.select_for_update().get(pk=producto_post.pk)
        except Producto.DoesNotExist as exc:
            raise CompraServiceError("Se detectó un producto inválido en la compra.") from exc

        permitir_producto_inactivo_existente = bool(
            getattr(form.instance, "pk", None) and form.instance.producto_id == producto.pk
        )

        if not producto.activo and not permitir_producto_inactivo_existente:
            raise CompraServiceError(
                f"El producto {producto.nombre} no está activo para compras."
            )

        if cantidad is None or cantidad <= 0:
            raise CompraServiceError(
                f"La cantidad del producto {producto.nombre} debe ser mayor que 0."
            )

        if cantidad > MAX_CANTIDAD_COMPRA_SERVICIO:
            raise CompraServiceError(
                f"La cantidad del producto {producto.nombre} supera el máximo permitido."
            )

        if precio_unitario is None or precio_unitario <= 0:
            raise CompraServiceError(
                f"El precio unitario del producto {producto.nombre} debe ser mayor que 0."
            )

        if producto.pk in productos_vistos:
            raise CompraServiceError(
                f"No puedes repetir el producto {producto.nombre} en la misma compra."
            )

        productos_vistos.add(producto.pk)

        lineas.append({
            "detalle_id": getattr(form.instance, "pk", None),
            "producto": producto,
            "cantidad": cantidad,
            "precio_unitario": precio_unitario,
        })

    if not lineas:
        raise CompraServiceError("Debes agregar al menos un producto a la compra.")

    return lineas


def _extraer_lineas_devolucion_validas(compra, formset):
    lineas = []
    acumulado_por_detalle = {}

    for form in formset.forms:
        if not getattr(form, "cleaned_data", None):
            continue

        if form.cleaned_data.get("DELETE"):
            continue

        detalle_post = form.cleaned_data.get("detalle_compra")
        cantidad = form.cleaned_data.get("cantidad") or 0

        fila_vacia = not detalle_post and not cantidad
        if fila_vacia:
            continue

        if not detalle_post or cantidad <= 0:
            raise CompraServiceError("Hay filas de devolución incompletas o inválidas.")

        try:
            detalle_compra = (
                compra.detalles
                .select_for_update()
                .select_related("producto")
                .get(pk=detalle_post.pk)
            )
        except compra.detalles.model.DoesNotExist as exc:
            raise CompraServiceError(
                "Se detectó un detalle de compra inválido para la devolución."
            ) from exc

        cantidad_ya_devuelta = (
            detalle_compra.detalles_devolucion
            .filter(devolucion__anulada=False)
            .aggregate(total=Sum("cantidad"))["total"] or 0
        )

        acumulado_por_detalle[detalle_compra.pk] = (
            acumulado_por_detalle.get(detalle_compra.pk, 0) + cantidad
        )

        disponible_por_compra = max(
            (detalle_compra.cantidad or 0) - cantidad_ya_devuelta,
            0,
        )
        stock_actual = detalle_compra.producto.stock_actual or 0
        disponible_para_devolver = min(disponible_por_compra, stock_actual)

        if acumulado_por_detalle[detalle_compra.pk] > disponible_para_devolver:
            raise CompraServiceError(
                f"Solo puedes devolver hasta {disponible_para_devolver} unidad(es) de {detalle_compra.producto.nombre}."
            )

        lineas.append((detalle_compra, cantidad))

    if not lineas:
        raise CompraServiceError("Debes agregar al menos un producto a devolver.")

    return lineas


def _extraer_lineas_devolucion_bloqueadas(compra, formset):
    lineas = []
    acumulado_por_detalle = {}
    detalles_bloqueados = {}
    devoluciones_bloqueadas = {}

    for form in formset.forms:
        if not getattr(form, "cleaned_data", None):
            continue

        if form.cleaned_data.get("DELETE"):
            continue

        detalle_post = form.cleaned_data.get("detalle_compra")
        cantidad = form.cleaned_data.get("cantidad") or 0

        fila_vacia = not detalle_post and not cantidad
        if fila_vacia:
            continue

        if not detalle_post or cantidad <= 0:
            raise CompraServiceError("Hay filas de devolución incompletas o inválidas.")

        detalle_id = detalle_post.pk

        if detalle_id not in detalles_bloqueados:
            try:
                detalle_compra = (
                    compra.detalles
                    .select_for_update()
                    .select_related("producto")
                    .get(pk=detalle_id)
                )
            except compra.detalles.model.DoesNotExist as exc:
                raise CompraServiceError(
                    "Se detectó un detalle de compra inválido para la devolución."
                ) from exc

            if detalle_compra.compra_id != compra.pk:
                raise CompraServiceError(
                    "Ese detalle no pertenece a la compra seleccionada."
                )

            detalles_bloqueados[detalle_id] = detalle_compra
            devoluciones_bloqueadas[detalle_id] = list(
                detalle_compra.detalles_devolucion
                .select_for_update()
                .filter(devolucion__anulada=False)
            )

        detalle_compra = detalles_bloqueados[detalle_id]
        cantidad_ya_devuelta = sum(
            (item.cantidad or 0)
            for item in devoluciones_bloqueadas[detalle_id]
        )

        acumulado_por_detalle[detalle_id] = (
            acumulado_por_detalle.get(detalle_id, 0) + cantidad
        )

        disponible_por_compra = max(
            (detalle_compra.cantidad or 0) - cantidad_ya_devuelta,
            0,
        )
        stock_actual = detalle_compra.producto.stock_actual or 0
        disponible_para_devolver = min(disponible_por_compra, stock_actual)

        if acumulado_por_detalle[detalle_id] > disponible_para_devolver:
            raise CompraServiceError(
                f"Solo puedes devolver hasta {disponible_para_devolver} unidad(es) de {detalle_compra.producto.nombre}."
            )

        lineas.append((detalle_compra, cantidad))

    if not lineas:
        raise CompraServiceError("Debes agregar al menos un producto a devolver.")

    return lineas


def validar_compra_editable(compra):
    if compra.devoluciones.filter(anulada=False).exists():
        raise CompraServiceError("No se puede editar una compra con devoluciones activas.")

    if compra.anulada:
        raise CompraServiceError("No se puede editar una compra anulada.")


def registrar_compra(*, form, formset, usuario):
    with transaction.atomic():
        compra = form.save(commit=False)
        compra.proveedor = _validar_proveedor_activo(compra.proveedor)

        lineas = _extraer_lineas_compra_validas(formset)

        total = sum(
            (linea["cantidad"] or 0) * (linea["precio_unitario"] or 0)
            for linea in lineas
        )

        compra.usuario = usuario
        compra.precio_total = total
        compra.save()

        for linea in lineas:
            detalle = DetalleCompra.objects.create(
                compra=compra,
                producto=linea["producto"],
                cantidad=linea["cantidad"],
                precio_unitario=linea["precio_unitario"],
            )

            aplicar_movimiento_stock(
                producto=detalle.producto,
                delta=(detalle.cantidad or 0),
                tipo_movimiento="COMPRA_ENTRADA",
                usuario=usuario,
                compra=compra,
                observacion=f"Registro de compra #{compra.id}"
            )

    return compra


def editar_compra(*, compra, form, formset, usuario):
    with transaction.atomic():
        compra = Compra.objects.select_for_update().get(pk=compra.pk)
        validar_compra_editable(compra)

        compra_editada = form.save(commit=False)
        compra_editada.proveedor = _validar_proveedor_activo(compra_editada.proveedor)

        lineas = _extraer_lineas_compra_validas(formset)

        old_map = dict(
            compra.detalles.values("producto_id")
            .annotate(total=Sum("cantidad"))
            .values_list("producto_id", "total")
        )

        total = sum(
            (linea["cantidad"] or 0) * (linea["precio_unitario"] or 0)
            for linea in lineas
        )

        compra_editada.precio_total = total
        compra_editada.save()

        formset.instance = compra_editada

        for obj in getattr(formset, "deleted_objects", []):
            obj.delete()

        detalles = formset.save(commit=False)

        for d in detalles:
            d.compra = compra_editada
            d.save()

        formset.save_m2m()

        new_map = dict(
            compra_editada.detalles.values("producto_id")
            .annotate(total=Sum("cantidad"))
            .values_list("producto_id", "total")
        )

        producto_ids = set(old_map.keys()) | set(new_map.keys())

        for pid in producto_ids:
            old_qty = old_map.get(pid) or 0
            new_qty = new_map.get(pid) or 0
            delta = new_qty - old_qty

            if delta == 0:
                continue

            producto_obj = (
                compra_editada.detalles
                .filter(producto_id=pid)
                .select_related("producto")
                .first()
            )

            if producto_obj:
                producto_ref = producto_obj.producto
            else:
                producto_ref = Producto.objects.get(pk=pid)

            aplicar_movimiento_stock(
                producto=producto_ref,
                delta=delta,
                tipo_movimiento="COMPRA_EDICION",
                usuario=usuario,
                compra=compra_editada,
                observacion=f"Edición de compra #{compra_editada.id}"
            )

    return compra_editada


def anular_compra(*, compra, usuario):
    with transaction.atomic():
        compra = Compra.objects.select_for_update().get(pk=compra.pk)

        if compra.anulada:
            raise CompraServiceError("La compra ya estaba anulada.")

        if compra.devoluciones.filter(anulada=False).exists():
            raise CompraServiceError(
                "No se puede anular la compra porque tiene devoluciones activas."
            )

        qtys = (
            compra.detalles.values("producto_id")
            .annotate(total=Sum("cantidad"))
            .values_list("producto_id", "total")
        )

        for pid, total in qtys:
            producto_ref = Producto.objects.get(pk=pid)

            try:
                aplicar_movimiento_stock(
                    producto=producto_ref,
                    delta=-(total or 0),
                    tipo_movimiento="COMPRA_ANULACION",
                    usuario=usuario,
                    compra=compra,
                    observacion=f"Anulación de compra #{compra.id}"
                )
            except ValidationError as exc:
                raise CompraServiceError(
                    f"No se puede anular la compra porque el producto {producto_ref.nombre} "
                    f"no tiene stock suficiente para revertir el movimiento."
                ) from exc

        compra.fecha_anulada = timezone.now().date()
        compra.anulada_en = timezone.now()
        compra.anulada = True
        compra.save(update_fields=["anulada", "fecha_anulada", "anulada_en"])

    return compra


def registrar_devolucion_compra(*, form, formset, usuario):
    with transaction.atomic():
        compra = (
            Compra.objects
            .select_for_update()
            .select_related("proveedor")
            .get(pk=form.cleaned_data["compra"].pk)
        )

        if compra.anulada:
            raise CompraServiceError("No puedes devolver sobre una compra anulada.")

        lineas = _extraer_lineas_devolucion_bloqueadas(compra, formset)

        devolucion = form.save(commit=False)
        devolucion.compra = compra
        devolucion.usuario = usuario
        devolucion.proveedor = compra.proveedor
        devolucion.total = 0
        devolucion.save()

        total = 0

        for detalle_compra, cantidad in lineas:
            detalle_dev = devolucion.detalles.model.objects.create(
                devolucion=devolucion,
                detalle_compra=detalle_compra,
                producto=detalle_compra.producto,
                cantidad=cantidad,
                precio_unitario=detalle_compra.precio_unitario,
            )

            aplicar_movimiento_stock(
                producto=detalle_dev.producto,
                delta=-(cantidad or 0),
                tipo_movimiento="DEV_COMPRA_SALIDA",
                usuario=usuario,
                devolucion=devolucion,
                observacion=f"Registro de devolución #{devolucion.id}"
            )

            total += detalle_dev.subtotal

        devolucion.total = total
        devolucion.save(update_fields=["total"])

    return devolucion


def anular_devolucion_compra(*, devolucion, usuario):
    with transaction.atomic():
        devolucion = (
            DevolucionCompra.objects
            .select_for_update()
            .prefetch_related("detalles__producto")
            .get(pk=devolucion.pk)
        )

        if devolucion.anulada:
            raise CompraServiceError("La devolución ya estaba anulada.")

        for d in devolucion.detalles.select_related("producto").all():
            aplicar_movimiento_stock(
                producto=d.producto,
                delta=(d.cantidad or 0),
                tipo_movimiento="DEV_COMPRA_ANULACION",
                usuario=usuario,
                devolucion=devolucion,
                observacion=f"Anulación de devolución #{devolucion.id}"
            )

        devolucion.anulada = True
        devolucion.fecha_anulada = timezone.now().date()
        devolucion.anulada_en = timezone.now()
        devolucion.save(update_fields=["anulada", "fecha_anulada", "anulada_en"])

    return devolucion


def _extraer_lineas_devolucion_validas(compra, formset):
    lineas = []
    vistos_por_detalle = set()

    for form in formset.forms:
        if not getattr(form, "cleaned_data", None):
            continue

        if form.cleaned_data.get("DELETE"):
            continue

        detalle_post = form.cleaned_data.get("detalle_compra")
        cantidad = form.cleaned_data.get("cantidad") or 0

        if not detalle_post and not cantidad:
            continue

        if not detalle_post or cantidad <= 0:
            raise CompraServiceError("Hay filas de devolución incompletas o inválidas.")

        try:
            detalle_compra = (
                compra.detalles
                .select_for_update()
                .select_related("producto")
                .get(pk=detalle_post.pk)
            )
        except compra.detalles.model.DoesNotExist as exc:
            raise CompraServiceError(
                "Se detectó un detalle de compra inválido para la devolución."
            ) from exc

        if detalle_compra.pk in vistos_por_detalle:
            raise CompraServiceError(
                "No puedes repetir el mismo detalle de compra en la misma devolución."
            )
        vistos_por_detalle.add(detalle_compra.pk)

        cantidad_ya_devuelta = (
            detalle_compra.detalles_devolucion
            .filter(devolucion__anulada=False)
            .aggregate(total=Sum("cantidad"))["total"] or 0
        )

        disponible_para_devolver = max(
            (detalle_compra.cantidad or 0) - cantidad_ya_devuelta,
            0,
        )

        if cantidad > disponible_para_devolver:
            raise CompraServiceError(
                f"Solo puedes devolver hasta {disponible_para_devolver} unidad(es) de {detalle_compra.producto.nombre}."
            )

        lineas.append((detalle_compra, cantidad))

    if not lineas:
        raise CompraServiceError("Debes agregar al menos un producto a devolver.")

    return lineas


def _extraer_lineas_devolucion_bloqueadas(compra, formset):
    lineas = []
    detalles_bloqueados = {}
    devoluciones_bloqueadas = {}
    vistos_por_detalle = set()

    for form in formset.forms:
        if not getattr(form, "cleaned_data", None):
            continue

        if form.cleaned_data.get("DELETE"):
            continue

        detalle_post = form.cleaned_data.get("detalle_compra")
        cantidad = form.cleaned_data.get("cantidad") or 0

        if not detalle_post and not cantidad:
            continue

        if not detalle_post or cantidad <= 0:
            raise CompraServiceError("Hay filas de devolución incompletas o inválidas.")

        detalle_id = detalle_post.pk

        if detalle_id not in detalles_bloqueados:
            try:
                detalle_compra = (
                    compra.detalles
                    .select_for_update()
                    .select_related("producto")
                    .get(pk=detalle_id)
                )
            except compra.detalles.model.DoesNotExist as exc:
                raise CompraServiceError(
                    "Se detectó un detalle de compra inválido para la devolución."
                ) from exc

            if detalle_compra.compra_id != compra.pk:
                raise CompraServiceError(
                    "Ese detalle no pertenece a la compra seleccionada."
                )

            detalles_bloqueados[detalle_id] = detalle_compra
            devoluciones_bloqueadas[detalle_id] = list(
                detalle_compra.detalles_devolucion
                .select_for_update()
                .filter(devolucion__anulada=False)
            )

        if detalle_id in vistos_por_detalle:
            raise CompraServiceError(
                "No puedes repetir el mismo detalle de compra en la misma devolución."
            )
        vistos_por_detalle.add(detalle_id)

        detalle_compra = detalles_bloqueados[detalle_id]
        cantidad_ya_devuelta = sum(
            (item.cantidad or 0)
            for item in devoluciones_bloqueadas[detalle_id]
        )

        disponible_para_devolver = max(
            (detalle_compra.cantidad or 0) - cantidad_ya_devuelta,
            0,
        )

        if cantidad > disponible_para_devolver:
            raise CompraServiceError(
                f"Solo puedes devolver hasta {disponible_para_devolver} unidad(es) de {detalle_compra.producto.nombre}."
            )

        lineas.append((detalle_compra, cantidad))

    if not lineas:
        raise CompraServiceError("Debes agregar al menos un producto a devolver.")

    return lineas


def _extraer_lineas_devolucion_validas(compra, formset):
    lineas = []
    vistos_por_detalle = set()

    for form in formset.forms:
        if not getattr(form, "cleaned_data", None):
            continue

        if form.cleaned_data.get("DELETE"):
            continue

        detalle_post = form.cleaned_data.get("detalle_compra")
        cantidad = form.cleaned_data.get("cantidad") or 0

        if not detalle_post and not cantidad:
            continue

        if not detalle_post or cantidad <= 0:
            raise CompraServiceError("Hay filas de devolución incompletas o inválidas.")

        try:
            detalle_compra = (
                compra.detalles
                .select_for_update()
                .select_related("producto")
                .get(pk=detalle_post.pk)
            )
        except compra.detalles.model.DoesNotExist as exc:
            raise CompraServiceError(
                "Se detectó un detalle de compra inválido para la devolución."
            ) from exc

        if detalle_compra.pk in vistos_por_detalle:
            raise CompraServiceError(
                "No puedes repetir el mismo detalle de compra en la misma devolución."
            )
        vistos_por_detalle.add(detalle_compra.pk)

        cantidad_ya_devuelta = (
            detalle_compra.detalles_devolucion
            .filter(devolucion__anulada=False)
            .aggregate(total=Sum("cantidad"))["total"] or 0
        )

        disponible_por_compra = max(
            (detalle_compra.cantidad or 0) - cantidad_ya_devuelta,
            0,
        )
        stock_actual = detalle_compra.producto.stock_actual or 0
        disponible_para_devolver = min(disponible_por_compra, stock_actual)

        if cantidad > disponible_para_devolver:
            raise CompraServiceError(
                f"Solo puedes devolver hasta {disponible_para_devolver} unidad(es) de {detalle_compra.producto.nombre}."
            )

        lineas.append((detalle_compra, cantidad))

    if not lineas:
        raise CompraServiceError("Debes agregar al menos un producto a devolver.")

    return lineas


def _extraer_lineas_devolucion_bloqueadas(compra, formset):
    lineas = []
    detalles_bloqueados = {}
    devoluciones_bloqueadas = {}
    vistos_por_detalle = set()

    for form in formset.forms:
        if not getattr(form, "cleaned_data", None):
            continue

        if form.cleaned_data.get("DELETE"):
            continue

        detalle_post = form.cleaned_data.get("detalle_compra")
        cantidad = form.cleaned_data.get("cantidad") or 0

        if not detalle_post and not cantidad:
            continue

        if not detalle_post or cantidad <= 0:
            raise CompraServiceError("Hay filas de devolución incompletas o inválidas.")

        detalle_id = detalle_post.pk

        if detalle_id not in detalles_bloqueados:
            try:
                detalle_compra = (
                    compra.detalles
                    .select_for_update()
                    .select_related("producto")
                    .get(pk=detalle_id)
                )
            except compra.detalles.model.DoesNotExist as exc:
                raise CompraServiceError(
                    "Se detectó un detalle de compra inválido para la devolución."
                ) from exc

            if detalle_compra.compra_id != compra.pk:
                raise CompraServiceError(
                    "Ese detalle no pertenece a la compra seleccionada."
                )

            detalles_bloqueados[detalle_id] = detalle_compra
            devoluciones_bloqueadas[detalle_id] = list(
                detalle_compra.detalles_devolucion
                .select_for_update()
                .filter(devolucion__anulada=False)
            )

        if detalle_id in vistos_por_detalle:
            raise CompraServiceError(
                "No puedes repetir el mismo detalle de compra en la misma devolución."
            )
        vistos_por_detalle.add(detalle_id)

        detalle_compra = detalles_bloqueados[detalle_id]
        cantidad_ya_devuelta = sum(
            (item.cantidad or 0)
            for item in devoluciones_bloqueadas[detalle_id]
        )

        disponible_por_compra = max(
            (detalle_compra.cantidad or 0) - cantidad_ya_devuelta,
            0,
        )
        stock_actual = detalle_compra.producto.stock_actual or 0
        disponible_para_devolver = min(disponible_por_compra, stock_actual)

        if cantidad > disponible_para_devolver:
            raise CompraServiceError(
                f"Solo puedes devolver hasta {disponible_para_devolver} unidad(es) de {detalle_compra.producto.nombre}."
            )

        lineas.append((detalle_compra, cantidad))

    if not lineas:
        raise CompraServiceError("Debes agregar al menos un producto a devolver.")

    return lineas


def anular_devolucion_compra(*, devolucion, usuario):
    with transaction.atomic():
        devolucion = (
            DevolucionCompra.objects
            .select_for_update()
            .prefetch_related("detalles__producto")
            .get(pk=devolucion.pk)
        )

        if devolucion.anulada:
            raise CompraServiceError("La devolución ya estaba anulada.")

        for detalle in devolucion.detalles.select_related("producto").all():
            try:
                aplicar_movimiento_stock(
                    producto=detalle.producto,
                    delta=(detalle.cantidad or 0),
                    tipo_movimiento="DEV_COMPRA_ANULACION",
                    usuario=usuario,
                    devolucion=devolucion,
                    observacion=f"Anulación de devolución #{devolucion.id}",
                )
            except ValidationError as exc:
                raise CompraServiceError(str(exc)) from exc

        devolucion.anulada = True
        devolucion.fecha_anulada = timezone.now().date()
        devolucion.anulada_en = timezone.now()
        devolucion.save(update_fields=["anulada", "fecha_anulada", "anulada_en"])

    return devolucion
