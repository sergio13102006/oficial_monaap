from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import JSONField
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

class PerfilUsuario(models.Model):
    """
    Modelo para extender la información del usuario
    Relacionado 1:1 con el modelo User de Django
    """
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE,
        related_name='perfil'
    )
    TIPO_DOCUMENTO_CHOICES = [
        ('tarjeta_identidad', 'Tarjeta de Identidad'),
        ('cedula', 'Cédula'),
        ('pasaporte', 'Pasaporte'),
        ('otro', 'Otro'),
    ]
    tipo_documento = models.CharField(
        max_length=30,
        choices=TIPO_DOCUMENTO_CHOICES,
        default='cedula',
        blank=True,
        null=True,
        help_text="Tipo de documento de identidad"
    )
    
    documento = models.CharField(
        max_length=20, 
        unique=True,
        null=True,
        blank=True,
        help_text="Número de documento de identidad"
    )
    
    telefono = models.CharField(
        max_length=15, 
        blank=True,
        help_text="Número de teléfono"
    )
    
    direccion = models.CharField(
        max_length=200, 
        blank=True,
        help_text="Dirección de residencia"
    )
    
    foto_perfil = models.ImageField(
        upload_to='perfiles/', 
        blank=True, 
        null=True,
        help_text="Foto de perfil del usuario"
    )
    
    fecha_nacimiento = models.DateField(
        null=True, 
        blank=True,
        help_text="Fecha de nacimiento"
    )
    
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    # Campos para recuperación de contraseña
    recovery_code = models.CharField(
        max_length=6, 
        blank=True, 
        null=True,
        help_text="Código de recuperación de contraseña"
    )
    
    recovery_code_created = models.DateTimeField(
        blank=True, 
        null=True,
        help_text="Fecha de creación del código de recuperación"
    )
    whatsapp_key = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text='API Key de CallMeBot para recibir alertas por WhatsApp',
        verbose_name='CallMeBot API Key',
    )
    
    class Meta:
        verbose_name = "Perfil de Usuario"
        verbose_name_plural = "Perfiles de Usuarios"
        ordering = ['-user__date_joined']
    
    def __str__(self):
        return f"Perfil de {self.user.username}"
    
    def get_nombre_completo(self):
        """Retorna el nombre completo del usuario"""
        return f"{self.user.first_name} {self.user.last_name}"

    def clean(self):
        super().clean()

        documento = (self.documento or '').strip()
        telefono = (self.telefono or '').strip()
        whatsapp_key = (self.whatsapp_key or '').strip()

        if documento and not documento.isdigit():
            raise ValidationError({'documento': 'El documento solo puede contener números.'})

        if telefono and not telefono.isdigit():
            raise ValidationError({'telefono': 'El teléfono solo puede contener números.'})

        if whatsapp_key and not whatsapp_key.isdigit():
            raise ValidationError({'whatsapp_key': 'La clave de WhatsApp solo puede contener números.'})

        if self.direccion:
            direccion = self.direccion.strip()
            if '<' in direccion or '>' in direccion:
                raise ValidationError({'direccion': 'La dirección contiene caracteres no permitidos.'})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class AuthSecurityState(models.Model):
    SUBJECT_USER = "user"
    SUBJECT_IP = "ip"
    SUBJECT_CHOICES = [
        (SUBJECT_USER, "Usuario"),
        (SUBJECT_IP, "IP"),
    ]

    subject_type = models.CharField(max_length=10, choices=SUBJECT_CHOICES, db_index=True)
    subject_value = models.CharField(max_length=150, db_index=True)
    failed_count = models.PositiveIntegerField(default=0)
    block_level = models.PositiveSmallIntegerField(default=0)
    blocked_until = models.DateTimeField(blank=True, null=True)
    strong_block_until = models.DateTimeField(blank=True, null=True)
    captcha_required_until = models.DateTimeField(blank=True, null=True)
    suspicious_until = models.DateTimeField(blank=True, null=True)
    reputation_score = models.PositiveIntegerField(default=0)
    reputation_expires_at = models.DateTimeField(blank=True, null=True)
    burst_count = models.PositiveIntegerField(default=0)
    burst_strikes = models.PositiveIntegerField(default=0)
    burst_window_started_at = models.DateTimeField(blank=True, null=True)
    burst_block_until = models.DateTimeField(blank=True, null=True)
    last_burst_at = models.DateTimeField(blank=True, null=True)
    last_failed_at = models.DateTimeField(blank=True, null=True)
    last_success_at = models.DateTimeField(blank=True, null=True)
    metadata = JSONField(default=dict, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Estado de seguridad"
        verbose_name_plural = "Estados de seguridad"
        unique_together = ("subject_type", "subject_value")
        indexes = [
            models.Index(fields=["subject_type", "subject_value"]),
            models.Index(fields=["blocked_until"]),
            models.Index(fields=["strong_block_until"]),
            models.Index(fields=["suspicious_until"]),
        ]

    def __str__(self):
        return f"{self.subject_type}:{self.subject_value}"


class AuthSecurityEvent(models.Model):
    EVENT_LOGIN_SUCCESS = "login_success"
    EVENT_LOGIN_FAILED = "login_failed"
    EVENT_LOGIN_BLOCKED = "login_blocked"
    EVENT_CAPTCHA_REQUIRED = "captcha_required"
    EVENT_CAPTCHA_FAILED = "captcha_failed"
    EVENT_LOGOUT = "logout"
    EVENT_RECOVERY_REQUESTED = "recovery_requested"
    EVENT_RECOVERY_CODE_SENT = "recovery_code_sent"
    EVENT_RECOVERY_CODE_FAILED = "recovery_code_failed"
    EVENT_RECOVERY_CODE_VERIFIED = "recovery_code_verified"
    EVENT_PASSWORD_CHANGED = "password_changed"
    EVENT_USERNAME_RECOVERY = "username_recovery"

    EVENT_CHOICES = [
        (EVENT_LOGIN_SUCCESS, "Login exitoso"),
        (EVENT_LOGIN_FAILED, "Login fallido"),
        (EVENT_LOGIN_BLOCKED, "Login bloqueado"),
        (EVENT_CAPTCHA_REQUIRED, "Captcha requerido"),
        (EVENT_CAPTCHA_FAILED, "Captcha fallido"),
        (EVENT_LOGOUT, "Cierre de sesión"),
        (EVENT_RECOVERY_REQUESTED, "Recuperación solicitada"),
        (EVENT_RECOVERY_CODE_SENT, "Código de recuperación enviado"),
        (EVENT_RECOVERY_CODE_FAILED, "Código de recuperación fallido"),
        (EVENT_RECOVERY_CODE_VERIFIED, "Código de recuperación verificado"),
        (EVENT_PASSWORD_CHANGED, "Contraseña cambiada"),
        (EVENT_USERNAME_RECOVERY, "Recuperación de usuario"),
    ]

    event_type = models.CharField(max_length=32, choices=EVENT_CHOICES, db_index=True)
    subject_type = models.CharField(max_length=10, choices=AuthSecurityState.SUBJECT_CHOICES, blank=True, default="")
    subject_value = models.CharField(max_length=150, blank=True, default="")
    user = models.ForeignKey(User, blank=True, null=True, on_delete=models.SET_NULL, related_name="security_events")
    username = models.CharField(max_length=150, blank=True, default="")
    ip_address = models.CharField(max_length=45, db_index=True)
    user_agent = models.CharField(max_length=255, blank=True, default="")
    success = models.BooleanField(default=False)
    details = JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Evento de seguridad"
        verbose_name_plural = "Eventos de seguridad"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["event_type", "created_at"]),
            models.Index(fields=["ip_address", "created_at"]),
            models.Index(fields=["username", "created_at"]),
        ]

    def __str__(self):
        return f"{self.event_type} - {self.ip_address}"


# Señales para crear/actualizar perfil automáticamente
@receiver(post_save, sender=User)
def crear_perfil_usuario(sender, instance, created, **kwargs):
    """
    Crea automáticamente un perfil cuando se crea un usuario
    """
    if created:
        PerfilUsuario.objects.create(user=instance)

@receiver(post_save, sender=User)
def guardar_perfil_usuario(sender, instance, **kwargs):
    """
    Guarda el perfil cuando se guarda el usuario
    """
    if hasattr(instance, 'perfil'):
        instance.perfil.save()
