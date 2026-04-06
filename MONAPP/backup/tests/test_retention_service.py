from django.test import TestCase

from backup.models import BackupRecord
from backup.services.retention_service import get_backups_exceeding_limit


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

