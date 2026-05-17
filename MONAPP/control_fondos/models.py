from decimal import Decimal
import re
import unicodedata

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone


ZERO = Decimal("0")


def _normalize_text(value):
    value = (value or "").strip()
    value = " ".join(value.split())
    value = unicodedata.normalize("NFKD", value)
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    return value.lower()


def _build_code(value):
    value = _normalize_text(value)
    value = re.sub(r"[^a-z0-9]+", "_", value)
    value = re.sub(r"_+", "_", value).strip("_")
    return value.upper()


class CuentaFinanciera(models.Model):
    TIPO_EFECTIVO = "EFECTIVO"
    TIPO_BANCO = "BANCO"
    TIPO_BILLETERA = "BILLETERA"
    TIPO_CAJA_FUERTE = "CAJA_FUERTE"
    TIPO_DATAFONO = "DATAFONO"
    TIPO_FINANCIACION = "FINANCIACION"
    TIPO_TARJETA = "TARJETA"
    TIPO_OTRA = "OTRA"
    CATEGORIA_CAJA = "CAJA"
    CATEGORIA_CAJA_FUERTE = "CAJA_FUERTE"
    CATEGORIA_BANCO = "BANCO"
    CATEGORIA_BILLETERA = "BILLETERA_DIGITAL"
    CATEGORIA_MEDIO_PAGO = "MEDIO_PAGO"
    CATEGORIA_FINANCIACION = "FINANCIACION"
    CATEGORIA_EGRESO = "EGRESO"
    CATEGORIA_OTRA = "OTRA"
    TIPOS_CUENTA = [
        (TIPO_EFECTIVO, "Efectivo"),
        (TIPO_BANCO, "Banco"),
        (TIPO_BILLETERA, "Billetera"),
        (TIPO_CAJA_FUERTE, "Caja fuerte"),
        (TIPO_DATAFONO, "Datáfono"),
        (TIPO_FINANCIACION, "Financiación"),
        (TIPO_TARJETA, "Tarjeta"),
        (TIPO_OTRA, "Otra"),
    ]
    CATEGORIAS_OPERATIVAS = [
        (CATEGORIA_CAJA, "Caja"),
        (CATEGORIA_CAJA_FUERTE, "Caja fuerte"),
        (CATEGORIA_BANCO, "Banco"),
        (CATEGORIA_BILLETERA, "Billetera digital"),
        (CATEGORIA_MEDIO_PAGO, "Medio de pago"),
        (CATEGORIA_FINANCIACION, "Financiación"),
        (CATEGORIA_EGRESO, "Egreso"),
        (CATEGORIA_OTRA, "Otra"),
    ]

    codigo = models.CharField(max_length=60, unique=True, null=True, blank=True, db_index=True)
    nombre = models.CharField(max_length=120)
    nombre_normalizado = models.CharField(max_length=160, editable=False, default="", db_index=True)
    tipo = models.CharField(max_length=20, choices=TIPOS_CUENTA, default=TIPO_EFECTIVO)
    categoria_operativa = models.CharField(max_length=20, choices=CATEGORIAS_OPERATIVAS, default=CATEGORIA_CAJA)
    activa = models.BooleanField(default=True)
    obligatoria_apertura = models.BooleanField(default=False)
    requiere_base_inicial = models.BooleanField(default=True)
    requiere_referencia = models.BooleanField(default=False)
    permite_entradas = models.BooleanField(default=True)
    permite_salidas = models.BooleanField(default=True)
    orden_visual = models.PositiveIntegerField(default=0)
    color = models.CharField(max_length=20, blank=True, default="")
    icono = models.CharField(max_length=50, blank=True, default="")

    class Meta:
        ordering = ["orden_visual", "nombre"]
        constraints = [
            models.UniqueConstraint(
                fields=["nombre_normalizado"],
                condition=~Q(nombre_normalizado=""),
                name="control_fondos_cuenta_nombre_normalizado_unico",
            ),
        ]
        verbose_name = "Cuenta financiera"
        verbose_name_plural = "Cuentas financieras"

    def clean(self):
        super().clean()
        self.nombre = " ".join((self.nombre or "").split()).title()
        self.nombre_normalizado = _normalize_text(self.nombre)
        if not self.codigo:
            self.codigo = _build_code(self.nombre)
        self._aplicar_configuracion_por_defecto()

    def save(self, *args, **kwargs):
        self.clean()
        existente = CuentaFinanciera.objects.exclude(pk=self.pk).filter(nombre_normalizado=self.nombre_normalizado).first()
        if existente:
            raise ValidationError({"nombre": "Ya existe una cuenta con un nombre equivalente."})
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nombre

    def _aplicar_configuracion_por_defecto(self):
        tipo = (self.tipo or "").upper()
        codigo = (self.codigo or "").upper()

        if tipo == self.TIPO_CAJA_FUERTE or codigo == "CAJA_FUERTE":
            self.categoria_operativa = self.CATEGORIA_CAJA_FUERTE
            self.requiere_base_inicial = True
            self.obligatoria_apertura = True
            self.permite_entradas = True
            self.permite_salidas = True
            self.requiere_referencia = False
        elif codigo == "CAJA_PRINCIPAL" or tipo == self.TIPO_EFECTIVO:
            self.categoria_operativa = self.CATEGORIA_CAJA
            self.requiere_base_inicial = True
            self.obligatoria_apertura = True
            self.permite_entradas = True
            self.permite_salidas = True
            self.requiere_referencia = False
        elif tipo == self.TIPO_BANCO:
            self.categoria_operativa = self.CATEGORIA_BANCO
            self.requiere_base_inicial = True
            self.obligatoria_apertura = True
            self.permite_entradas = True
            self.permite_salidas = True
            self.requiere_referencia = True
        elif tipo == self.TIPO_BILLETERA:
            self.categoria_operativa = self.CATEGORIA_BILLETERA
            self.requiere_base_inicial = True
            self.obligatoria_apertura = True
            self.permite_entradas = True
            self.permite_salidas = True
            self.requiere_referencia = True
        elif tipo == self.TIPO_DATAFONO or codigo == "DATAFONO":
            self.categoria_operativa = self.CATEGORIA_MEDIO_PAGO
            self.requiere_base_inicial = False
            self.obligatoria_apertura = False
            self.permite_entradas = True
            self.permite_salidas = False
            self.requiere_referencia = True
        elif tipo == self.TIPO_FINANCIACION or codigo == "SISTECREDITO_ADDI":
            self.categoria_operativa = self.CATEGORIA_FINANCIACION
            self.requiere_base_inicial = False
            self.obligatoria_apertura = False
            self.permite_entradas = True
            self.permite_salidas = False
            self.requiere_referencia = True
        elif tipo == self.TIPO_TARJETA or codigo == "TARJETA_CREDITO_COMPRAS":
            self.categoria_operativa = self.CATEGORIA_EGRESO
            self.requiere_base_inicial = False
            self.obligatoria_apertura = False
            self.permite_entradas = False
            self.permite_salidas = True
            self.requiere_referencia = True
        else:
            self.categoria_operativa = self.CATEGORIA_OTRA


class JornadaDiaria(models.Model):
    ESTADO_PENDIENTE_APERTURA = "PENDIENTE_APERTURA"
    ESTADO_APERTURA_INCOMPLETA = "APERTURA_INCOMPLETA"
    ESTADO_ABIERTO = "ABIERTO"
    ESTADO_EN_REVISION = "EN_REVISION"
    ESTADO_CERRADO = "CERRADO"
    ESTADO_REABIERTO = "REABIERTO_CON_AUTORIZACION"
    ESTADO_CERRADA_AUTO = "CERRADO_AUTO"
    ESTADOS = [
        (ESTADO_PENDIENTE_APERTURA, "Pendiente de apertura"),
        (ESTADO_APERTURA_INCOMPLETA, "Apertura incompleta"),
        (ESTADO_ABIERTO, "Abierto"),
        (ESTADO_EN_REVISION, "En revisión"),
        (ESTADO_CERRADO, "Cerrado"),
        (ESTADO_REABIERTO, "Reabierto con autorización"),
        (ESTADO_CERRADA_AUTO, "Cerrado automáticamente"),
    ]

    fecha = models.DateField(unique=True)
    sede = models.CharField(max_length=120, blank=True, default="")
    estado = models.CharField(max_length=30, choices=ESTADOS, default=ESTADO_PENDIENTE_APERTURA)
    responsable_apertura = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="jornadas_financieras_abiertas",
    )
    usuario_cierre = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="jornadas_financieras_cerradas",
    )
    autorizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="jornadas_financieras_autorizadas",
    )
    base_inicial_caja = models.DecimalField(max_digits=18, decimal_places=0, default=ZERO)
    base_inicial_caja_fuerte = models.DecimalField(max_digits=18, decimal_places=0, default=ZERO)
    observacion_apertura = models.TextField(blank=True, default="")
    efectivo_contado_real = models.DecimalField(max_digits=18, decimal_places=0, null=True, blank=True)
    caja_fuerte_contada_real = models.DecimalField(max_digits=18, decimal_places=0, null=True, blank=True)
    transferencias_verificadas = models.DecimalField(max_digits=18, decimal_places=0, null=True, blank=True)
    datofono_verificado = models.DecimalField(max_digits=18, decimal_places=0, null=True, blank=True)
    financiacion_verificada = models.DecimalField(max_digits=18, decimal_places=0, null=True, blank=True)
    diferencia_caja = models.DecimalField(max_digits=18, decimal_places=0, null=True, blank=True)
    diferencia_caja_fuerte = models.DecimalField(max_digits=18, decimal_places=0, null=True, blank=True)
    diferencia_transferencias = models.DecimalField(max_digits=18, decimal_places=0, null=True, blank=True)
    diferencia_datofono = models.DecimalField(max_digits=18, decimal_places=0, null=True, blank=True)
    diferencia_financiacion = models.DecimalField(max_digits=18, decimal_places=0, null=True, blank=True)
    observacion_cierre = models.TextField(blank=True, default="")
    motivo_reapertura = models.TextField(blank=True, default="")
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_cierre = models.DateTimeField(null=True, blank=True)
    fecha_reapertura = models.DateTimeField(null=True, blank=True)

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

    TIPO_MOVIMIENTO_INGRESO = "INGRESO"
    TIPO_MOVIMIENTO_SALIDA = "SALIDA"
    TIPO_MOVIMIENTO_TRANSFERENCIA = "TRANSFERENCIA_INTERNA"
    TIPO_MOVIMIENTO_AJUSTE = "AJUSTE"
    TIPO_MOVIMIENTO_ANULACION = "ANULACION"
    TIPO_MOVIMIENTO_COMPRA_TARJETA = "COMPRA_TARJETA"
    TIPOS_MOVIMIENTO = [
        (TIPO_MOVIMIENTO_INGRESO, "Ingreso"),
        (TIPO_MOVIMIENTO_SALIDA, "Salida"),
        (TIPO_MOVIMIENTO_TRANSFERENCIA, "Transferencia interna"),
        (TIPO_MOVIMIENTO_AJUSTE, "Ajuste"),
        (TIPO_MOVIMIENTO_ANULACION, "Anulación"),
        (TIPO_MOVIMIENTO_COMPRA_TARJETA, "Compra con tarjeta"),
    ]

    ESTADO_ACTIVO = "ACTIVO"
    ESTADO_ANULADO = "ANULADO"
    ESTADO_CORREGIDO = "CORREGIDO"
    ESTADO_PENDIENTE_VALIDACION = "PENDIENTE_VALIDACION"
    ESTADO_RECHAZADO = "RECHAZADO"
    ESTADOS = [
        (ESTADO_ACTIVO, "Activo"),
        (ESTADO_ANULADO, "Anulado"),
        (ESTADO_CORREGIDO, "Corregido"),
        (ESTADO_PENDIENTE_VALIDACION, "Pendiente de validación"),
        (ESTADO_RECHAZADO, "Rechazado"),
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
    tipo_movimiento = models.CharField(max_length=30, choices=TIPOS_MOVIMIENTO, blank=True, default="")
    valor = models.DecimalField(max_digits=18, decimal_places=0)
    valor_total = models.DecimalField(max_digits=18, decimal_places=0, default=ZERO)
    descuento = models.DecimalField(max_digits=18, decimal_places=0, default=ZERO)
    valor_neto = models.DecimalField(max_digits=18, decimal_places=0, default=ZERO)
    concepto = models.CharField(max_length=255, blank=True, default="")
    procedimiento = models.CharField(max_length=180, blank=True, default="")
    producto_servicio = models.CharField(max_length=180, blank=True, default="")
    profesional = models.CharField(max_length=180, blank=True, default="")
    cliente = models.CharField(max_length=180, blank=True, default="")
    entrada_efectivo = models.DecimalField(max_digits=18, decimal_places=0, default=ZERO)
    salida_efectivo = models.DecimalField(max_digits=18, decimal_places=0, default=ZERO)
    bancolombia = models.DecimalField(max_digits=18, decimal_places=0, default=ZERO)
    nequi = models.DecimalField(max_digits=18, decimal_places=0, default=ZERO)
    daviplata = models.DecimalField(max_digits=18, decimal_places=0, default=ZERO)
    nubank = models.DecimalField(max_digits=18, decimal_places=0, default=ZERO)
    datofono = models.DecimalField(max_digits=18, decimal_places=0, default=ZERO)
    sistecredito_addi = models.DecimalField(max_digits=18, decimal_places=0, default=ZERO)
    ingreso_caja_fuerte = models.DecimalField(max_digits=18, decimal_places=0, default=ZERO)
    retiro_caja_fuerte = models.DecimalField(max_digits=18, decimal_places=0, default=ZERO)
    tarjeta_credito_compras = models.DecimalField(max_digits=18, decimal_places=0, default=ZERO)
    motivo_salida = models.CharField(max_length=180, blank=True, default="")
    referencia = models.CharField(max_length=120, blank=True, default="")
    comprobante = models.CharField(max_length=120, blank=True, default="")
    soporte_adjunto = models.FileField(upload_to="control_fondos/soportes/movimientos/", null=True, blank=True)
    observacion = models.TextField(blank=True, default="")
    estado = models.CharField(max_length=30, choices=ESTADOS, default=ESTADO_ACTIVO)
    estado_validacion = models.CharField(max_length=30, choices=ESTADOS, default=ESTADO_PENDIENTE_VALIDACION)
    fecha_validacion = models.DateTimeField(null=True, blank=True)
    usuario_validacion = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="movimientos_financieros_validados",
    )
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
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="movimientos_financieros_registrados",
    )
    request_uid = models.CharField(max_length=64, null=True, blank=True, db_index=True)
    fecha_hora = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-fecha_hora", "-id"]
        constraints = [
            models.CheckConstraint(
                condition=Q(valor__gt=0),
                name="control_fondos_movimiento_cuenta_valor_mayor_cero",
            ),
            models.CheckConstraint(
                condition=Q(valor_total__gte=0),
                name="control_fondos_movimiento_cuenta_valor_total_no_negativo",
            ),
            models.CheckConstraint(
                condition=Q(descuento__gte=0),
                name="control_fondos_movimiento_cuenta_descuento_no_negativo",
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

        if self.valor_total and self.descuento and self.valor_total < self.descuento:
            raise ValidationError("El descuento no puede ser mayor que el valor total.")

        if self.tipo_movimiento in {self.TIPO_MOVIMIENTO_INGRESO, self.TIPO_MOVIMIENTO_TRANSFERENCIA}:
            total_medios = (
                (self.entrada_efectivo or ZERO)
                + (self.bancolombia or ZERO)
                + (self.nequi or ZERO)
                + (self.daviplata or ZERO)
                + (self.nubank or ZERO)
                + (self.datofono or ZERO)
                + (self.sistecredito_addi or ZERO)
            )
            if self.valor_neto and total_medios and total_medios != self.valor_neto:
                raise ValidationError(
                    "El valor neto debe coincidir con la suma de los medios de pago."
                )

        if (
            (self.bancolombia or ZERO)
            or (self.nequi or ZERO)
            or (self.daviplata or ZERO)
            or (self.nubank or ZERO)
            or (self.datofono or ZERO)
            or (self.sistecredito_addi or ZERO)
        ) and not self.referencia:
            raise ValidationError("Las transferencias y pagos electrónicos requieren referencia.")

        if (self.salida_efectivo or ZERO) > ZERO or (self.tarjeta_credito_compras or ZERO) > ZERO:
            if not self.motivo_salida:
                raise ValidationError("Las salidas y compras con tarjeta requieren un motivo.")

    def __str__(self):
        return f"{self.cuenta} - {self.tipo} - {self.valor}"


class TransferenciaCuenta(models.Model):
    ESTADO_PENDIENTE = "PENDIENTE"
    ESTADO_APROBADA = "APROBADA"
    ESTADO_RECHAZADA = "RECHAZADA"
    ESTADOS = [
        (ESTADO_PENDIENTE, "Pendiente"),
        (ESTADO_APROBADA, "Aprobada"),
        (ESTADO_RECHAZADA, "Rechazada"),
    ]

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
    referencia = models.CharField(max_length=120, blank=True, default="")
    comprobante = models.CharField(max_length=120, blank=True, default="")
    soporte_adjunto = models.FileField(upload_to="control_fondos/soportes/transferencias/", null=True, blank=True)
    observacion = models.TextField(blank=True, default="")
    estado = models.CharField(max_length=20, choices=ESTADOS, default=ESTADO_APROBADA)
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
    usuario_validacion = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="transferencias_financieras_validadas",
    )
    fecha_hora = models.DateTimeField(default=timezone.now)
    fecha_validacion = models.DateTimeField(null=True, blank=True)

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

    def clean(self):
        super().clean()
        if self.cuenta_origen_id and self.cuenta_destino_id and self.cuenta_origen_id == self.cuenta_destino_id:
            raise ValidationError("La cuenta origen y la cuenta destino deben ser distintas.")
        if self.valor <= 0:
            raise ValidationError("El valor de la transferencia debe ser mayor que cero.")

    def __str__(self):
        return f"{self.cuenta_origen} -> {self.cuenta_destino} ({self.valor})"


class BitacoraFondos(models.Model):
    accion = models.CharField(max_length=60)
    modelo = models.CharField(max_length=80, blank=True, default="")
    objeto_id = models.CharField(max_length=80, blank=True, default="")
    datos_anteriores = models.JSONField(default=dict, blank=True)
    datos_nuevos = models.JSONField(default=dict, blank=True)
    motivo = models.TextField(blank=True, default="")
    ip = models.GenericIPAddressField(null=True, blank=True)
    dispositivo = models.CharField(max_length=180, blank=True, default="")
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="bitacoras_control_fondos",
    )
    fecha_hora = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-fecha_hora", "-id"]
        verbose_name = "Bitácora de fondos"
        verbose_name_plural = "Bitácora de fondos"

    def __str__(self):
        return f"{self.accion} - {self.modelo} {self.objeto_id}"
