from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from control_fondos.models import CuentaFinanciera


class CompraViewsTest(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="compras_admin",
            password="12345678",
            is_superuser=True,
        )
        CuentaFinanciera.objects.create(
            nombre="Caja Principal",
            tipo=CuentaFinanciera.TIPO_EFECTIVO,
            activa=True,
            orden_visual=1,
        )
        self.client.force_login(self.user)

    def test_crear_compra_renderiza_formulario_con_cuenta_financiera(self):
        response = self.client.get(reverse("compras:crear_compra"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Cuenta financiera")
        self.assertContains(response, "Guardar compra")
