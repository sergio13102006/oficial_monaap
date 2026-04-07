from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
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
    atencion = models.OneToOneField(
        'AtencionServicio',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='gestion_alisado_detalle',
        verbose_name='Atencion relacionada'
    )
    tratamiento_firmado = models.OneToOneField(
        'TratamientoDatosFirmado',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='gestion_alisado_detalle',
        verbose_name='Tratamiento firmado relacionado'
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


class AtencionServicio(models.Model):
    ESTADO_PENDIENTE = 'pendiente'
    ESTADO_EN_PROCESO = 'en_proceso'
    ESTADO_COMPLETADA = 'completada'
    ESTADO_CANCELADA = 'cancelada'
    ESTADOS_ATENCION = [
        (ESTADO_PENDIENTE, 'Pendiente'),
        (ESTADO_EN_PROCESO, 'En proceso'),
        (ESTADO_COMPLETADA, 'Completada'),
        (ESTADO_CANCELADA, 'Cancelada'),
    ]

    id_atencion = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.PROTECT,
        related_name='atenciones_servicio',
        verbose_name='Cliente relacionado',
    )
    fecha_atencion = models.DateTimeField(default=timezone.now, verbose_name='Fecha de la atencion')
    sede = models.CharField(max_length=150, blank=True, default='', verbose_name='Sede')
    profesional_o_asesor = models.CharField(max_length=200, verbose_name='Profesional o asesor')
    tipo_servicio = models.CharField(max_length=200, verbose_name='Tipo de servicio')
    estado_atencion = models.CharField(
        max_length=20,
        choices=ESTADOS_ATENCION,
        default=ESTADO_PENDIENTE,
        verbose_name='Estado de la atencion',
    )
    observaciones_atencion = models.TextField(blank=True, default='', verbose_name='Observaciones de la atencion')
    usuario_registro = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='atenciones_registradas',
        verbose_name='Usuario que registro',
    )
    tratamiento_completado = models.BooleanField(default=False, verbose_name='Tratamiento completado')
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-fecha_atencion']
        verbose_name = 'Atencion o servicio'
        verbose_name_plural = 'Atenciones o servicios'

    def __str__(self):
        return f"{self.tipo_servicio} - {self.cliente} - {self.fecha_atencion:%d/%m/%Y %H:%M}"


class TratamientoDatosFirmado(models.Model):
    ESTADO_PENDIENTE = 'pendiente'
    ESTADO_ENVIADA = 'enviada_a_tablet'
    ESTADO_ABIERTA = 'abierta_en_tablet'
    ESTADO_FIRMADA = 'firmada'
    ESTADO_CANCELADA = 'cancelada'
    ESTADO_EXPIRADA = 'expirada'
    ESTADO_ERROR = 'error'
    ESTADOS_TRATAMIENTO = [
        (ESTADO_PENDIENTE, 'Pendiente'),
        (ESTADO_ENVIADA, 'Enviada a tablet'),
        (ESTADO_ABIERTA, 'Abierta en tablet'),
        (ESTADO_FIRMADA, 'Firmada'),
        (ESTADO_CANCELADA, 'Cancelada'),
        (ESTADO_EXPIRADA, 'Expirada'),
        (ESTADO_ERROR, 'Error'),
    ]

    id_tratamiento = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.PROTECT,
        related_name='tratamientos_datos',
        verbose_name='Cliente relacionado',
    )
    atencion = models.OneToOneField(
        AtencionServicio,
        on_delete=models.PROTECT,
        related_name='tratamiento_datos',
        verbose_name='Atencion o servicio relacionado',
    )
    fecha_hora_firma = models.DateTimeField(null=True, blank=True, verbose_name='Fecha y hora de firma')
    estado = models.CharField(
        max_length=30,
        choices=ESTADOS_TRATAMIENTO,
        default=ESTADO_PENDIENTE,
        db_index=True,
        verbose_name='Estado',
    )
    texto_tratamiento = models.TextField(verbose_name='Texto exacto del tratamiento firmado')
    version_tratamiento = models.CharField(max_length=50, default='v1', verbose_name='Version del tratamiento')
    ruta_archivo_firma = models.CharField(max_length=255, blank=True, default='', verbose_name='Ruta del archivo de la firma')
    hash_integridad = models.CharField(max_length=128, blank=True, default='', verbose_name='Hash de integridad')
    sede = models.CharField(max_length=150, blank=True, default='', verbose_name='Sede')
    tablet_utilizada = models.CharField(max_length=120, blank=True, default='', verbose_name='Tablet utilizada')
    usuario_inicio_proceso = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tratamientos_iniciados',
        verbose_name='Usuario que inicio el proceso',
    )
    usuario_cierre_proceso = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tratamientos_cerrados',
        verbose_name='Usuario que cerro el proceso',
    )
    snapshot_cliente = models.JSONField(default=dict, verbose_name='Snapshot de datos del cliente')
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-creado_en']
        verbose_name = 'Tratamiento de datos firmado'
        verbose_name_plural = 'Tratamientos de datos firmados'

    @property
    def esta_firmado(self):
        return self.estado == self.ESTADO_FIRMADA and self.fecha_hora_firma is not None

    def marcar_estado(self, estado, *, fecha_hora_firma=None, usuario_cierre=None):
        self.estado = estado
        update_fields = ['estado', 'actualizado_en']
        if fecha_hora_firma is not None:
            self.fecha_hora_firma = fecha_hora_firma
            update_fields.append('fecha_hora_firma')
        if usuario_cierre is not None:
            self.usuario_cierre_proceso = usuario_cierre
            update_fields.append('usuario_cierre_proceso')
        self.save(update_fields=update_fields)

    def clean(self):
        super().clean()
        if self.pk and TratamientoDatosFirmado.objects.filter(pk=self.pk, estado=self.ESTADO_FIRMADA).exists():
            previous = TratamientoDatosFirmado.objects.get(pk=self.pk)
            immutable_fields = [
                'cliente_id',
                'atencion_id',
                'texto_tratamiento',
                'version_tratamiento',
                'ruta_archivo_firma',
                'hash_integridad',
                'sede',
                'tablet_utilizada',
                'snapshot_cliente',
            ]
            for field_name in immutable_fields:
                if getattr(previous, field_name) != getattr(self, field_name):
                    raise ValidationError('Un tratamiento firmado no se puede editar.')

    def __str__(self):
        return f"Tratamiento {self.id_tratamiento} - {self.cliente}"


class TabletConsentToken(models.Model):
    ESTADO_PENDIENTE = 'pendiente'
    ESTADO_ENVIADA = 'enviada_a_tablet'
    ESTADO_ABIERTA = 'abierta_en_tablet'
    ESTADO_FIRMADA = 'firmada'
    ESTADO_CANCELADA = 'cancelada'
    ESTADO_EXPIRADA = 'expirada'
    ESTADO_ERROR = 'error'
    ESTADOS_PROCESO = [
        (ESTADO_PENDIENTE, 'Pendiente'),
        (ESTADO_ENVIADA, 'Enviada a tablet'),
        (ESTADO_ABIERTA, 'Abierta en tablet'),
        (ESTADO_FIRMADA, 'Firmada'),
        (ESTADO_CANCELADA, 'Cancelada'),
        (ESTADO_EXPIRADA, 'Expirada'),
        (ESTADO_ERROR, 'Error'),
    ]

    token = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.CASCADE,
        related_name='tablet_consent_tokens',
        verbose_name='Cliente'
    )
    creado_por = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tablet_consent_tokens_creados',
        verbose_name='Creado por'
    )
    gestion = models.ForeignKey(
        GestionAlisado,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tablet_tokens',
        verbose_name='Gestión relacionada'
    )
    creado_en = models.DateTimeField(auto_now_add=True)
    expira_en = models.DateTimeField()
    abierta_en = models.DateTimeField(null=True, blank=True)
    usado_en = models.DateTimeField(null=True, blank=True)
    activo = models.BooleanField(default=True)
    estado_proceso = models.CharField(
        max_length=30,
        choices=ESTADOS_PROCESO,
        default=ESTADO_PENDIENTE,
        db_index=True,
        verbose_name='Estado del proceso'
    )
    detalle_estado = models.TextField(blank=True, default='', verbose_name='Detalle del estado')

    class Meta:
        verbose_name = 'Token de tablet'
        verbose_name_plural = 'Tokens de tablet'
        ordering = ['-creado_en']

    def esta_vigente(self):
        return self.activo and self.usado_en is None and self.expira_en > timezone.now()

    def marcar_estado(self, estado, *, activo=None, detalle='', abierta_en=None, usado_en=None):
        self.estado_proceso = estado
        if activo is not None:
            self.activo = activo
        if detalle is not None:
            self.detalle_estado = detalle
        if abierta_en is not None:
            self.abierta_en = abierta_en
        if usado_en is not None:
            self.usado_en = usado_en

        update_fields = ['estado_proceso', 'activo', 'detalle_estado']
        if abierta_en is not None:
            update_fields.append('abierta_en')
        if usado_en is not None:
            update_fields.append('usado_en')
        self.save(update_fields=update_fields)

    def __str__(self):
        return f"Tablet token {self.token} - {self.cliente}"


class TabletKioskState(models.Model):
    SINGLETON_ID = 1
    CONEXION_CONECTADA = 'conectada'
    CONEXION_DESCONECTADA = 'desconectada'
    ESTADO_ESPERA = 'waiting'
    ESTADO_LISTO = 'ready'
    ESTADOS_CONEXION = [
        (CONEXION_CONECTADA, 'Conectada'),
        (CONEXION_DESCONECTADA, 'Desconectada'),
    ]
    ESTADOS = [
        (ESTADO_ESPERA, 'En espera'),
        (ESTADO_LISTO, 'Proceso listo'),
    ]

    id = models.PositiveSmallIntegerField(primary_key=True, default=SINGLETON_ID, editable=False)
    tablet_id = models.CharField(max_length=100, default='default-tablet', verbose_name='Identificador de tablet')
    estado = models.CharField(max_length=20, choices=ESTADOS, default=ESTADO_ESPERA)
    conexion_estado = models.CharField(max_length=20, choices=ESTADOS_CONEXION, default=CONEXION_DESCONECTADA)
    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tablet_kiosk_states',
        verbose_name='Cliente'
    )
    token = models.ForeignKey(
        TabletConsentToken,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='kiosk_states',
        verbose_name='Token activo'
    )
    gestion = models.ForeignKey(
        GestionAlisado,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tablet_kiosk_states',
        verbose_name='Gestión'
    )
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)
    ultima_actividad = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Estado de kiosco tablet'
        verbose_name_plural = 'Estado de kiosco tablet'

    @property
    def listo(self):
        return self.estado == self.ESTADO_LISTO and self.token_id is not None

    def marcar_espera(self):
        self.estado = self.ESTADO_ESPERA
        self.cliente = None
        self.token = None
        self.gestion = None
        self.save(update_fields=['estado', 'cliente', 'token', 'gestion', 'actualizado_en'])

    def marcar_listo(self, cliente_obj, token_obj, gestion=None):
        self.estado = self.ESTADO_LISTO
        self.cliente = cliente_obj
        self.token = token_obj
        self.gestion = gestion
        self.save(update_fields=['estado', 'cliente', 'token', 'gestion', 'actualizado_en'])

    def marcar_conectada(self, tablet_id=None):
        self.conexion_estado = self.CONEXION_CONECTADA
        self.ultima_actividad = timezone.now()
        if tablet_id:
            self.tablet_id = tablet_id
            self.save(update_fields=['conexion_estado', 'ultima_actividad', 'tablet_id', 'actualizado_en'])
            return
        self.save(update_fields=['conexion_estado', 'ultima_actividad', 'actualizado_en'])

    def marcar_desconectada(self):
        self.conexion_estado = self.CONEXION_DESCONECTADA
        self.ultima_actividad = timezone.now()
        self.save(update_fields=['conexion_estado', 'ultima_actividad', 'actualizado_en'])

    def touch_actividad(self):
        self.ultima_actividad = timezone.now()
        self.save(update_fields=['ultima_actividad', 'actualizado_en'])
