from django.db import migrations, models


def poblar_historial_uso(apps, schema_editor):
    BackupRecord = apps.get_model("backup", "BackupRecord")
    for record in BackupRecord.objects.all().iterator():
        if record.estado == "restaurado":
            record.ultima_accion = "restaurado"
            if not record.veces_restaurado:
                record.veces_restaurado = 1
            if not record.fecha_ultima_restauracion:
                record.fecha_ultima_restauracion = record.fecha_creacion
        elif record.estado == "fallido":
            record.ultima_accion = "fallido"
        else:
            record.ultima_accion = "creado"
        record.save(update_fields=["ultima_accion", "veces_restaurado", "fecha_ultima_restauracion"])


class Migration(migrations.Migration):

    dependencies = [
        ("backup", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="backuprecord",
            name="ultima_accion",
            field=models.CharField(
                choices=[
                    ("creado", "Creado"),
                    ("importado", "Importado"),
                    ("restaurado", "Restaurado"),
                    ("fallido", "Fallido"),
                ],
                default="creado",
                max_length=20,
                verbose_name="Ultima accion",
            ),
        ),
        migrations.AddField(
            model_name="backuprecord",
            name="veces_restaurado",
            field=models.PositiveIntegerField(default=0, verbose_name="Veces restaurado"),
        ),
        migrations.AddField(
            model_name="backuprecord",
            name="fecha_ultima_restauracion",
            field=models.DateTimeField(blank=True, null=True, verbose_name="Fecha ultima restauracion"),
        ),
        migrations.RunPython(poblar_historial_uso, migrations.RunPython.noop),
    ]
