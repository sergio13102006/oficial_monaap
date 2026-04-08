from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from Proveedores.models import Proveedor
from compras.models import Compra
from control_fondos.models import BaseDiariaCuenta, CuentaFinanciera, MovimientoCuenta, TransferenciaCuenta
from control_fondos.services import registrar_base_diaria, registrar_salida_por_compra, registrar_transferencia


class ControlFondosServicesTest(TestCase):
    def setUp(self):
        self.caja = CuentaFinanciera.objects.create(nombre="Caja", tipo=CuentaFinanciera.TIPO_EFECTIVO, activa=True, orden_visual=1)
        self.banco = CuentaFinanciera.objects.create(nombre="Banco", tipo=CuentaFinanciera.TIPO_BANCO, activa=True, orden_visual=2)
        self.proveedor = Proveedor.objects.create(
            nit="9001001",
            nombre_proveedor="Proveedor",
            telefono_proveedor="3001111111",
            correo_proveedor="p@test.com",
            direccion_proveedor="Calle 1",
            estado="activo",
        )
        registrar_base_diaria(cuenta=self.caja, base_inicial=Decimal("100000"), fecha=timezone.localdate())
        registrar_base_diaria(cuenta=self.banco, base_inicial=Decimal("50000"), fecha=timezone.localdate())

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
