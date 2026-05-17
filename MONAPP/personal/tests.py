from django.contrib.auth.models import Group
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Personal


class PersonalPasswordChangeTests(TestCase):
    def setUp(self):
        self.user_model = get_user_model()
        self.admin = self.user_model.objects.create_user(
            username="admin-personal",
            email="admin.personal@example.com",
            password="AdminPass123!",
            first_name="Admin",
            last_name="Personal",
        )
        self.admin.is_superuser = True
        self.admin.is_staff = True
        self.admin.save(update_fields=["is_superuser", "is_staff"])

        self.auxiliar = self.user_model.objects.create_user(
            username="aux-personal",
            email="aux.personal@example.com",
            password="AuxPass123!",
            first_name="Aux",
            last_name="Personal",
        )
        grupo_aux = Group.objects.create(name="Auxiliar")
        self.auxiliar.groups.add(grupo_aux)

        self.target_user = self.user_model.objects.create_user(
            username="maria.personal",
            email="maria.personal@example.com",
            password="OldPass123!",
            first_name="Maria",
            last_name="Gomez",
        )
        self.personal = Personal.objects.create(
            tipo_documento="CC",
            numero_documento="123456789",
            nombres="Maria",
            apellidos="Gomez",
            correo="maria.personal@example.com",
            telefono="3001234567",
            rol="Colaborador",
            activo=True,
        )

    def test_admin_can_change_password_from_personal_module(self):
        self.client.force_login(self.admin)
        url = reverse("personal:cambiar_password_personal", args=[self.personal.pk])

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Cambiar contraseña")

        response = self.client.post(
            url,
            {
                "new_password1": "NuevaClave123!",
                "new_password2": "NuevaClave123!",
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)

        self.target_user.refresh_from_db()
        self.assertTrue(self.target_user.check_password("NuevaClave123!"))

    def test_non_admin_cannot_change_password_from_personal_module(self):
        self.client.force_login(self.auxiliar)
        url = reverse("personal:cambiar_password_personal", args=[self.personal.pk])

        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

        response = self.client.post(
            url,
            {
                "new_password1": "OtraClave123!",
                "new_password2": "OtraClave123!",
            },
        )
        self.assertEqual(response.status_code, 403)

        self.target_user.refresh_from_db()
        self.assertTrue(self.target_user.check_password("OldPass123!"))

