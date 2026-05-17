from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse

from usuarios.forms import IdentifierPasswordResetForm
from usuarios.security import get_client_ip


class UsuariosSecurityTest(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="1001",
            password="Password123",
            email="usuario@example.com",
        )
        self.client.force_login(self.user)

    def test_login_ignora_next_externo(self):
        self.client.logout()
        response = self.client.post(
            reverse("usuarios:login"),
            data={
                "username": "1001",
                "password": "Password123",
                "next": "https://evil.com/phish",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("core:dashboard"))

    def test_logout_requiere_post(self):
        response = self.client.get(reverse("usuarios:logout"))
        self.assertEqual(response.status_code, 405)

    def test_lista_usuarios_requiere_permiso(self):
        response = self.client.get(reverse("usuarios:lista_usuarios"))
        self.assertEqual(response.status_code, 403)

    def test_detalle_usuario_requiere_permiso(self):
        response = self.client.get(
            reverse("usuarios:detalle_usuario", args=[self.user.id]),
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(response.status_code, 403)

    def test_validaciones_requieren_permiso(self):
        response_documento = self.client.get(
            reverse("usuarios:validar_documento"),
            {"documento": "123456"},
        )
        response_email = self.client.get(
            reverse("usuarios:validar_email"),
            {"email": "usuario@example.com"},
        )
        self.assertEqual(response_documento.status_code, 403)
        self.assertEqual(response_email.status_code, 403)

    def test_cambiar_password_solo_admin(self):
        admin = get_user_model().objects.create_user(
            username="admin-1",
            password="Admin12345",
            email="admin@example.com",
            is_staff=True,
            is_superuser=True,
        )
        self.client.force_login(admin)

        target = get_user_model().objects.create_user(
            username="2002",
            password="ViejaClave123",
            email="target@example.com",
        )
        response = self.client.post(
            reverse("usuarios:cambiar_password_usuario", args=[target.id]),
            data={
                "new_password1": "NuevaClave123",
                "new_password2": "NuevaClave123",
            },
        )
        self.assertEqual(response.status_code, 302)
        target.refresh_from_db()
        self.assertTrue(target.check_password("NuevaClave123"))

    def test_auxiliar_no_puede_cambiar_password_de_otros(self):
        grupo = Group.objects.create(name="Auxiliar")
        self.user.is_superuser = False
        self.user.save(update_fields=["is_superuser"])
        self.user.groups.add(grupo)
        self.client.force_login(self.user)

        target = get_user_model().objects.create_user(
            username="3003",
            password="ViejaClave123",
            email="target2@example.com",
        )
        response = self.client.post(
            reverse("usuarios:cambiar_password_usuario", args=[target.id]),
            data={
                "new_password1": "NuevaClave123",
                "new_password2": "NuevaClave123",
            },
        )
        self.assertEqual(response.status_code, 403)

    def test_recovery_form_no_enumera(self):
        form = IdentifierPasswordResetForm(data={"email": "noexiste@example.com"})
        self.assertTrue(form.is_valid(), form.errors.as_json())

    @override_settings(DEBUG=False, LOGIN_SECURITY_FORCE_CAPTCHA=True, LOGIN_RECAPTCHA_SITE_KEY="", LOGIN_RECAPTCHA_SECRET_KEY="")
    def test_login_sin_captcha_configurado_no_rompe(self):
        self.client.logout()
        response = self.client.post(
            reverse("usuarios:login"),
            data={
                "username": "1001",
                "password": "Password123",
                "ajax_login": "1",
            },
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(response.status_code, 503)
        self.assertJSONEqual(
            response.content.decode("utf-8"),
            {
                "success": False,
                "message": "La verificación de seguridad no está configurada.",
                "blocked": True,
                "blocked_minutes": 0,
                "attempts": 0,
                "captcha_required": True,
                "captcha_site_key": "",
            },
        )

    @override_settings(LOGIN_TRUSTED_PROXY_IPS=["10.0.0.1"])
    def test_get_client_ip_respeta_proxy_confiable(self):
        request = RequestFactory().get(
            "/",
            HTTP_X_FORWARDED_FOR="203.0.113.10, 10.0.0.1",
            REMOTE_ADDR="10.0.0.1",
        )
        self.assertEqual(get_client_ip(request), "203.0.113.10")

    def test_get_client_ip_ignora_forwarded_no_confiable(self):
        request = RequestFactory().get(
            "/",
            HTTP_X_FORWARDED_FOR="203.0.113.10, 10.0.0.1",
            REMOTE_ADDR="198.51.100.20",
        )
        self.assertEqual(get_client_ip(request), "198.51.100.20")
