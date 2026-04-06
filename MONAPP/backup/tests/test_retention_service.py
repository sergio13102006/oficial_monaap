from django.test import TestCase

from backup.models import BackupConfig, BackupRecord
from backup.services.retention_service import apply_retention_policy, get_backups_exceeding_limit


class RetentionServiceTests(TestCase):
    def test_detecta_excedentes_sobre_el_limite(self):
        for idx in range(3):
            BackupRecord.objects.create(
                nombre=f"backup_{idx}",
                tipo="completo",
                estado="exitoso",
                archivo=f"/tmp/backup_{idx}.zip",
            )
        excedentes, keep_ids = get_backups_exceeding_limit(limit=2)
        self.assertEqual(excedentes.count(), 1)
        self.assertEqual(len(keep_ids), 2)

    def test_retencion_conserva_ultimo_backup_valido_y_backups_seguridad_recientes(self):
        config = BackupConfig.get_config()
        config.max_backups = 1
        config.retencion_backups_seguridad = 1
        config.save()

        old_success = BackupRecord.objects.create(
            nombre="old_success",
            tipo="completo",
            estado="exitoso",
            archivo="old_success.zip",
        )
        BackupRecord.objects.create(
            nombre="old_security",
            tipo="completo",
            estado="exitoso",
            archivo="old_security.zip",
            es_backup_seguridad=True,
        )
        recent_security = BackupRecord.objects.create(
            nombre="recent_security",
            tipo="completo",
            estado="exitoso",
            archivo="recent_security.zip",
            es_backup_seguridad=True,
        )

        result = apply_retention_policy(limit=1)

        self.assertFalse(BackupRecord.objects.filter(pk=old_success.pk).exists())
        self.assertTrue(BackupRecord.objects.filter(pk=recent_security.pk).exists())
        self.assertEqual(result["errores"], [])
