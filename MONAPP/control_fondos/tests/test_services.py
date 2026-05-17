from decimal import Decimal
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from Proveedores.models import Proveedor
from compras.models import Compra
from control_fondos.forms import MovimientoControladoForm
from control_fondos.models import BaseDiariaCuenta, CuentaFinanciera, MovimientoCuenta, TransferenciaCuenta
from control_fondos.services import ControlFondosError, abrir_jornada, registrar_base_diaria, registrar_salida_por_compra, registrar_transferencia


class ControlFondosServicesTest(TestCase):
    def setUp(self):
        self.caja = CuentaFinanciera.objects.get(codigo="CAJA_PRINCIPAL")
        self.caja_fuerte = CuentaFinanciera.objects.get(codigo="CAJA_FUERTE")
        self.banco = CuentaFinanciera.objects.get(codigo="BANCOLOMBIA")
        self.nequi = CuentaFinanciera.objects.get(codigo="NEQUI")
        self.daviplata = CuentaFinanciera.objects.get(codigo="DAVIPLATA")
        self.nu_bank = CuentaFinanciera.objects.get(codigo="NU_BANK")
        for cuenta in [self.caja, self.caja_fuerte, self.banco, self.nequi, self.daviplata, self.nu_bank]:
            cuenta.activa = True
            cuenta.save(update_fields=["activa"])
        self.caja.activa = True
        self.caja.save(update_fields=["activa"])
        self.banco.activa = True
        self.banco.save(update_fields=["activa"])
        self.nequi.activa = True
        self.nequi.save(update_fields=["activa"])
        self.daviplata.activa = True
        self.daviplata.save(update_fields=["activa"])
        self.nu_bank.activa = True
        self.nu_bank.save(update_fields=["activa"])
        self.proveedor = Proveedor.objects.create(
            nit="9001001",
            nombre_proveedor="Proveedor",
            telefono_proveedor="3001111111",
            correo_proveedor="p@test.com",
            direccion_proveedor="Calle 1",
            estado="activo",
        )
        for cuenta, base in [
            (self.caja, Decimal("100000")),
            (self.caja_fuerte, Decimal("50000")),
            (self.banco, Decimal("50000")),
            (self.nequi, Decimal("0")),
            (self.daviplata, Decimal("0")),
            (self.nu_bank, Decimal("0")),
        ]:
            registrar_base_diaria(cuenta=cuenta, base_inicial=base, fecha=timezone.localdate())

    def test_registrar_base_diaria_unica_por_cuenta_y_fecha(self):
        registrar_base_diaria(cuenta=self.caja, base_inicial=Decimal("100000"), fecha=timezone.localdate())
        self.assertEqual(BaseDiariaCuenta.objects.filter(cuenta=self.caja, jornada__fecha=timezone.localdate()).count(), 1)

    def test_registrar_salida_por_compra_crea_movimiento(self):
        compra = Compra.objects.create(proveedor=self.proveedor, cuenta_financiera=self.caja, precio_total=Decimal("25000"))
        movimiento, created = registrar_salida_por_compra(compra=compra, request_uid="cf-compra-1")
        self.assertTrue(created)
        self.assertEqual(movimiento.compra, compra)
        self.assertEqual(movimiento.tipo, MovimientoCuenta.TIPO_SALIDA)

    def test_transferencia_crea_dos_movimientos_enlazados(self):
        transferencia = registrar_transferencia(
            cuenta_origen=self.caja,
            cuenta_destino=self.banco,
            valor=Decimal("10000"),
            request_uid="cf-transfer-1",
        )
        self.assertIsInstance(transferencia, TransferenciaCuenta)
        self.assertEqual(transferencia.movimiento_salida.tipo, MovimientoCuenta.TIPO_SALIDA)
        self.assertEqual(transferencia.movimiento_entrada.tipo, MovimientoCuenta.TIPO_ENTRADA)

    def test_jornada_queda_en_apertura_incompleta_si_faltan_bases_obligatorias(self):
        fecha = timezone.localdate() + timedelta(days=1)
        registrar_base_diaria(cuenta=self.caja, base_inicial=Decimal("100000"), fecha=fecha)
        jornada = abrir_jornada(fecha=fecha, usuario=None, sede="Principal")
        self.assertEqual(jornada.estado, "APERTURA_INCOMPLETA")

    def test_cuentas_sin_base_no_permiten_registrar_base(self):
        medio_pago = CuentaFinanciera.objects.get(codigo="DATAFONO")

        with self.assertRaises(ControlFondosError):
            registrar_base_diaria(
                cuenta=medio_pago,
                base_inicial=Decimal("1000"),
                fecha=timezone.localdate(),
            )

    def test_movimiento_ingreso_permite_pagos_mixtos_si_cuadran(self):
        form = MovimientoControladoForm(
            data={
                "fecha": timezone.localdate().isoformat(),
                "tipo_movimiento": MovimientoCuenta.TIPO_MOVIMIENTO_INGRESO,
                "cuenta": self.caja.pk,
                "valor_total": "1000",
                "descuento": "0",
                "entrada_efectivo": "500",
                "bancolombia": "500",
                "referencia": "REF-1",
            }
        )
        self.assertTrue(form.is_valid(), form.errors.as_json())

    def test_movimiento_ingreso_rechaza_pagos_mixtos_descuadrados(self):
        form = MovimientoControladoForm(
            data={
                "fecha": timezone.localdate().isoformat(),
                "tipo_movimiento": MovimientoCuenta.TIPO_MOVIMIENTO_INGRESO,
                "cuenta": self.caja.pk,
                "valor_total": "1000",
                "descuento": "0",
                "entrada_efectivo": "400",
                "bancolombia": "500",
                "referencia": "REF-1",
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("valor neto debe coincidir", str(form.errors).lower())
