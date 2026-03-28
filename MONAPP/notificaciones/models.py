from django.db import models
from django.contrib.auth.models import User


class Notificacion(models.Model):
    """
    Notificación dirigida a un usuario específico.
    Solo se muestra a Administradores y Auxiliares.
    """

    TIPO_CHOICES = [
        ('info',    'Información'),
        ('success', 'Éxito'),
        ('warning', 'Advertencia'),
        ('danger',  'Error / Alerta'),
    ]

    destinatario = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notificaciones',
        help_text='Usuario que recibirá la notificación',
    )

    titulo = models.CharField(
        max_length=120,
        help_text='Título corto de la notificación',
    )

    mensaje = models.TextField(
        help_text='Cuerpo del mensaje',
    )

    tipo = models.CharField(
        max_length=10,
        choices=TIPO_CHOICES,
        default='info',
    )

    # ── NUEVO: marca notificaciones críticas (pepita amarilla en campana) ────
    urgente = models.BooleanField(
        default=False,
        help_text='True para notificaciones críticas como stock en cero',
    )

    leida = models.BooleanField(
        default=False,
        help_text='True cuando el usuario ya la aceptó/leyó',
    )

    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Notificación'
        verbose_name_plural = 'Notificaciones'
        ordering = ['-urgente', '-fecha_creacion']   # urgentes siempre primero

    def __str__(self):
        tag = ' 🚨' if self.urgente else ''
        return f'[{self.tipo.upper()}]{tag} {self.titulo} → {self.destinatario.username}'

    @property
    def icono(self):
        if self.urgente:
            return 'bi-exclamation-octagon-fill'
        iconos = {
            'info':    'bi-info-circle-fill',
            'success': 'bi-check-circle-fill',
            'warning': 'bi-exclamation-triangle-fill',
            'danger':  'bi-x-circle-fill',
        }
        return iconos.get(self.tipo, 'bi-bell-fill')

    @property
    def color_icono(self):
        if self.urgente:
            return '#e74c3c'
        colores = {
            'info':    '#3498db',
            'success': '#27ae60',
            'warning': '#f39c12',
            'danger':  '#e74c3c',
        }
        return colores.get(self.tipo, '#8D604A')