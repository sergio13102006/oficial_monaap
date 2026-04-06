from backup.models import BackupConfig


def get_backup_config():
    return BackupConfig.get_config()


def update_backup_config(cleaned_data):
    config = get_backup_config()
    for field in (
        "backup_automatico",
        "frecuencia_horas",
        "max_backups",
        "incluir_media",
        "restore_mode_default",
        "crear_backup_pre_restore",
        "permitir_restore_cross_engine",
        "habilitar_mirror_media",
        "retencion_backups_seguridad",
        "ruta_backups",
    ):
        if field in cleaned_data:
            setattr(config, field, cleaned_data[field])
    config.save()
    return config


def is_auto_backup_enabled():
    return bool(get_backup_config().backup_automatico)


def get_retention_limit():
    return int(get_backup_config().max_backups or 10)


def get_security_retention_limit():
    return int(get_backup_config().retencion_backups_seguridad or 0)
