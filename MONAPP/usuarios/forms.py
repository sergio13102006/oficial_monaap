import re

from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User, Group
from core.form_validations import ValidationFormMixin
from .models import PerfilUsuario


_TEXTO_SEGURO_RE = re.compile(r'^[A-Za-zÁÉÍÓÚáéíóúÑñ\s]+$')
_NUMEROS_RE = re.compile(r'^\d+$')


def _texto_seguro(valor):
    return bool(_TEXTO_SEGURO_RE.match((valor or '').strip()))


def _solo_numeros(valor):
    return bool(_NUMEROS_RE.match((valor or '').strip()))


class LoginForm(AuthenticationForm):
    username = forms.CharField(
        label='Documento',
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Número de documento',
            'autofocus': True
        })
    )
    password = forms.CharField(
        label='Contraseña',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ingrese su contraseña',
            'id': 'password'
        })
    )
    remember_me = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
            'id': 'remember_me'
        }),
        label='Recordarme'
    )


class RegistroForm(UserCreationForm):

    ROL_CHOICES = [
        ('Administrador', 'Administrador'),
        ('Auxiliar', 'Auxiliar'),
        ('Colaborador', 'Colaborador'),
    ]

    rol = forms.ChoiceField(
        choices=ROL_CHOICES,
        required=True,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Rol del usuario'
    )

    tipo_documento = forms.ChoiceField(
        choices=[
            ('tarjeta_identidad', 'Tarjeta de Identidad'),
            ('cedula', 'Cédula'),
            ('pasaporte', 'Pasaporte'),
            ('otro', 'Otro'),
        ],
        required=True,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Tipo de Documento'
    )

    documento = forms.CharField(
        max_length=20,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Número de documento',
            'pattern': '[0-9]+',
            'title': 'Solo se permiten números',
            'inputmode': 'numeric',
        }),
        label='Documento'
    )

    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'correo@ejemplo.com'
        })
    )

    first_name = forms.CharField(
        max_length=150,
        required=True,
        label='Nombre',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nombre',
            'pattern': '[a-zA-ZáéíóúÁÉÍÓÚñÑ\\s]+',
            'title': 'Solo se permiten letras y espacios',
        })
    )

    last_name = forms.CharField(
        max_length=150,
        required=True,
        label='Apellido',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Apellido',
            'pattern': '[a-zA-ZáéíóúÁÉÍÓÚñÑ\\s]+',
            'title': 'Solo se permiten letras y espacios',
        })
    )

    telefono = forms.CharField(
        max_length=15,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Teléfono (opcional)',
            'pattern': '[0-9]+',
            'title': 'Solo se permiten números',
            'inputmode': 'numeric',
        }),
        label='Teléfono'
    )

    foto_perfil = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.jpg,.jpeg,.png,.gif,image/jpeg,image/png,image/gif'
        }),
        label='Foto de Perfil'
    )

    whatsapp_key = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ej: 1234567 (obtenida de CallMeBot)',
            'pattern': '[0-9]+',
            'title': 'Solo se permiten números',
            'inputmode': 'numeric',
        }),
        label='CallMeBot API Key',
        help_text='Opcional — para recibir alertas de stock por WhatsApp'
    )

    class Meta:
        model = User
        fields = ['email', 'first_name', 'last_name', 'password1', 'password2']
        widgets = {
            'password1': forms.PasswordInput(attrs={
                'class': 'form-control',
                'placeholder': 'Contraseña'
            }),
            'password2': forms.PasswordInput(attrs={
                'class': 'form-control',
                'placeholder': 'Confirmar contraseña'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.order_fields([
            'tipo_documento', 'documento', 'email',
            'first_name', 'last_name',
            'password1', 'password2',
            'rol', 'telefono', 'whatsapp_key', 'foto_perfil'
        ])

    def clean_documento(self):
        documento = (self.cleaned_data.get('documento') or '').strip()
        if documento:
            if not _solo_numeros(documento):
                raise forms.ValidationError('El documento solo puede contener números.')
            if PerfilUsuario.objects.filter(documento__iexact=documento).exists():
                raise forms.ValidationError('Este documento ya está registrado.')
        return documento

    def clean_email(self):
        email = (self.cleaned_data.get('email') or '').strip()
        if '<' in email or '>' in email:
            raise forms.ValidationError('Correo electrónico inválido.')
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('Este correo electrónico ya está registrado.')
        return email

    def clean_first_name(self):
        first_name = (self.cleaned_data.get('first_name') or '').strip()
        if first_name:
            if not _texto_seguro(first_name):
                raise forms.ValidationError('El nombre solo puede contener letras y espacios.')
        return first_name

    def clean_last_name(self):
        last_name = (self.cleaned_data.get('last_name') or '').strip()
        if last_name:
            if not _texto_seguro(last_name):
                raise forms.ValidationError('El apellido solo puede contener letras y espacios.')
        return last_name

    def clean_telefono(self):
        telefono = (self.cleaned_data.get('telefono') or '').strip()
        if telefono and not _solo_numeros(telefono):
            raise forms.ValidationError('El teléfono solo puede contener números.')
        return telefono

    def clean_whatsapp_key(self):
        whatsapp_key = (self.cleaned_data.get('whatsapp_key') or '').strip()
        if whatsapp_key and not _solo_numeros(whatsapp_key):
            raise forms.ValidationError('La clave de WhatsApp solo puede contener números.')
        return whatsapp_key

    def clean_foto_perfil(self):
        foto = self.cleaned_data.get('foto_perfil')
        if not foto:
            return foto

        nombre = (getattr(foto, 'name', '') or '').lower()
        permitidas = ('.jpg', '.jpeg', '.png', '.gif')
        if not nombre.endswith(permitidas):
            raise forms.ValidationError('Solo se permiten archivos JPG, JPEG, PNG o GIF.')

        return foto

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = self.cleaned_data['documento']
        user.email    = self.cleaned_data['email']

        rol = self.cleaned_data['rol']
        user.is_staff = rol in ['Administrador', 'Auxiliar']

        if commit:
            user.save()

            perfil = user.perfil
            perfil.documento      = self.cleaned_data['documento']
            perfil.tipo_documento = self.cleaned_data['tipo_documento']
            perfil.telefono       = self.cleaned_data.get('telefono', '')
            perfil.whatsapp_key   = self.cleaned_data.get('whatsapp_key', '')

            if self.cleaned_data.get('foto_perfil'):
                perfil.foto_perfil = self.cleaned_data['foto_perfil']

            perfil.save()

            user.groups.clear()
            grupo, _ = Group.objects.get_or_create(name=rol)
            user.groups.add(grupo)

            # ── Enviar email de bienvenida si es Admin o Auxiliar ────────────
            if rol in ['Administrador', 'Auxiliar'] and user.email:
                from notificaciones.email_alertas import enviar_bienvenida
                enviar_bienvenida(
                    nombre   = user.first_name or user.username,
                    rol      = rol,
                    username = user.username,
                    email    = user.email,
                )

        return user

class EditarUsuarioForm(ValidationFormMixin, forms.ModelForm):
    ROL_CHOICES = [
        ('Administrador', 'Administrador'),
        ('Auxiliar', 'Auxiliar'),
        ('Colaborador', 'Colaborador'),
    ]

    rol = forms.ChoiceField(
        choices=ROL_CHOICES,
        required=True,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Rol'
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'is_active']
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'pattern': r'[a-zA-ZáéíóúÁÉÍÓÚñÑ\s]+',
                'title': 'Solo se permiten letras y espacios'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'pattern': r'[a-zA-ZáéíóúÁÉÍÓÚñÑ\s]+',
                'title': 'Solo se permiten letras y espacios'
            }),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True
        self.fields['email'].required = True

        self.fields['rol'].choices = [(str(v), str(l)) for v, l in self.ROL_CHOICES]

        if self.instance.pk:
            grupo = self.instance.groups.first()
            if grupo:
                self.fields['rol'].initial = str(grupo.name)

    def clean_first_name(self):
        first_name = self.cleaned_data.get('first_name', '').strip()
        if not first_name:
            raise forms.ValidationError('El nombre es obligatorio.')
        if not _texto_seguro(first_name):
            raise forms.ValidationError('El nombre solo puede contener letras y espacios.')
        if len(first_name) > 150:
            raise forms.ValidationError('El nombre no puede exceder 150 caracteres.')
        return first_name

    def clean_last_name(self):
        last_name = self.cleaned_data.get('last_name', '').strip()
        if not last_name:
            raise forms.ValidationError('El apellido es obligatorio.')
        if not _texto_seguro(last_name):
            raise forms.ValidationError('El apellido solo puede contener letras y espacios.')
        if len(last_name) > 150:
            raise forms.ValidationError('El apellido no puede exceder 150 caracteres.')
        return last_name

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip()
        if not email:
            raise forms.ValidationError('El correo electrónico es obligatorio.')
        if '<' in email or '>' in email:
            raise forms.ValidationError('Correo electrónico inválido.')
        if '@' not in email or '.' not in email.split('@')[-1]:
            raise forms.ValidationError('Correo electrónico inválido.')
        qs = User.objects.filter(email__iexact=email)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError('Este correo electrónico ya está registrado.')
        return email


class EditarPerfilForm(forms.ModelForm):

    class Meta:
        model = PerfilUsuario
        fields = [
            'tipo_documento',
            'documento',
            'telefono',
            'foto_perfil',
            'whatsapp_key',
        ]
        widgets = {
            'tipo_documento': forms.Select(attrs={
                'class': 'form-control'
            }),
            'documento': forms.TextInput(attrs={
                'class': 'form-control',
                'pattern': '[0-9]+',
                'title': 'Solo se permiten números'
            }),
            'telefono': forms.TextInput(attrs={
                'class': 'form-control',
                'pattern': '[0-9]+',
                'title': 'Solo se permiten números'
            }),
            'foto_perfil': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.jpg,.jpeg,.png,.gif,image/jpeg,image/png,image/gif'
            }),
            'whatsapp_key': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: 1234567 (obtenida de CallMeBot)',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['tipo_documento'].required = True
        self.fields['documento'].required      = True

    def clean_documento(self):
        documento = self.cleaned_data.get('documento', '').strip()
        if not documento:
            raise forms.ValidationError('El número de documento es obligatorio.')
        if not _solo_numeros(documento):
            raise forms.ValidationError('El documento solo puede contener números.')
        qs = PerfilUsuario.objects.filter(documento__iexact=documento)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError('Este documento ya está registrado.')
        return documento

    def clean_telefono(self):
        telefono = self.cleaned_data.get('telefono', '').strip()
        if telefono:
            if not _solo_numeros(telefono):
                raise forms.ValidationError('El teléfono solo puede contener números.')
            if len(telefono) != 10:
                raise forms.ValidationError('El teléfono debe tener exactamente 10 dígitos.')
        return telefono

    def clean_whatsapp_key(self):
        whatsapp_key = (self.cleaned_data.get('whatsapp_key') or '').strip()
        if whatsapp_key and not _solo_numeros(whatsapp_key):
            raise forms.ValidationError('La clave de WhatsApp solo puede contener números.')
        return whatsapp_key

    def clean_foto_perfil(self):
        foto = self.cleaned_data.get('foto_perfil')
        if not foto:
            return foto

        nombre = (getattr(foto, 'name', '') or '').lower()
        if not nombre.endswith(('.jpg', '.jpeg', '.png', '.gif')):
            raise forms.ValidationError('Solo se permiten archivos JPG, JPEG, PNG o GIF.')

        return foto


class UsuarioBusquedaForm(forms.Form):
    """Formulario para búsqueda y filtrado de usuarios"""
    busqueda = forms.CharField(
        required=False,
        label='Buscar por usuario, nombre, email o documento',
        widget=forms.TextInput(attrs={
            'class': 'usuarios-form-control',
            'placeholder': 'Ingrese término de búsqueda'
        })
    )
    filtro = forms.ChoiceField(
        required=False,
        label='Filtrar por',
        choices=[
            ('', 'Todos'),
            ('activo', 'Activos'),
            ('inactivo', 'Inactivos'),
            ('rol_Administrador', 'Administrador'),
            ('rol_Auxiliar', 'Auxiliar'),
            ('rol_Colaborador', 'Colaborador'),
        ],
        widget=forms.Select(attrs={
            'class': 'usuarios-form-control',
            'id': 'id_filtro_usuarios',
            'onchange': 'enviarFormularioFiltro(this.form)'
        })
    )
