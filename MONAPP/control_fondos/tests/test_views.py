from decimal import Decimal

from django.contrib.auth.models import Group
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
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
        self.caja = CuentaFinanciera.objects.get(codigo="CAJA_PRINCIPAL")
        self.caja_fuerte = CuentaFinanciera.objects.get(codigo="CAJA_FUERTE")
        self.banco = CuentaFinanciera.objects.get(codigo="BANCOLOMBIA")
        self.nequi = CuentaFinanciera.objects.get(codigo="NEQUI")
        self.daviplata = CuentaFinanciera.objects.get(codigo="DAVIPLATA")
        self.nu_bank = CuentaFinanciera.objects.get(codigo="NU_BANK")
        for cuenta in [self.caja, self.caja_fuerte, self.banco, self.nequi, self.daviplata, self.nu_bank]:
            cuenta.activa = True
            cuenta.save(update_fields=["activa"])
        registrar_base_diaria(
            cuenta=self.caja,
            base_inicial=Decimal("10000"),
            fecha=timezone.localdate(),
            usuario=self.user,
        )
        registrar_base_diaria(
            cuenta=self.caja_fuerte,
            base_inicial=Decimal("5000"),
            fecha=timezone.localdate(),
            usuario=self.user,
        )
        registrar_base_diaria(
            cuenta=self.banco,
            base_inicial=Decimal("5000"),
            fecha=timezone.localdate(),
            usuario=self.user,
        )
        registrar_base_diaria(
            cuenta=self.nequi,
            base_inicial=Decimal("0"),
            fecha=timezone.localdate(),
            usuario=self.user,
        )
        registrar_base_diaria(
            cuenta=self.daviplata,
            base_inicial=Decimal("0"),
            fecha=timezone.localdate(),
            usuario=self.user,
        )
        registrar_base_diaria(
            cuenta=self.nu_bank,
            base_inicial=Decimal("0"),
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

    def test_colaborador_puede_ver_pero_no_gestionar(self):
        grupo = Group.objects.create(name="Colaborador")
        self.user.is_superuser = False
        self.user.save(update_fields=["is_superuser"])
        self.user.groups.add(grupo)
        self.client.force_login(self.user)

        response_dashboard = self.client.get(reverse("control_fondos:dashboard"))
        response_cuentas = self.client.get(reverse("control_fondos:cuentas"))

        self.assertEqual(response_dashboard.status_code, 200)
        self.assertEqual(response_cuentas.status_code, 403)

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

    def test_movimientos_post_con_soporte_adjuntado(self):
        soporte = SimpleUploadedFile("movimiento.txt", b"soporte movimiento")
        response = self.client.post(
            reverse("control_fondos:movimientos"),
            data={
                "fecha": timezone.localdate().isoformat(),
                "tipo_movimiento": MovimientoCuenta.TIPO_MOVIMIENTO_INGRESO,
                "cuenta": self.caja.pk,
                "valor_total": "1000",
                "descuento": "0",
                "entrada_efectivo": "1000",
                "referencia": "REF-MOV-1",
                "soporte_adjunto": soporte,
            },
        )

        self.assertEqual(response.status_code, 302)
        movimiento = MovimientoCuenta.objects.latest("id")
        self.assertTrue(bool(movimiento.soporte_adjunto))

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

    def test_transferencias_post_con_soporte_adjunto(self):
        soporte = SimpleUploadedFile("transferencia.txt", b"soporte transferencia")
        response = self.client.post(
            reverse("control_fondos:transferencias"),
            data={
                "fecha": timezone.localdate().isoformat(),
                "cuenta_origen": self.banco.pk,
                "cuenta_destino": self.caja.pk,
                "valor": "1000",
                "observacion": "Movimiento de prueba",
                "request_uid": "transferencia-view-file",
                "soporte_adjunto": soporte,
            },
        )

        self.assertEqual(response.status_code, 302)
        transferencia = TransferenciaCuenta.objects.latest("id")
        self.assertTrue(bool(transferencia.soporte_adjunto))

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

    def test_bitacora_renderiza(self):
        response = self.client.get(reverse("control_fondos:bitacora"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Bitácora de fondos")

    def test_exportar_movimientos_excel(self):
        response = self.client.get(reverse("control_fondos:exportar_movimientos_excel"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response["Content-Type"],
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
