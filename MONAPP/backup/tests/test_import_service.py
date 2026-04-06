from types import SimpleNamespace
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from backup.models import BackupRecord
from backup.services.import_service import import_backup


class ImportarBackupViewTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username="admin_backup",
            email="admin@example.com",
            password="testpass123",
            is_staff=True,
            is_superuser=True,
        )
        self.client.force_login(self.user)

    @mock.patch("backup.views.restore_backup")
    @mock.patch("backup.views.import_backup")
    def test_importar_con_restauracion_ejecuta_ambos_pasos(
        self,
        mock_importar,
        mock_restaurar,
    ):
        record = SimpleNamespace(nombre="backup_prueba", archivo="/tmp/backup_prueba.zip")
        mock_importar.return_value = record

        archivo = SimpleUploadedFile(
            "backup_prueba.zip",
            b"contenido-falso",
            content_type="application/zip",
        )

        response = self.client.post(
            reverse("backup:importar"),
            {
                "archivo_backup": archivo,
                "notas": "Prueba",
                "restaurar_despues": "on",
            },
        )

        self.assertEqual(response.status_code, 302)
        mock_importar.assert_called_once()
        mock_restaurar.assert_called_once()

    @mock.patch("backup.views.restore_backup")
    @mock.patch("backup.views.import_backup")
    def test_importar_sin_restauracion_solo_registra_el_backup(
        self,
        mock_importar,
        mock_restaurar,
    ):
        record = SimpleNamespace(nombre="backup_prueba", archivo="/tmp/backup_prueba.zip")
        mock_importar.return_value = record

        archivo = SimpleUploadedFile(
            "backup_prueba.zip",
            b"contenido-falso",
            content_type="application/zip",
        )

        response = self.client.post(
            reverse("backup:importar"),
            {
                "archivo_backup": archivo,
                "notas": "Prueba",
            },
        )

        self.assertEqual(response.status_code, 302)
        mock_importar.assert_called_once()
        mock_restaurar.assert_not_called()

    def test_importacion_invalida_no_contamina_historial(self):
        archivo = SimpleUploadedFile(
            "backup_prueba.txt",
            b"contenido-falso",
            content_type="text/plain",
        )

        with self.assertRaises(Exception):
            import_backup(archivo, usuario=self.user, notas="fallo")

        self.assertEqual(BackupRecord.objects.count(), 0)
