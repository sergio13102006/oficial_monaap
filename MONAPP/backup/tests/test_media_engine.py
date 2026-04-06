import os
import shutil
import tempfile
import zipfile

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

    def test_mirror_elimina_solo_sobrantes_dentro_de_media_root(self):
        media_root = os.path.join(os.getcwd(), "test_media_engine_mirror")
        outside_dir = os.path.join(os.getcwd(), "test_media_engine_outside")
        zip_path = os.path.join(outside_dir, "mirror.zip")
        try:
            os.makedirs(media_root, exist_ok=True)
            os.makedirs(outside_dir, exist_ok=True)
            os.makedirs(os.path.join(media_root, "docs"), exist_ok=True)
            with open(os.path.join(media_root, "docs", "stale.txt"), "w", encoding="utf-8") as fh:
                fh.write("old")
            with open(os.path.join(outside_dir, "outside.txt"), "w", encoding="utf-8") as fh:
                fh.write("outside")
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                zf.writestr("media/docs/keep.txt", "new")

            with override_settings(MEDIA_ROOT=media_root):
                with zipfile.ZipFile(zip_path, "r") as zf:
                    MediaBackupEngine().restore_media_from_zip(zf, ["media/docs/keep.txt"], mode="mirror")

            self.assertFalse(os.path.exists(os.path.join(media_root, "docs", "stale.txt")))
            self.assertTrue(os.path.exists(os.path.join(media_root, "docs", "keep.txt")))
            self.assertTrue(os.path.exists(os.path.join(outside_dir, "outside.txt")))
        finally:
            shutil.rmtree(media_root, ignore_errors=True)
            shutil.rmtree(outside_dir, ignore_errors=True)
