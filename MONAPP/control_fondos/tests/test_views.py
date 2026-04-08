from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from control_fondos.models import BaseDiariaCuenta, CuentaFinanciera, MovimientoCuenta, TransferenciaCuenta
from control_fondos.services import registrar_base_diaria, registrar_transferencia


class ControlFondosViewsTest(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="fondos",
            password="12345678",
            is_superuser=True,
        )
        self.caja = CuentaFinanciera.objects.create(
            nombre="Caja Principal",
            tipo=CuentaFinanciera.TIPO_EFECTIVO,
            activa=True,
            orden_visual=1,
        )
        self.banco = CuentaFinanciera.objects.create(
            nombre="Bancolombia",
            tipo=CuentaFinanciera.TIPO_BANCO,
            activa=True,
            orden_visual=2,
        )
        registrar_base_diaria(
            cuenta=self.caja,
            base_inicial=Decimal("10000"),
            fecha=timezone.localdate(),
            usuario=self.user,
        )
        registrar_base_diaria(
            cuenta=self.banco,
            base_inicial=Decimal("5000"),
            fecha=timezone.localdate(),
            usuario=self.user,
        )
        registrar_transferencia(
            cuenta_origen=self.caja,
            cuenta_destino=self.banco,
            valor=Decimal("2000"),
            usuario=self.user,
            fecha=timezone.localdate(),
            request_uid="test-transfer-base",
        )
        self.client.force_login(self.user)

    def test_dashboard_renderiza(self):
        response = self.client.get(reverse("control_fondos:dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Control de fondos")
        self.assertContains(response, "Caja y Bancos")
        self.assertContains(response, "Ver movimientos")

    def test_dashboard_crea_cuentas_base_si_no_existen(self):
        TransferenciaCuenta.objects.all().delete()
        MovimientoCuenta.objects.all().delete()
        BaseDiariaCuenta.objects.all().delete()
        CuentaFinanciera.objects.all().delete()

        response = self.client.get(reverse("control_fondos:dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(CuentaFinanciera.objects.filter(nombre="Caja Principal").exists())
        self.assertTrue(CuentaFinanciera.objects.filter(nombre="Bancolombia").exists())

    def test_historico_renderiza(self):
        response = self.client.get(reverse("control_fondos:historico"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Jornada")
        self.assertContains(response, "Auditoria del dia")

    def test_cuentas_renderiza(self):
        response = self.client.get(reverse("control_fondos:cuentas"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Cuentas financieras")
        self.assertContains(response, "Caja Principal")

    def test_cuentas_permite_crear_entidad_financiera(self):
        response = self.client.post(
            reverse("control_fondos:cuentas"),
            data={
                "nombre": "nequi principal",
                "tipo": CuentaFinanciera.TIPO_BILLETERA,
                "activa": "on",
                "orden_visual": 3,
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            CuentaFinanciera.objects.filter(
                nombre="Nequi Principal",
                tipo=CuentaFinanciera.TIPO_BILLETERA,
            ).exists()
        )

    def test_movimientos_renderiza(self):
        response = self.client.get(reverse("control_fondos:movimientos"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Libro de movimientos")
        self.assertContains(response, "Transferencia")
        self.assertContains(response, "Saldo neto")

    def test_detalle_cuenta_renderiza(self):
        response = self.client.get(
            reverse("control_fondos:detalle_cuenta", args=[self.caja.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Detalle de cuenta")
        self.assertContains(response, "Caja Principal")
        self.assertContains(response, "Transferencias enviadas")

    def test_transferencias_renderiza(self):
        response = self.client.get(reverse("control_fondos:transferencias"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Transferencias entre cuentas")

    def test_transferencias_post_crea_movimientos(self):
        response = self.client.post(
            reverse("control_fondos:transferencias"),
            data={
                "fecha": timezone.localdate().isoformat(),
                "cuenta_origen": self.banco.pk,
                "cuenta_destino": self.caja.pk,
                "valor": "1000",
                "observacion": "Movimiento de prueba",
                "request_uid": "transferencia-view-1",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            MovimientoCuenta.objects.filter(
                clase=MovimientoCuenta.CLASE_TRANSFERENCIA
            ).count(),
            4,
        )

    def test_transferencias_muestra_comprobante_logico(self):
        response = self.client.post(
            reverse("control_fondos:transferencias"),
            data={
                "fecha": timezone.localdate().isoformat(),
                "cuenta_origen": self.banco.pk,
                "cuenta_destino": self.caja.pk,
                "valor": "1000",
                "observacion": "Movimiento de prueba",
                "request_uid": "transferencia-view-2",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Comprobante logico")
        self.assertContains(response, "Movimiento salida")
