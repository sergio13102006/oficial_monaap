from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from clientes.models import Cliente
import uuid


class GestionAlisado(models.Model):
    OPCIONES_SI_NO = [
        ('si', 'Sí'),
        ('no', 'No'),
    ]
    
    MEDIO_PAGO = [
        ('efectivo', 'Efectivo'),
        ('tarjeta', 'Tarjeta'),
        ('medio_virtual', 'Medio Virtual'),
    ]
    
    POROSIDAD = [
        ('alta', 'Alta'),
        ('media', 'Media'),
        ('baja', 'Baja'),
    ]
    
    TEXTURA = [
        ('gruesa', 'Gruesa'),
        ('normal', 'Normal'),
        ('delgada', 'Delgada'),
    ]
    
    FORMA_NATURAL = [
        ('liso', 'Liso'),
        ('ondulado', 'Ondulado'),
        ('rizado', 'Rizado'),
        ('afro', 'Afro'),
    ]
    
    ELASTICIDAD = [
        ('alta', 'Alta'),
        ('media', 'Media'),
        ('baja', 'Baja'),
        ('no_presenta', 'No Presenta'),
    ]
    
    LONGITUD = [
        ('corto', 'Corto'),
        ('medio', 'Medio'),
        ('largo', 'Largo'),
        ('extra_largo', 'Extra Largo'),
    ]
    
    DENSIDAD = [
        ('alta', 'Alta'),
        ('media', 'Media'),
        ('baja', 'Baja'),
    ]
    
    PIEL_CABELLUDO = [
        ('grasa', 'Grasa'),
        ('normal', 'Normal'),
        ('seca', 'Seca'),
    ]
    
    NIVEL_ALOPECIA = [
        ('alta', 'Alta'),
        ('media', 'Media'),
        ('baja', 'Baja'),
        ('no_presenta', 'No Presenta'),
    ]
    
    NIVEL_CAIDA = [
        ('alta', 'Alta'),
        ('media', 'Media'),
        ('baja', 'Baja'),
        ('no_presenta', 'No Presenta'),
    ]
    
    NIVEL_CASPA = [
        ('cronica', 'Crónica'),
        ('media', 'Media'),
        ('baja', 'Baja'),
        ('no_presenta', 'No Presenta'),
    ]
    
    # Identificador único
    id_gestion = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Cliente asociado
    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.PROTECT,
        verbose_name='Cliente',
        related_name='gestiones_alisado',
        null=True,
        blank=True
    )
    
    # Información del servicio y pago
    precio_alisado = models.IntegerField(
        validators=[MinValueValidator(0)],
        verbose_name='Precio del Alisado'
    )
    es_oferta_especial = models.CharField(
        max_length=2,
        choices=OPCIONES_SI_NO,
        default='no',
        verbose_name='¿Es una oferta especial?'
    )
    descripcion_oferta = models.TextField(
        blank=True,
        null=True,
        verbose_name='¿Cuál es la promoción?'
    )
    anticipo_cliente = models.IntegerField(
        validators=[MinValueValidator(0)],
        default=0,
        verbose_name='Anticipo realizado por el cliente'
    )
    medio_pago = models.CharField(
        max_length=20,
        choices=MEDIO_PAGO,
        verbose_name='Medio de pago'
    )
    saldo_pendiente = models.IntegerField(
        validators=[MinValueValidator(0)],
        default=0,
        verbose_name='Saldo pendiente por pagar'
    )
    
    # Información del procedimiento
    procedimiento_realizado_por = models.CharField(
        max_length=200,
        verbose_name='Procedimiento realizado por'
    )
    fecha_hora = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha y Hora'
    )
    tipo_alisado = models.TextField(
        verbose_name='Tipo de alisado a realizar'
    )
    requiere_resellado = models.CharField(
        max_length=2,
        choices=OPCIONES_SI_NO,
        default='no',
        verbose_name='¿Requiere resellado?'
    )
    porcentaje_alisado = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name='Porcentaje de alisado del tratamiento'
    )
    
    # Características del cabello
    porosidad = models.CharField(
        max_length=10,
        choices=POROSIDAD,
        verbose_name='Porosidad'
    )
    textura = models.CharField(
        max_length=10,
        choices=TEXTURA,
        verbose_name='Textura'
    )
    forma_natural = models.CharField(
        max_length=15,
        choices=FORMA_NATURAL,
        verbose_name='Forma Natural'
    )
    elasticidad = models.CharField(
        max_length=15,
        choices=ELASTICIDAD,
        verbose_name='Elasticidad'
    )
    longitud = models.CharField(
        max_length=15,
        choices=LONGITUD,
        verbose_name='Longitud'
    )
    densidad = models.CharField(
        max_length=10,
        choices=DENSIDAD,
        verbose_name='Densidad o Cantidad'
    )
    piel_cabelludo = models.CharField(
        max_length=10,
        choices=PIEL_CABELLUDO,
        verbose_name='Piel Cabelludo'
    )
    alopecia = models.CharField(
        max_length=15,
        choices=NIVEL_ALOPECIA,
        verbose_name='Alopecia'
    )
    caida_cabello = models.CharField(
        max_length=15,
        choices=NIVEL_CAIDA,
        verbose_name='Caída de Cabello'
    )
    
    # Estado de salud y condiciones especiales
    lactante = models.CharField(
        max_length=2,
        choices=OPCIONES_SI_NO,
        verbose_name='¿Lactante?'
    )
    gestante = models.CharField(
        max_length=2,
        choices=OPCIONES_SI_NO,
        verbose_name='¿Gestante?'
    )
    caspa = models.CharField(
        max_length=15,
        choices=NIVEL_CASPA,
        verbose_name='Caspa'
    )
    
    # Procesos químicos
    procesos_tintura = models.BooleanField(default=False, verbose_name='Tintura')
    procesos_decoloracion = models.BooleanField(default=False, verbose_name='Decoloración')
    procesos_ondulados = models.BooleanField(default=False, verbose_name='Ondulados Perm')
    procesos_extracciones = models.BooleanField(default=False, verbose_name='Extracciones')
    procesos_alisados = models.BooleanField(default=False, verbose_name='Alisados')
    procesos_super_aclarante = models.BooleanField(default=False, verbose_name='Super Aclarante')
    procesos_otro = models.TextField(
        blank=True,
        null=True,
        verbose_name='Otro proceso químico'
    )
    
    # Hábitos y cuidados
    cuenta_con_secador = models.CharField(
        max_length=2,
        choices=OPCIONES_SI_NO,
        verbose_name='¿Cuenta con secador?'
    )
    frecuencia_recoge_cabello = models.TextField(
        verbose_name='¿Cada cuánto recoge su cabello?'
    )
    realiza_ejercicio = models.CharField(
        max_length=2,
        choices=OPCIONES_SI_NO,
        verbose_name='¿Realiza ejercicio o algún tipo de deporte?'
    )
    frecuencia_ejercicio = models.TextField(
        blank=True,
        null=True,
        verbose_name='¿Cuántas veces a la semana hace deporte?'
    )
    usa_casco = models.CharField(
        max_length=2,
        choices=OPCIONES_SI_NO,
        verbose_name='¿Debe usar algún casco?'
    )
    productos_capilares = models.TextField(
        verbose_name='Marca shampoo, acondicionador y mascarilla que utiliza'
    )
    se_bana_agua_caliente = models.CharField(
        max_length=2,
        choices=OPCIONES_SI_NO,
        verbose_name='¿Se baña con agua caliente?'
    )
    requiere_refuerzo_15dias = models.CharField(
        max_length=2,
        choices=OPCIONES_SI_NO,
        verbose_name='¿Requiere refuerzo de alisado de 15 días?'
    )
    
    # Información médica
    sufre_tiroides = models.CharField(
        max_length=2,
        choices=OPCIONES_SI_NO,
        verbose_name='¿Sufre de tiroides o toma medicamentos para la tiroides?'
    )
    medicamento_tiroides = models.TextField(
        blank=True,
        null=True,
        verbose_name='¿Qué medicamento?'
    )
    
    # Despunte
    despunte_hoy = models.CharField(
        max_length=2,
        choices=OPCIONES_SI_NO,
        verbose_name='¿Se realizará el día de hoy despunte?'
    )
    
    # Recomendaciones finales
    recomendaciones_post_cuidados = models.TextField(
        verbose_name='Recomendaciones o anotaciones sobre post cuidados'
    )
    
    # Firma del consentimiento
    firma_consentimiento = models.ImageField(
        upload_to='firmas_consentimiento/',
        blank=True,
        null=True,
        verbose_name='Firma del consentimiento informado'
    )
    
    class Meta:
        ordering = ['-fecha_hora']
        verbose_name = 'Gestión de Alisado'
        verbose_name_plural = 'Gestiones de Alisado'
    
    def clean(self):
        super().clean()

        if self.precio_alisado is not None and self.anticipo_cliente is not None:
            saldo_esperado = self.precio_alisado - self.anticipo_cliente
            if saldo_esperado < 0:
                raise ValidationError({
                    'anticipo_cliente': 'El anticipo no puede ser mayor que el precio del alisado.',
                })

            if self.saldo_pendiente is not None and self.saldo_pendiente != saldo_esperado:
                raise ValidationError({
                    'saldo_pendiente': 'El saldo pendiente debe ser igual al precio menos el anticipo.',
                })

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"Alisado - {self.procedimiento_realizado_por} - {self.fecha_hora.strftime('%d/%m/%Y %H:%M')}"
