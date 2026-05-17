from django.db import migrations, models


def forwards_standardize_operacion(apps, schema_editor):
    CuentaFinanciera = apps.get_model("control_fondos", "CuentaFinanciera")

    for cuenta in CuentaFinanciera.objects.all():
        codigo = (cuenta.codigo or "").upper()
        tipo = (cuenta.tipo or "").upper()

        if tipo == "CAJA_FUERTE" or codigo == "CAJA_FUERTE":
            cuenta.categoria_operativa = "CAJA_FUERTE"
            cuenta.obligatoria_apertura = True
            cuenta.requiere_base_inicial = True
            cuenta.requiere_referencia = False
            cuenta.permite_entradas = True
            cuenta.permite_salidas = True
        elif codigo == "CAJA_PRINCIPAL" or tipo == "EFECTIVO":
            cuenta.categoria_operativa = "CAJA"
            cuenta.obligatoria_apertura = True
            cuenta.requiere_base_inicial = True
            cuenta.requiere_referencia = False
            cuenta.permite_entradas = True
            cuenta.permite_salidas = True
        elif tipo == "BANCO":
            cuenta.categoria_operativa = "BANCO"
            cuenta.obligatoria_apertura = True
            cuenta.requiere_base_inicial = True
            cuenta.requiere_referencia = True
            cuenta.permite_entradas = True
            cuenta.permite_salidas = True
        elif tipo == "BILLETERA":
            cuenta.categoria_operativa = "BILLETERA_DIGITAL"
            cuenta.obligatoria_apertura = True
            cuenta.requiere_base_inicial = True
            cuenta.requiere_referencia = True
            cuenta.permite_entradas = True
            cuenta.permite_salidas = True
        elif tipo == "DATAFONO" or codigo == "DATAFONO":
            cuenta.categoria_operativa = "MEDIO_PAGO"
            cuenta.obligatoria_apertura = False
            cuenta.requiere_base_inicial = False
            cuenta.requiere_referencia = True
            cuenta.permite_entradas = True
            cuenta.permite_salidas = False
        elif tipo == "FINANCIACION" or codigo == "SISTECREDITO_ADDI":
            cuenta.categoria_operativa = "FINANCIACION"
            cuenta.obligatoria_apertura = False
            cuenta.requiere_base_inicial = False
            cuenta.requiere_referencia = True
            cuenta.permite_entradas = True
            cuenta.permite_salidas = False
        elif tipo == "TARJETA" or codigo == "TARJETA_CREDITO_COMPRAS":
            cuenta.categoria_operativa = "EGRESO"
            cuenta.obligatoria_apertura = False
            cuenta.requiere_base_inicial = False
            cuenta.requiere_referencia = True
            cuenta.permite_entradas = False
            cuenta.permite_salidas = True
        else:
            cuenta.categoria_operativa = "OTRA"

        cuenta.save(
            update_fields=[
                "categoria_operativa",
                "obligatoria_apertura",
                "requiere_base_inicial",
                "requiere_referencia",
                "permite_entradas",
                "permite_salidas",
            ]
        )


class Migration(migrations.Migration):

    dependencies = [
        ("control_fondos", "0002_bitacorafondos_remove_jornadadiaria_creada_por_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="cuentafinanciera",
            name="categoria_operativa",
            field=models.CharField(
                choices=[
                    ("CAJA", "Caja"),
                    ("CAJA_FUERTE", "Caja fuerte"),
                    ("BANCO", "Banco"),
                    ("BILLETERA_DIGITAL", "Billetera digital"),
                    ("MEDIO_PAGO", "Medio de pago"),
                    ("FINANCIACION", "Financiación"),
                    ("EGRESO", "Egreso"),
                    ("OTRA", "Otra"),
                ],
                default="CAJA",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="cuentafinanciera",
            name="obligatoria_apertura",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="cuentafinanciera",
            name="requiere_base_inicial",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="cuentafinanciera",
            name="requiere_referencia",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="cuentafinanciera",
            name="permite_entradas",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="cuentafinanciera",
            name="permite_salidas",
            field=models.BooleanField(default=True),
        ),
        migrations.RunPython(forwards_standardize_operacion, migrations.RunPython.noop),
    ]
