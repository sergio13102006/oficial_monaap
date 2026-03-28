from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("personal", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="personal",
            name="rol",
            field=models.CharField(
                choices=[
                    ("Administrador", "Administrador"),
                    ("Auxiliar", "Auxiliar"),
                    ("Colaborador", "Colaborador"),
                    ("Estilista", "Estilista"),
                ],
                default="Colaborador",
                max_length=20,
            ),
        ),
    ]
