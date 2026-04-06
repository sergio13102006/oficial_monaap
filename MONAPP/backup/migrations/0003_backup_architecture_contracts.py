from django.db import migrations, models
import django.db.models.deletion


def seed_backup_contract_fields(apps, schema_editor):
    BackupRecord = apps.get_model("backup", "BackupRecord")
    BackupConfig = apps.get_model("backup", "BackupConfig")

    for record in BackupRecord.objects.all().iterator():
        if not record.db_engine:
            record.db_engine = "sqlite"
        if not record.origen:
            record.origen = "local"
        if record.tipo in {"completo", "media"}:
            record.incluye_media = True
        if record.ultima_accion == "fallido":
            record.detalle_error = record.detalle_error or record.notas or ""
        record.save(
            update_fields=[
                "db_engine",
                "origen",
                "incluye_media",
                "detalle_error",
            ]
        )

    for config in BackupConfig.objects.all().iterator():
        if not config.restore_mode_default:
            config.restore_mode_default = "overwrite"
        config.save(
            update_fields=[
                "restore_mode_default",
                "crear_backup_pre_restore",
                "permitir_restore_cross_engine",
                "habilitar_mirror_media",
                "retencion_backups_seguridad",
            ]
        )


class Migration(migrations.Migration):

    dependencies = [
        ("backup", "0002_backuprecord_historial_uso"),
    ]

    operations = [
        migrations.AddField(
            model_name="backuprecord",
            name="backup_padre",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="backups_derivados", to="backup.backuprecord"),
        ),
        migrations.AddField(
            model_name="backuprecord",
            name="checksum",
            field=models.CharField(blank=True, default="", max_length=128, verbose_name="Checksum"),
        ),
        migrations.AddField(
            model_name="backuprecord",
            name="db_engine",
            field=models.CharField(choices=[("sqlite", "SQLite"), ("postgresql", "PostgreSQL")], default="sqlite", max_length=30, verbose_name="Motor de base de datos"),
        ),
        migrations.AddField(
            model_name="backuprecord",
            name="detalle_error",
            field=models.TextField(blank=True, default="", verbose_name="Detalle de error"),
        ),
        migrations.AddField(
            model_name="backuprecord",
            name="es_backup_seguridad",
            field=models.BooleanField(default=False, verbose_name="Es backup de seguridad"),
        ),
        migrations.AddField(
            model_name="backuprecord",
            name="incluye_media",
            field=models.BooleanField(default=False, verbose_name="Incluye media"),
        ),
        migrations.AddField(
            model_name="backuprecord",
            name="origen",
            field=models.CharField(blank=True, default="local", max_length=120, verbose_name="Origen"),
        ),
        migrations.AddField(
            model_name="backupconfig",
            name="crear_backup_pre_restore",
            field=models.BooleanField(default=True, verbose_name="Crear backup antes de restaurar"),
        ),
        migrations.AddField(
            model_name="backupconfig",
            name="habilitar_mirror_media",
            field=models.BooleanField(default=False, verbose_name="Habilitar mirror de media"),
        ),
        migrations.AddField(
            model_name="backupconfig",
            name="permitir_restore_cross_engine",
            field=models.BooleanField(default=False, verbose_name="Permitir restore entre motores"),
        ),
        migrations.AddField(
            model_name="backupconfig",
            name="restore_mode_default",
            field=models.CharField(choices=[("overwrite", "Overwrite"), ("mirror", "Mirror")], default="overwrite", max_length=20, verbose_name="Modo restore por defecto"),
        ),
        migrations.AddField(
            model_name="backupconfig",
            name="retencion_backups_seguridad",
            field=models.PositiveIntegerField(default=3, verbose_name="Retencion backups de seguridad"),
        ),
        migrations.RunPython(seed_backup_contract_fields, migrations.RunPython.noop),
    ]
