from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("Productos", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="producto",
            name="unidad_medida",
            field=models.CharField(
                choices=[
                    ("unidad", "Unidad"),
                    ("kg", "Kilogramo"),
                    ("g", "Gramo"),
                    ("litro", "Litro"),
                    ("ml", "Mililitro"),
                    ("caja", "Caja"),
                    ("paquete", "Paquete"),
                    ("metro", "Metro"),
                ],
                max_length=45,
                verbose_name="Unidad de Medida",
            ),
        ),
        migrations.RemoveField(
            model_name="producto",
            name="imagen_url",
        ),
    ]
