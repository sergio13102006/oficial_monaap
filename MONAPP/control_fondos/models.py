from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone


class CuentaFinanciera(models.Model):
    TIPO_EFECTIVO = "EFECTIVO"
    TIPO_BANCO = "BANCO"
    TIPO_BILLETERA = "BILLETERA"
    TIPO_OTRA = "OTRA"
    TIPOS_CUENTA = [
        (TIPO_EFECTIVO, "Efectivo"),
        (TIPO_BANCO, "Banco"),
        (TIPO_BILLETERA, "Billetera"),
        (TIPO_OTRA, "Otra"),
    ]

    nombre = models.CharField(max_length=120, unique=True)
    tipo = models.CharField(max_length=20, choices=TIPOS_CUENTA, default=TIPO_EFECTIVO)
    activa = models.BooleanField(default=True)
    orden_visual = models.PositiveIntegerField(default=0)
    color = models.CharField(max_length=20, blank=True, default="")
    icono = models.CharField(max_length=50, blank=True, default="")

    class Meta:
        ordering = ["orden_visual", "nombre"]
        verbose_name = "Cuenta financiera"
        verbose_name_plural = "Cuentas financieras"

    def __str__(self):
        return self.nombre


class JornadaDiaria(models.Model):
    ESTADO_ABIERTA = "ABIERTA"
    ESTADO_CERRADA_AUTO = "CERRADA_AUTO"
    ESTADOS = [
        (ESTADO_ABIERTA, "Abierta"),
        (ESTADO_CERRADA_AUTO, "Cerrada automáticamente"),
    ]

    fecha = models.DateField(unique=True)
    estado = models.CharField(max_length=20, choices=ESTADOS, default=ESTADO_ABIERTA)
    creada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="jornadas_financieras_creadas",
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_cierre_auto = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-fecha"]
        verbose_name = "Jornada diaria"
        verbose_name_plural = "Jornadas diarias"

    def __str__(self):
        return f"Jornada {self.fecha:%Y-%m-%d}"


class BaseDiariaCuenta(models.Model):
    jornada = models.ForeignKey(
        JornadaDiaria,
        on_delete=models.PROTECT,
        related_name="bases_cuenta",
    )
    cuenta = models.ForeignKey(
        CuentaFinanciera,
        on_delete=models.PROTECT,
        related_name="bases_diarias",
    )
    base_inicial = models.DecimalField(max_digits=18, decimal_places=0)
    registrada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="bases_financieras_registradas",
    )
    fecha_registro = models.DateTimeField(auto_now_add=True)
    observacion = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["jornada__fecha", "cuenta__orden_visual", "cuenta__nombre"]
        constraints = [
            models.UniqueConstraint(
                fields=["jornada", "cuenta"],
                name="control_fondos_base_diaria_cuenta_unica_por_jornada",
            ),
            models.CheckConstraint(
                condition=Q(base_inicial__gte=0),
                name="control_fondos_base_diaria_base_inicial_no_negativa",
            ),
        ]
        verbose_name = "Base diaria por cuenta"
        verbose_name_plural = "Bases diarias por cuenta"

    def __str__(self):
        return f"{self.cuenta} - {self.jornada.fecha:%Y-%m-%d}"


class MovimientoCuenta(models.Model):
    TIPO_ENTRADA = "ENTRADA"
    TIPO_SALIDA = "SALIDA"
    TIPOS = [
        (TIPO_ENTRADA, "Entrada"),
        (TIPO_SALIDA, "Salida"),
    ]

    CLASE_SERVICIO = "SERVICIO"
    CLASE_COMPRA = "COMPRA"
    CLASE_AJUSTE = "AJUSTE"
    CLASE_TRANSFERENCIA = "TRANSFERENCIA"
    CLASE_ANULACION = "ANULACION"
    CLASE_REVERSA = "REVERSA"
    CLASES = [
        (CLASE_SERVICIO, "Servicio"),
        (CLASE_COMPRA, "Compra"),
        (CLASE_AJUSTE, "Ajuste"),
        (CLASE_TRANSFERENCIA, "Transferencia"),
        (CLASE_ANULACION, "Anulación"),
        (CLASE_REVERSA, "Reversa"),
    ]

    ESTADO_ACTIVO = "ACTIVO"
    ESTADO_ANULADO = "ANULADO"
    ESTADOS = [
        (ESTADO_ACTIVO, "Activo"),
        (ESTADO_ANULADO, "Anulado"),
    ]

    jornada = models.ForeignKey(
        JornadaDiaria,
        on_delete=models.PROTECT,
        related_name="movimientos",
    )
    cuenta = models.ForeignKey(
        CuentaFinanciera,
        on_delete=models.PROTECT,
        related_name="movimientos",
    )
    tipo = models.CharField(max_length=10, choices=TIPOS)
    clase = models.CharField(max_length=20, choices=CLASES)
    valor = models.DecimalField(max_digits=18, decimal_places=0)
    concepto = models.CharField(max_length=255)
    referencia = models.CharField(max_length=120, blank=True, default="")
    fecha_hora = models.DateTimeField(default=timezone.now)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="movimientos_financieros_registrados",
    )
    estado = models.CharField(max_length=10, choices=ESTADOS, default=ESTADO_ACTIVO)
    movimiento_origen = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="movimientos_reversa",
    )
    compra = models.ForeignKey(
        "compras.Compra",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="movimientos_financieros",
    )
    servicio = models.ForeignKey(
        "gestion_alisados.GestionAlisado",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="movimientos_financieros",
    )
    colaborador = models.ForeignKey(
        "personal.Personal",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="movimientos_financieros",
    )
    request_uid = models.CharField(max_length=64, null=True, blank=True, db_index=True)

    class Meta:
        ordering = ["-fecha_hora", "-id"]
        constraints = [
            models.CheckConstraint(
                condition=Q(valor__gt=0),
                name="control_fondos_movimiento_cuenta_valor_mayor_cero",
            ),
            models.UniqueConstraint(
                fields=["request_uid"],
                condition=Q(request_uid__isnull=False),
                name="control_fondos_movimiento_cuenta_request_uid_unico",
            ),
        ]
        verbose_name = "Movimiento de cuenta"
        verbose_name_plural = "Movimientos de cuenta"

    def clean(self):
        super().clean()
        if self.movimiento_origen_id and self.movimiento_origen_id == self.pk:
            raise ValidationError("Un movimiento no puede referenciarse a sí mismo como origen.")

    def __str__(self):
        return f"{self.cuenta} - {self.tipo} - {self.valor}"


class TransferenciaCuenta(models.Model):
    cuenta_origen = models.ForeignKey(
        CuentaFinanciera,
        on_delete=models.PROTECT,
        related_name="transferencias_salientes",
    )
    cuenta_destino = models.ForeignKey(
        CuentaFinanciera,
        on_delete=models.PROTECT,
        related_name="transferencias_entrantes",
    )
    valor = models.DecimalField(max_digits=18, decimal_places=0)
    movimiento_salida = models.OneToOneField(
        MovimientoCuenta,
        on_delete=models.PROTECT,
        related_name="transferencia_salida",
    )
    movimiento_entrada = models.OneToOneField(
        MovimientoCuenta,
        on_delete=models.PROTECT,
        related_name="transferencia_entrada",
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="transferencias_financieras_registradas",
    )
    fecha_hora = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-fecha_hora", "-id"]
        constraints = [
            models.CheckConstraint(
                condition=Q(valor__gt=0),
                name="control_fondos_transferencia_valor_mayor_cero",
            ),
            models.CheckConstraint(
                condition=~Q(cuenta_origen=models.F("cuenta_destino")),
                name="control_fondos_transferencia_cuentas_distintas",
            ),
        ]
        verbose_name = "Transferencia entre cuentas"
        verbose_name_plural = "Transferencias entre cuentas"

    def __str__(self):
        return f"{self.cuenta_origen} -> {self.cuenta_destino} ({self.valor})"
