from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from backup.models import BackupRecord


class BackupViewsTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username="admin_backup_views",
            email="admin_backup_views@example.com",
            password="testpass123",
            is_staff=True,
            is_superuser=True,
        )
        self.client.force_login(self.user)

    @mock.patch("backup.views.get_database_stats")
    def test_dashboard_responde_200(self, mock_stats):
        mock_stats.return_value = {
            "db_size_legible": "1.0 KB",
            "total_tablas": 0,
            "media_size_legible": "0.0 B",
            "media_files": 0,
        }
        response = self.client.get(reverse("backup:dashboard"))
        self.assertEqual(response.status_code, 200)

    @mock.patch("backup.views.get_database_stats")
    def test_dashboard_muestra_historial_de_uso_en_la_tabla(self, mock_stats):
        mock_stats.return_value = {
            "db_size_legible": "1.0 KB",
            "total_tablas": 0,
            "media_size_legible": "0.0 B",
            "media_files": 0,
        }
        BackupRecord.objects.create(
            nombre="backup_historial_ui",
            tipo="completo",
            estado="exitoso",
            ultima_accion="restaurado",
            veces_restaurado=1,
            archivo="c:/tmp/backup_historial_ui.zip",
            tamano=100,
            usuario=self.user,
        )

        response = self.client.get(reverse("backup:dashboard"))

        self.assertContains(response, "Última acción:")
        self.assertContains(response, "Veces usado:")
        self.assertContains(response, "Restaurado")
