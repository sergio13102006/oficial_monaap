from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gestion_alisados', '0004_tabletconsenttoken_estado_proceso'),
    ]

    operations = [
        migrations.AddField(
            model_name='tabletkioskstate',
            name='conexion_estado',
            field=models.CharField(choices=[('conectada', 'Conectada'), ('desconectada', 'Desconectada')], default='desconectada', max_length=20),
        ),
        migrations.AddField(
            model_name='tabletkioskstate',
            name='tablet_id',
            field=models.CharField(default='default-tablet', max_length=100, verbose_name='Identificador de tablet'),
        ),
        migrations.AddField(
            model_name='tabletkioskstate',
            name='ultima_actividad',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
