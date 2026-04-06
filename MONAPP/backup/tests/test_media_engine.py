import os
import shutil

from django.test import TestCase, override_settings

from backup.services.engines.media_engine import MediaBackupEngine


class MediaEngineTests(TestCase):
    def test_collect_media_files_en_directorio_vacio(self):
        media_root = os.path.join(os.getcwd(), "test_media_engine_empty")
        os.makedirs(media_root, exist_ok=True)
        try:
            with override_settings(MEDIA_ROOT=media_root):
                files = MediaBackupEngine().collect_media_files()
        finally:
            shutil.rmtree(media_root, ignore_errors=True)
        self.assertEqual(files, [])
