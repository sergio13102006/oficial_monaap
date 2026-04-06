from django.db import migrations, models


def seed_estado_proceso(apps, schema_editor):
    TabletConsentToken = apps.get_model('gestion_alisados', 'TabletConsentToken')

    for token in TabletConsentToken.objects.all():
        if token.usado_en:
            token.estado_proceso = 'firmada'
            token.detalle_estado = token.detalle_estado or 'Consentimiento firmado correctamente.'
        elif token.activo:
            token.estado_proceso = 'enviada_a_tablet'
            token.detalle_estado = token.detalle_estado or 'Sesion enviada a la tablet y pendiente de apertura.'
        else:
            token.estado_proceso = 'cancelada'
            token.detalle_estado = token.detalle_estado or 'Sesion cerrada sin firma registrada.'
        token.save(update_fields=['estado_proceso', 'detalle_estado'])


class Migration(migrations.Migration):

    dependencies = [
        ('gestion_alisados', '0003_tabletkioskstate'),
    ]

    operations = [
        migrations.AddField(
            model_name='tabletconsenttoken',
            name='abierta_en',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='tabletconsenttoken',
            name='detalle_estado',
            field=models.TextField(blank=True, default='', verbose_name='Detalle del estado'),
        ),
        migrations.AddField(
            model_name='tabletconsenttoken',
            name='estado_proceso',
            field=models.CharField(choices=[('pendiente', 'Pendiente'), ('enviada_a_tablet', 'Enviada a tablet'), ('abierta_en_tablet', 'Abierta en tablet'), ('firmada', 'Firmada'), ('cancelada', 'Cancelada'), ('expirada', 'Expirada'), ('error', 'Error')], db_index=True, default='pendiente', max_length=30, verbose_name='Estado del proceso'),
        ),
        migrations.RunPython(seed_estado_proceso, migrations.RunPython.noop),
    ]
