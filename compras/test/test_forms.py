from decimal import Decimal

from django.forms import ValidationError
from django.test import TestCase

from Proveedores.models import Proveedor
from Productos.models import Producto
from inventario.models import Stock

from compras.forms import (
    CompraForm,
    DetalleCompraForm,
    DevolucionCompraForm,
    DetalleDevolucionCompraForm,
    DetalleDevolucionCompraFormSet,
)
from compras.models import (
    Compra,
    DetalleCompra,
    DevolucionCompra,
    DetalleDevolucionCompra,
)


class CompraFormsTest(TestCase):
    def setUp(self):
        self.proveedor_activo = Proveedor.objects.create(
            nit="900100001",
            nombre_proveedor="Proveedor Activo",
            telefono_proveedor="3001111111",
            correo_proveedor="activo@test.com",
            direccion_proveedor="Calle 1",
            estado="activo",
        )
        self.proveedor_inactivo = Proveedor.objects.create(
            nit="900100002",
            nombre_proveedor="Proveedor Inactivo",
            telefono_proveedor="3002222222",
            correo_proveedor="inactivo@test.com",
            direccion_proveedor="Calle 2",
            estado="inactivo",
        )

        self.producto_activo = self._crear_producto(
            nombre="Keratina",
            precio=1000,
            stock=20,
            activo=True,
        )
        self.producto_inactivo = self._crear_producto(
            nombre="Botox",
            precio=2000,
            stock=20,
            activo=False,
        )
        self.producto_otro = self._crear_producto(
            nombre="Shampoo",
            precio=3000,
            stock=20,
            activo=True,
        )

        self.compra_activa = Compra.objects.create(
            proveedor=self.proveedor_activo,
            precio_total=Decimal("10000"),
            usuario=None,
            anulada=False,
        )
        self.detalle_compra_activo = DetalleCompra.objects.create(
            compra=self.compra_activa,
            producto=self.producto_activo,
            cantidad=10,
            precio_unitario=Decimal("1000"),
        )

        self.compra_anulada = Compra.objects.create(
            proveedor=self.proveedor_activo,
            precio_total=Decimal("5000"),
            usuario=None,
            anulada=True,
        )
        self.detalle_compra_otro = DetalleCompra.objects.create(
            compra=self.compra_anulada,
            producto=self.producto_otro,
            cantidad=5,
            precio_unitario=Decimal("3000"),
        )

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

    def _crear_devolucion_activa(self, *, compra, detalle_compra, cantidad):
        devolucion = DevolucionCompra.objects.create(
            compra=compra,
            proveedor=compra.proveedor,
            usuario=None,
            motivo="Prueba",
            observacion="",
            total=Decimal(str(cantidad)) * detalle_compra.precio_unitario,
            anulada=False,
        )
        DetalleDevolucionCompra.objects.create(
            devolucion=devolucion,
            detalle_compra=detalle_compra,
            producto=detalle_compra.producto,
            cantidad=cantidad,
            precio_unitario=detalle_compra.precio_unitario,
        )
        return devolucion

    # =========================
    # CompraForm
    # =========================
    def test_compra_form_solo_muestra_proveedores_activos(self):
        form = CompraForm()

        qs = form.fields["proveedor"].queryset
        self.assertIn(self.proveedor_activo, qs)
        self.assertNotIn(self.proveedor_inactivo, qs)

    def test_compra_form_es_valido_con_proveedor_activo(self):
        form = CompraForm(data={"proveedor": self.proveedor_activo.pk})
        self.assertTrue(form.is_valid(), form.errors)

    # =========================
    # DetalleCompraForm
    # =========================
    def test_detalle_compra_form_nuevo_solo_muestra_productos_activos(self):
        form = DetalleCompraForm()

        qs = form.fields["producto"].queryset
        self.assertIn(self.producto_activo, qs)
        self.assertIn(self.producto_otro, qs)
        self.assertNotIn(self.producto_inactivo, qs)

    def test_detalle_compra_form_edicion_incluye_producto_inactivo_actual(self):
        compra = Compra.objects.create(
            proveedor=self.proveedor_activo,
            precio_total=Decimal("4000"),
            usuario=None,
            anulada=False,
        )
        detalle = DetalleCompra.objects.create(
            compra=compra,
            producto=self.producto_inactivo,
            cantidad=2,
            precio_unitario=Decimal("2000"),
        )

        form = DetalleCompraForm(instance=detalle)

        qs = form.fields["producto"].queryset
        self.assertIn(self.producto_inactivo, qs)
        self.assertTrue(form.fields["producto"].disabled)
        self.assertIn("inactivo", form.fields["producto"].help_text.lower())

    def test_detalle_compra_form_si_manipulan_post_con_producto_inactivo_conserva_el_original(self):
        compra = Compra.objects.create(
            proveedor=self.proveedor_activo,
            precio_total=Decimal("4000"),
            usuario=None,
            anulada=False,
        )
        detalle = DetalleCompra.objects.create(
            compra=compra,
            producto=self.producto_inactivo,
            cantidad=2,
            precio_unitario=Decimal("2000"),
        )

        form = DetalleCompraForm(
            data={
                "producto": self.producto_activo.pk,
                "cantidad": 2,
                "precio_unitario": 2000,
            },
            instance=detalle,
        )

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["producto"], self.producto_inactivo)

    def test_detalle_compra_model_clean_rechaza_cantidad_menor_o_igual_a_cero(self):
        detalle = DetalleCompra(
            compra=self.compra_activa,
            producto=self.producto_activo,
            cantidad=0,
            precio_unitario=Decimal("1000"),
        )

        with self.assertRaises(ValidationError) as ctx:
            detalle.clean()

        self.assertIn("cantidad", ctx.exception.message_dict)

    def test_detalle_compra_model_clean_rechaza_precio_menor_o_igual_a_cero(self):
        detalle = DetalleCompra(
            compra=self.compra_activa,
            producto=self.producto_activo,
            cantidad=1,
            precio_unitario=Decimal("0"),
        )

        with self.assertRaises(ValidationError) as ctx:
            detalle.clean()

        self.assertIn("precio_unitario", ctx.exception.message_dict)

    # =========================
    # DevolucionCompraForm
    # =========================
    def test_devolucion_compra_form_solo_muestra_compras_no_anuladas(self):
        form = DevolucionCompraForm()

        qs = form.fields["compra"].queryset
        self.assertIn(self.compra_activa, qs)
        self.assertNotIn(self.compra_anulada, qs)

    def test_devolucion_compra_form_rechaza_compra_anulada(self):
        form = DevolucionCompraForm(
            data={
                "compra": self.compra_anulada.pk,
                "motivo": "defecto_fabrica",
                "observacion": "Obs",
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("compra", form.errors)
        self.assertIn("opción válida", form.errors["compra"][0].lower())

    def test_devolucion_compra_form_es_valido_con_compra_activa(self):
        form = DevolucionCompraForm(
            data={
                "compra": self.compra_activa.pk,
                "motivo": "defecto_fabrica",
                "observacion": "Observación",
            }
        )

        self.assertTrue(form.is_valid(), form.errors)

    # =========================
    # DetalleDevolucionCompraForm
    # =========================
    def test_detalle_devolucion_form_es_valido_con_datos_correctos(self):
        form = DetalleDevolucionCompraForm(
            data={
                "detalle_compra": self.detalle_compra_activo.pk,
                "cantidad": 2,
            },
            compra=self.compra_activa,
        )

        self.assertTrue(form.is_valid(), form.errors)

    def test_detalle_devolucion_form_rechaza_cantidad_cero(self):
        form = DetalleDevolucionCompraForm(
            data={
                "detalle_compra": self.detalle_compra_activo.pk,
                "cantidad": 0,
            },
            compra=self.compra_activa,
        )

        self.assertFalse(form.is_valid())
        self.assertIn("cantidad", form.errors)
        self.assertIn("mayor que 0", form.errors["cantidad"][0])

    def test_detalle_devolucion_form_rechaza_si_falta_detalle(self):
        form = DetalleDevolucionCompraForm(
            data={
                "detalle_compra": "",
                "cantidad": 2,
            },
            compra=self.compra_activa,
        )

        self.assertFalse(form.is_valid())
        self.assertIn("detalle_compra", form.errors)
        
    def test_detalle_devolucion_form_rechaza_detalle_que_no_pertenece_a_la_compra(self):
        form = DetalleDevolucionCompraForm(
            data={
                "detalle_compra": self.detalle_compra_otro.pk,
                "cantidad": 1,
            },
            compra=self.compra_activa,
        )

        self.assertFalse(form.is_valid())
        self.assertIn("detalle_compra", form.errors)
        self.assertIn("opción válida", form.errors["detalle_compra"][0].lower())

    def test_detalle_devolucion_form_rechaza_si_supera_disponible_para_devolver(self):
        self._crear_devolucion_activa(
            compra=self.compra_activa,
            detalle_compra=self.detalle_compra_activo,
            cantidad=8,
        )
        # Comprado 10, ya devuelto 8, disponible 2

        form = DetalleDevolucionCompraForm(
            data={
                "detalle_compra": self.detalle_compra_activo.pk,
                "cantidad": 3,
            },
            compra=self.compra_activa,
        )

        self.assertFalse(form.is_valid())
        self.assertIn("cantidad", form.errors)
        self.assertIn("solo puedes devolver hasta 2", form.errors["cantidad"][0].lower())

    def test_detalle_devolucion_form_ignora_stock_actual_bajo_si_esta_dentro_de_lo_comprado(self):
        stock = self.producto_activo.stock
        stock.cantidad_actual = 1
        stock.save(update_fields=["cantidad_actual"])

        form = DetalleDevolucionCompraForm(
            data={
                "detalle_compra": self.detalle_compra_activo.pk,
                "cantidad": 2,
            },
            compra=self.compra_activa,
        )

        self.assertTrue(form.is_valid(), form.errors)

    # =========================
    # DetalleDevolucionCompraFormSet
    # =========================
    def test_formset_devolucion_rechaza_si_no_hay_ningun_detalle(self):
        data = {
            "detalles-TOTAL_FORMS": "1",
            "detalles-INITIAL_FORMS": "0",
            "detalles-MIN_NUM_FORMS": "0",
            "detalles-MAX_NUM_FORMS": "1000",
            "detalles-0-detalle_compra": "",
            "detalles-0-cantidad": "",
        }

        formset = DetalleDevolucionCompraFormSet(
            data=data,
            prefix="detalles",
            form_kwargs={"compra": self.compra_activa},
        )

        self.assertFalse(formset.is_valid())
        self.assertIn(
            "Debes agregar al menos un producto a devolver.",
            formset.non_form_errors()
        )

    def test_formset_devolucion_rechaza_si_varias_filas_superan_disponible(self):
        # Comprado 10. Dos filas del mismo detalle suman 11.
        data = {
            "detalles-TOTAL_FORMS": "3",
            "detalles-INITIAL_FORMS": "0",
            "detalles-MIN_NUM_FORMS": "0",
            "detalles-MAX_NUM_FORMS": "1000",

            "detalles-0-detalle_compra": str(self.detalle_compra_activo.pk),
            "detalles-0-cantidad": "6",

            "detalles-1-detalle_compra": str(self.detalle_compra_activo.pk),
            "detalles-1-cantidad": "5",

            "detalles-2-detalle_compra": "",
            "detalles-2-cantidad": "",
        }

        formset = DetalleDevolucionCompraFormSet(
            data=data,
            prefix="detalles",
            form_kwargs={"compra": self.compra_activa},
        )

        self.assertFalse(formset.is_valid())

        errores_cantidad = []
        for form in formset.forms:
            errores_cantidad.extend(form.errors.get("cantidad", []))

        self.assertTrue(
            any("entre todas las filas solo puedes devolver hasta 10" in e.lower() for e in errores_cantidad),
            msg=f"No encontré el error esperado. Errores: {errores_cantidad}"
        )

    def test_formset_devolucion_es_valido_si_las_filas_no_superan_disponible(self):
        data = {
            "detalles-TOTAL_FORMS": "3",
            "detalles-INITIAL_FORMS": "0",
            "detalles-MIN_NUM_FORMS": "0",
            "detalles-MAX_NUM_FORMS": "1000",

            "detalles-0-detalle_compra": str(self.detalle_compra_activo.pk),
            "detalles-0-cantidad": "4",

            "detalles-1-detalle_compra": str(self.detalle_compra_activo.pk),
            "detalles-1-cantidad": "3",

            "detalles-2-detalle_compra": "",
            "detalles-2-cantidad": "",
        }

        formset = DetalleDevolucionCompraFormSet(
            data=data,
            prefix="detalles",
            form_kwargs={"compra": self.compra_activa},
        )

        self.assertTrue(formset.is_valid(), formset.errors)


def _test_formset_devolucion_rechaza_si_repite_el_mismo_detalle(self):
    data = {
        "detalles-TOTAL_FORMS": "3",
        "detalles-INITIAL_FORMS": "0",
        "detalles-MIN_NUM_FORMS": "0",
        "detalles-MAX_NUM_FORMS": "1000",
        "detalles-0-detalle_compra": str(self.detalle_compra_activo.pk),
        "detalles-0-cantidad": "2",
        "detalles-1-detalle_compra": str(self.detalle_compra_activo.pk),
        "detalles-1-cantidad": "1",
        "detalles-2-detalle_compra": "",
        "detalles-2-cantidad": "",
    }

    formset = DetalleDevolucionCompraFormSet(
        data=data,
        prefix="detalles",
        form_kwargs={"compra": self.compra_activa},
    )

    self.assertFalse(formset.is_valid())

    errores_detalle = []
    for form in formset.forms:
        errores_detalle.extend(form.errors.get("detalle_compra", []))

    self.assertTrue(
        any("no puedes repetir el mismo detalle de compra" in e.lower() for e in errores_detalle),
        msg=f"No encontré el error esperado. Errores: {errores_detalle}",
    )


def _test_formset_devolucion_es_valido_si_las_filas_usan_detalles_distintos(self):
    detalle_compra_extra = DetalleCompra.objects.create(
        compra=self.compra_activa,
        producto=self.producto_otro,
        cantidad=6,
        precio_unitario=Decimal("3000"),
    )

    data = {
        "detalles-TOTAL_FORMS": "3",
        "detalles-INITIAL_FORMS": "0",
        "detalles-MIN_NUM_FORMS": "0",
        "detalles-MAX_NUM_FORMS": "1000",
        "detalles-0-detalle_compra": str(self.detalle_compra_activo.pk),
        "detalles-0-cantidad": "4",
        "detalles-1-detalle_compra": str(detalle_compra_extra.pk),
        "detalles-1-cantidad": "2",
        "detalles-2-detalle_compra": "",
        "detalles-2-cantidad": "",
    }

    formset = DetalleDevolucionCompraFormSet(
        data=data,
        prefix="detalles",
        form_kwargs={"compra": self.compra_activa},
    )

    self.assertTrue(formset.is_valid(), formset.errors)


CompraFormsTest.test_formset_devolucion_rechaza_si_varias_filas_superan_disponible = _test_formset_devolucion_rechaza_si_repite_el_mismo_detalle
CompraFormsTest.test_formset_devolucion_es_valido_si_las_filas_no_superan_disponible = _test_formset_devolucion_es_valido_si_las_filas_usan_detalles_distintos
