from datetime import datetime
from decimal import Decimal
from unittest.mock import call, patch

from django.test import TestCase
from django.utils import timezone

from Proveedores.models import Proveedor
from Productos.models import Producto
from inventario.models import Stock

from compras import services
from compras.forms import (
    CompraForm,
    DetalleCompraFormSet,
    DevolucionCompraForm,
    DetalleDevolucionCompraFormSet,
)
from compras.models import Compra, DetalleCompra, DevolucionCompra, DetalleDevolucionCompra


class CompraServicesTest(TestCase):
    def setUp(self):
        self.proveedor = Proveedor.objects.create(
            nit="900100200",
            nombre_proveedor="Proveedor Test",
            telefono_proveedor="3001234567",
            correo_proveedor="proveedor@test.com",
            direccion_proveedor="Calle 123",
            estado="activo",
        )

        self.producto_1 = self._crear_producto(
            nombre="Keratina",
            precio=1000,
            stock=50,
        )
        self.producto_2 = self._crear_producto(
            nombre="Botox",
            precio=2000,
            stock=50,
        )
        self.producto_3 = self._crear_producto(
            nombre="Shampoo",
            precio=3000,
            stock=50,
        )

        # En services.py el usuario es nullable en Compra/Devolucion
        # y aquí no hace falta autenticar. Así evitamos dependencias
        # laterales de perfiles o señales del módulo usuarios.
        self.usuario = None

    # =========================
    # Helpers
    # =========================
    def _crear_producto(self, *, nombre, precio, stock=0, activo=True):
        producto = Producto.objects.create(
            marca="Mona",
            nombre=nombre,
            precio=precio,
            descripcion="",
            linea="",
            presentacion="",
            unidad_medida="unidad",
            activo=activo,
        )

        stock_obj, _ = Stock.objects.get_or_create(
            producto=producto,
            defaults={"cantidad_actual": stock}
        )

        if stock_obj.cantidad_actual != stock:
            stock_obj.cantidad_actual = stock
            stock_obj.save(update_fields=["cantidad_actual"])

        return producto
    def _crear_compra_directa(self, detalles):
        """
        detalles = [
            {"producto": self.producto_1, "cantidad": 5, "precio_unitario": 1000},
            ...
        ]
        """
        total = sum(
            Decimal(str(d["cantidad"])) * Decimal(str(d["precio_unitario"]))
            for d in detalles
        )

        compra = Compra.objects.create(
            proveedor=self.proveedor,
            precio_total=total,
            usuario=self.usuario,
        )

        for d in detalles:
            DetalleCompra.objects.create(
                compra=compra,
                producto=d["producto"],
                cantidad=d["cantidad"],
                precio_unitario=Decimal(str(d["precio_unitario"])),
            )

        return compra

    def _crear_devolucion_directa(self, compra, detalles, total=0, anulada=False):
        devolucion = DevolucionCompra.objects.create(
            compra=compra,
            proveedor=compra.proveedor,
            usuario=self.usuario,
            motivo="Prueba",
            observacion="",
            total=Decimal(str(total)),
            anulada=anulada,
        )

        for d in detalles:
            DetalleDevolucionCompra.objects.create(
                devolucion=devolucion,
                detalle_compra=d["detalle_compra"],
                producto=d["detalle_compra"].producto,
                cantidad=d["cantidad"],
                precio_unitario=Decimal(str(d["precio_unitario"])),
            )

        return devolucion

    def _compra_form_valido(self, *, proveedor=None, instance=None):
        form = CompraForm(
            data={"proveedor": (proveedor or self.proveedor).pk},
            instance=instance,
        )
        self.assertTrue(form.is_valid(), form.errors)
        return form

    def _detalle_compra_formset_creacion_valido(self, filas):
        data = {
            "detalles-TOTAL_FORMS": str(len(filas) + 1),
            "detalles-INITIAL_FORMS": "0",
            "detalles-MIN_NUM_FORMS": "0",
            "detalles-MAX_NUM_FORMS": "1000",
        }

        for i, fila in enumerate(filas):
            data[f"detalles-{i}-producto"] = str(fila["producto"].pk)
            data[f"detalles-{i}-cantidad"] = str(fila["cantidad"])
            data[f"detalles-{i}-precio_unitario"] = str(fila["precio_unitario"])

        blank = len(filas)
        data[f"detalles-{blank}-producto"] = ""
        data[f"detalles-{blank}-cantidad"] = ""
        data[f"detalles-{blank}-precio_unitario"] = ""

        formset = DetalleCompraFormSet(data=data, prefix="detalles")
        self.assertTrue(formset.is_valid(), formset.errors)
        return formset

    def _detalle_compra_formset_edicion_valido(
        self,
        *,
        compra,
        filas_existentes,
        filas_nuevas=None,
    ):
        filas_nuevas = filas_nuevas or []

        total_forms = len(filas_existentes) + len(filas_nuevas) + 1
        data = {
            "detalles-TOTAL_FORMS": str(total_forms),
            "detalles-INITIAL_FORMS": str(len(filas_existentes)),
            "detalles-MIN_NUM_FORMS": "0",
            "detalles-MAX_NUM_FORMS": "1000",
        }

        for i, fila in enumerate(filas_existentes):
            detalle = fila["detalle"]
            data[f"detalles-{i}-id"] = str(detalle.pk)
            data[f"detalles-{i}-producto"] = str(fila.get("producto", detalle.producto).pk)
            data[f"detalles-{i}-cantidad"] = str(fila.get("cantidad", detalle.cantidad))
            data[f"detalles-{i}-precio_unitario"] = str(
                fila.get("precio_unitario", detalle.precio_unitario)
            )
            if fila.get("DELETE"):
                data[f"detalles-{i}-DELETE"] = "on"

        offset = len(filas_existentes)
        for j, fila in enumerate(filas_nuevas, start=offset):
            data[f"detalles-{j}-producto"] = str(fila["producto"].pk)
            data[f"detalles-{j}-cantidad"] = str(fila["cantidad"])
            data[f"detalles-{j}-precio_unitario"] = str(fila["precio_unitario"])

        blank = len(filas_existentes) + len(filas_nuevas)
        data[f"detalles-{blank}-producto"] = ""
        data[f"detalles-{blank}-cantidad"] = ""
        data[f"detalles-{blank}-precio_unitario"] = ""

        formset = DetalleCompraFormSet(
            data=data,
            instance=compra,
            prefix="detalles",
        )
        self.assertTrue(formset.is_valid(), formset.errors)
        return formset

    def _devolucion_form_valido(self, *, compra):
        form = DevolucionCompraForm(
            data={
                "compra": compra.pk,
                "motivo": "defecto_fabrica",
                "observacion": "Observación de prueba",
            }
        )
        self.assertTrue(form.is_valid(), form.errors)
        return form

    def _detalle_devolucion_formset_valido(self, *, compra, filas):
        data = {
            "detalles-TOTAL_FORMS": str(len(filas) + 1),
            "detalles-INITIAL_FORMS": "0",
            "detalles-MIN_NUM_FORMS": "0",
            "detalles-MAX_NUM_FORMS": "1000",
        }

        for i, fila in enumerate(filas):
            data[f"detalles-{i}-detalle_compra"] = str(fila["detalle_compra"].pk)
            data[f"detalles-{i}-cantidad"] = str(fila["cantidad"])

        blank = len(filas)
        data[f"detalles-{blank}-detalle_compra"] = ""
        data[f"detalles-{blank}-cantidad"] = ""

        formset = DetalleDevolucionCompraFormSet(
            data=data,
            prefix="detalles",
            form_kwargs={"compra": compra},
        )
        self.assertTrue(formset.is_valid(), formset.errors)
        return formset

    # =========================
    # validar_compra_editable
    # =========================
    def test_validar_compra_editable_falla_si_esta_anulada(self):
        compra = self._crear_compra_directa([
            {"producto": self.producto_1, "cantidad": 2, "precio_unitario": 1000},
        ])
        compra.anulada = True
        compra.save(update_fields=["anulada"])

        with self.assertRaisesMessage(
            services.CompraServiceError,
            "No se puede editar una compra anulada."
        ):
            services.validar_compra_editable(compra)

    def test_validar_compra_editable_falla_si_tiene_devoluciones_activas(self):
        compra = self._crear_compra_directa([
            {"producto": self.producto_1, "cantidad": 2, "precio_unitario": 1000},
        ])
        detalle = compra.detalles.first()

        self._crear_devolucion_directa(
            compra=compra,
            detalles=[
                {
                    "detalle_compra": detalle,
                    "cantidad": 1,
                    "precio_unitario": detalle.precio_unitario,
                }
            ],
            total=1000,
            anulada=False,
        )

        with self.assertRaisesMessage(
            services.CompraServiceError,
            "No se puede editar una compra con devoluciones activas."
        ):
            services.validar_compra_editable(compra)

    # =========================
    # registrar_compra
    # =========================
    @patch("compras.services.aplicar_movimiento_stock")
    def test_registrar_compra_guarda_total_detalles_y_movimientos(self, mock_mov_stock):
        form = self._compra_form_valido()

        formset = self._detalle_compra_formset_creacion_valido([
            {"producto": self.producto_1, "cantidad": 2, "precio_unitario": 1000},
            {"producto": self.producto_2, "cantidad": 3, "precio_unitario": 2000},
        ])

        compra = services.registrar_compra(
            form=form,
            formset=formset,
            usuario=self.usuario,
        )

        compra.refresh_from_db()

        self.assertEqual(compra.proveedor, self.proveedor)
        self.assertEqual(compra.precio_total, Decimal("8000"))
        self.assertEqual(compra.detalles.count(), 2)

        detalle_1 = compra.detalles.get(producto=self.producto_1)
        detalle_2 = compra.detalles.get(producto=self.producto_2)

        self.assertEqual(detalle_1.cantidad, 2)
        self.assertEqual(detalle_1.precio_unitario, Decimal("1000"))
        self.assertEqual(detalle_2.cantidad, 3)
        self.assertEqual(detalle_2.precio_unitario, Decimal("2000"))

        self.assertEqual(mock_mov_stock.call_count, 2)
        mock_mov_stock.assert_has_calls([
            call(
                producto=self.producto_1,
                delta=2,
                tipo_movimiento="COMPRA_ENTRADA",
                usuario=self.usuario,
                compra=compra,
                observacion=f"Registro de compra #{compra.id}"
            ),
            call(
                producto=self.producto_2,
                delta=3,
                tipo_movimiento="COMPRA_ENTRADA",
                usuario=self.usuario,
                compra=compra,
                observacion=f"Registro de compra #{compra.id}"
            ),
        ], any_order=True)

    # =========================
    # editar_compra
    # =========================
    @patch("compras.services.aplicar_movimiento_stock")
    def test_editar_compra_recalcula_total_y_aplica_deltas(self, mock_mov_stock):
        compra = self._crear_compra_directa([
            {"producto": self.producto_1, "cantidad": 5, "precio_unitario": 1000},
            {"producto": self.producto_2, "cantidad": 3, "precio_unitario": 2000},
        ])

        detalle_1 = compra.detalles.get(producto=self.producto_1)
        detalle_2 = compra.detalles.get(producto=self.producto_2)

        form = self._compra_form_valido(instance=compra)

        formset = self._detalle_compra_formset_edicion_valido(
            compra=compra,
            filas_existentes=[
                {
                    "detalle": detalle_1,
                    "cantidad": 7,  # delta +2
                    "precio_unitario": 1000,
                },
                {
                    "detalle": detalle_2,
                    "cantidad": 1,  # delta -2
                    "precio_unitario": 2000,
                },
            ],
        )

        compra_editada = services.editar_compra(
            compra=compra,
            form=form,
            formset=formset,
            usuario=self.usuario,
        )

        compra_editada.refresh_from_db()

        self.assertEqual(compra_editada.precio_total, Decimal("9000"))
        self.assertEqual(
            compra_editada.detalles.get(producto=self.producto_1).cantidad,
            7
        )
        self.assertEqual(
            compra_editada.detalles.get(producto=self.producto_2).cantidad,
            1
        )

        self.assertEqual(mock_mov_stock.call_count, 2)
        mock_mov_stock.assert_has_calls([
            call(
                producto=self.producto_1,
                delta=2,
                tipo_movimiento="COMPRA_EDICION",
                usuario=self.usuario,
                compra=compra_editada,
                observacion=f"Edición de compra #{compra_editada.id}"
            ),
            call(
                producto=self.producto_2,
                delta=-2,
                tipo_movimiento="COMPRA_EDICION",
                usuario=self.usuario,
                compra=compra_editada,
                observacion=f"Edición de compra #{compra_editada.id}"
            ),
        ], any_order=True)

    # =========================
    # anular_compra
    # =========================
    @patch("compras.services.aplicar_movimiento_stock")
    def test_anular_compra_marca_anulada_y_revierte_stock(self, mock_mov_stock):
        compra = self._crear_compra_directa([
            {"producto": self.producto_1, "cantidad": 5, "precio_unitario": 1000},
            {"producto": self.producto_2, "cantidad": 2, "precio_unitario": 2000},
        ])

        fixed_now = timezone.make_aware(datetime(2026, 3, 17, 10, 30, 0))

        with patch("compras.services.timezone.now", return_value=fixed_now):
            services.anular_compra(compra=compra, usuario=self.usuario)

        compra.refresh_from_db()

        self.assertTrue(compra.anulada)
        self.assertEqual(compra.fecha_anulada, fixed_now.date())
        self.assertEqual(compra.anulada_en, fixed_now)

        self.assertEqual(mock_mov_stock.call_count, 2)
        mock_mov_stock.assert_has_calls([
            call(
                producto=self.producto_1,
                delta=-5,
                tipo_movimiento="COMPRA_ANULACION",
                usuario=self.usuario,
                compra=compra,
                observacion=f"Anulación de compra #{compra.id}"
            ),
            call(
                producto=self.producto_2,
                delta=-2,
                tipo_movimiento="COMPRA_ANULACION",
                usuario=self.usuario,
                compra=compra,
                observacion=f"Anulación de compra #{compra.id}"
            ),
        ], any_order=True)

    def test_anular_compra_falla_si_ya_estaba_anulada(self):
        compra = self._crear_compra_directa([
            {"producto": self.producto_1, "cantidad": 1, "precio_unitario": 1000},
        ])
        compra.anulada = True
        compra.save(update_fields=["anulada"])

        with self.assertRaisesMessage(
            services.CompraServiceError,
            "La compra ya estaba anulada."
        ):
            services.anular_compra(compra=compra, usuario=self.usuario)

    def test_anular_compra_falla_si_tiene_devoluciones_activas(self):
        compra = self._crear_compra_directa([
            {"producto": self.producto_1, "cantidad": 2, "precio_unitario": 1000},
        ])
        detalle = compra.detalles.first()

        self._crear_devolucion_directa(
            compra=compra,
            detalles=[
                {
                    "detalle_compra": detalle,
                    "cantidad": 1,
                    "precio_unitario": detalle.precio_unitario,
                }
            ],
            total=1000,
            anulada=False,
        )

        with self.assertRaisesMessage(
            services.CompraServiceError,
            "No se puede anular la compra porque tiene devoluciones activas."
        ):
            services.anular_compra(compra=compra, usuario=self.usuario)

    # =========================
    # registrar_devolucion_compra
    # =========================
    @patch("compras.services.aplicar_movimiento_stock")
    def test_registrar_devolucion_compra_guarda_total_proveedor_y_movimientos(self, mock_mov_stock):
        compra = self._crear_compra_directa([
            {"producto": self.producto_1, "cantidad": 5, "precio_unitario": 1000},
            {"producto": self.producto_2, "cantidad": 4, "precio_unitario": 2000},
        ])

        detalle_1 = compra.detalles.get(producto=self.producto_1)
        detalle_2 = compra.detalles.get(producto=self.producto_2)

        form = self._devolucion_form_valido(compra=compra)
        formset = self._detalle_devolucion_formset_valido(
            compra=compra,
            filas=[
                {"detalle_compra": detalle_1, "cantidad": 2},
                {"detalle_compra": detalle_2, "cantidad": 1},
            ],
        )

        devolucion = services.registrar_devolucion_compra(
            form=form,
            formset=formset,
            usuario=self.usuario,
        )

        devolucion.refresh_from_db()

        self.assertEqual(devolucion.compra, compra)
        self.assertEqual(devolucion.proveedor, compra.proveedor)
        self.assertEqual(devolucion.total, Decimal("4000"))
        self.assertEqual(devolucion.detalles.count(), 2)

        dev_1 = devolucion.detalles.get(producto=self.producto_1)
        dev_2 = devolucion.detalles.get(producto=self.producto_2)

        self.assertEqual(dev_1.cantidad, 2)
        self.assertEqual(dev_1.precio_unitario, Decimal("1000"))
        self.assertEqual(dev_2.cantidad, 1)
        self.assertEqual(dev_2.precio_unitario, Decimal("2000"))

        self.assertEqual(mock_mov_stock.call_count, 2)
        mock_mov_stock.assert_has_calls([
            call(
                producto=self.producto_1,
                delta=-2,
                tipo_movimiento="DEV_COMPRA_SALIDA",
                usuario=self.usuario,
                devolucion=devolucion,
                observacion=f"Registro de devolución #{devolucion.id}"
            ),
            call(
                producto=self.producto_2,
                delta=-1,
                tipo_movimiento="DEV_COMPRA_SALIDA",
                usuario=self.usuario,
                devolucion=devolucion,
                observacion=f"Registro de devolución #{devolucion.id}"
            ),
        ], any_order=True)

    @patch("compras.services.aplicar_movimiento_stock")
    def test_registrar_devolucion_compra_rechaza_si_el_estado_cambia_antes_de_guardar(self, mock_mov_stock):
        compra = self._crear_compra_directa([
            {"producto": self.producto_1, "cantidad": 5, "precio_unitario": 1000},
        ])
        detalle = compra.detalles.first()

        form = self._devolucion_form_valido(compra=compra)
        formset = self._detalle_devolucion_formset_valido(
            compra=compra,
            filas=[
                {"detalle_compra": detalle, "cantidad": 5},
            ],
        )

        self._crear_devolucion_directa(
            compra=compra,
            detalles=[
                {
                    "detalle_compra": detalle,
                    "cantidad": 5,
                    "precio_unitario": detalle.precio_unitario,
                }
            ],
            total=5000,
            anulada=False,
        )

        with self.assertRaisesMessage(
            services.CompraServiceError,
            "Solo puedes devolver hasta 0 unidad(es)"
        ):
            services.registrar_devolucion_compra(
                form=form,
                formset=formset,
                usuario=self.usuario,
            )

        self.assertEqual(mock_mov_stock.call_count, 0)

    # =========================
    # anular_devolucion_compra
    # =========================
    @patch("compras.services.aplicar_movimiento_stock")
    def test_anular_devolucion_compra_marca_anulada_y_restaura_stock(self, mock_mov_stock):
        compra = self._crear_compra_directa([
            {"producto": self.producto_1, "cantidad": 5, "precio_unitario": 1000},
        ])
        detalle = compra.detalles.first()

        devolucion = self._crear_devolucion_directa(
            compra=compra,
            detalles=[
                {
                    "detalle_compra": detalle,
                    "cantidad": 2,
                    "precio_unitario": detalle.precio_unitario,
                }
            ],
            total=2000,
            anulada=False,
        )

        fixed_now = timezone.make_aware(datetime(2026, 3, 17, 11, 0, 0))

        with patch("compras.services.timezone.now", return_value=fixed_now):
            services.anular_devolucion_compra(
                devolucion=devolucion,
                usuario=self.usuario,
            )

        devolucion.refresh_from_db()

        self.assertTrue(devolucion.anulada)
        self.assertEqual(devolucion.fecha_anulada, fixed_now.date())
        self.assertEqual(devolucion.anulada_en, fixed_now)

        mock_mov_stock.assert_called_once_with(
            producto=self.producto_1,
            delta=2,
            tipo_movimiento="DEV_COMPRA_ANULACION",
            usuario=self.usuario,
            devolucion=devolucion,
            observacion=f"Anulación de devolución #{devolucion.id}"
        )

    def test_anular_devolucion_compra_falla_si_ya_estaba_anulada(self):
        compra = self._crear_compra_directa([
            {"producto": self.producto_1, "cantidad": 2, "precio_unitario": 1000},
        ])
        detalle = compra.detalles.first()

        devolucion = self._crear_devolucion_directa(
            compra=compra,
            detalles=[
                {
                    "detalle_compra": detalle,
                    "cantidad": 1,
                    "precio_unitario": detalle.precio_unitario,
                }
            ],
            total=1000,
            anulada=True,
        )

        with self.assertRaisesMessage(
            services.CompraServiceError,
            "La devolución ya estaba anulada."
        ):
            services.anular_devolucion_compra(
                devolucion=devolucion,
                usuario=self.usuario,
            )


def _test_registrar_devolucion_compra_rechaza_detalle_repetido(self):
    from types import SimpleNamespace

    compra = self._crear_compra_directa([
        {"producto": self.producto_1, "cantidad": 5, "precio_unitario": 1000},
    ])
    detalle = compra.detalles.first()

    form = self._devolucion_form_valido(compra=compra)
    formset = SimpleNamespace(
        forms=[
            SimpleNamespace(
                cleaned_data={
                    "DELETE": False,
                    "detalle_compra": detalle,
                    "cantidad": 2,
                }
            ),
            SimpleNamespace(
                cleaned_data={
                    "DELETE": False,
                    "detalle_compra": detalle,
                    "cantidad": 1,
                }
            ),
        ]
    )

    with self.assertRaisesMessage(
        services.CompraServiceError,
        "No puedes repetir el mismo detalle de compra en la misma devolución.",
    ):
        services.registrar_devolucion_compra(
            form=form,
            formset=formset,
            usuario=self.usuario,
        )


CompraServicesTest.test_registrar_devolucion_compra_rechaza_detalle_repetido = (
    _test_registrar_devolucion_compra_rechaza_detalle_repetido
)
