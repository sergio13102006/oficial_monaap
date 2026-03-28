from django.core.exceptions import ValidationError
from django.db import models
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
