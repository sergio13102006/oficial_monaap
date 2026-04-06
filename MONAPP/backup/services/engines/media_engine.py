import os

from django.conf import settings

from backup.exceptions import BackupEngineError


class MediaBackupEngine:
    def get_media_root(self):
        return str(getattr(settings, "MEDIA_ROOT", ""))

    def collect_media_files(self):
        media_root = self.get_media_root()
        if not media_root or not os.path.exists(media_root):
            return []
        files = []
        for dirpath, _, filenames in os.walk(media_root):
            for filename in filenames:
                file_path = os.path.join(dirpath, filename)
                files.append(
                    {
                        "file_path": file_path,
                        "arc_name": os.path.join(
                            "media", os.path.relpath(file_path, media_root)
                        ),
                        "size": os.path.getsize(file_path),
                    }
                )
        return files

    def add_media_to_zip(self, zip_file):
        files = self.collect_media_files()
        for item in files:
            zip_file.write(item["file_path"], item["arc_name"])
        return files

    def restore_media_from_zip(self, zip_file, members, mode="overwrite"):
        if mode not in {"overwrite", "mirror"}:
            raise BackupEngineError("Modo de restauración de media no soportado.")
        media_root = self.get_media_root()
        if not media_root:
            return 0
        restored = set()
        total = 0
        from ..validation_service import media_relative_path

        for member in members:
            relative_media = media_relative_path(member)
            if not relative_media:
                continue
            target = os.path.join(media_root, relative_media)
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with zip_file.open(member) as src, open(target, "wb") as dst:
                dst.write(src.read())
            restored.add(os.path.normpath(target))
            total += 1

        if mode == "mirror":
            for dirpath, _, filenames in os.walk(media_root):
                for filename in filenames:
                    filepath = os.path.normpath(os.path.join(dirpath, filename))
                    if filepath not in restored:
                        os.remove(filepath)
        return total

