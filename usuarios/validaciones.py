from datetime import date
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
import re
from .models import PerfilUsuario


def validar_datos_usuario(data, user_id=None):
    """
    Valida los datos de un usuario y su perfil
    
    Args:
        data: diccionario con los datos a validar
        user_id: ID del usuario (None si es creación, ID si es edición)
    
    Returns:
        diccionario con los errores encontrados (vacío si no hay errores)
    """
    errores = {}

    # Extraer y limpiar datos
    tipo_documento = data.get('tipo_documento', '').strip()
    documento = data.get('documento', '').strip()
    first_name = data.get('first_name', '').strip()
    last_name = data.get('last_name', '').strip()
    email = data.get('email', '').strip()
    telefono = data.get('telefono', '').strip()
    whatsapp_key = data.get('whatsapp_key', '').strip()
    fecha_nacimiento_str = data.get('fecha_nacimiento', '').strip()
    username = data.get('username', '').strip()

    # ===============================
    # VALIDACIÓN TIPO DE DOCUMENTO
    # ===============================
    TIPOS_DOCUMENTO_VALIDOS = ['tarjeta_identidad', 'cedula', 'pasaporte', 'otro']
    
    if not tipo_documento:
        errores['tipo_documento'] = 'El tipo de documento es obligatorio.'
    elif tipo_documento not in TIPOS_DOCUMENTO_VALIDOS:
        errores['tipo_documento'] = 'Tipo de documento inválido.'

    # ===============================
    # VALIDACIÓN NÚMERO DE DOCUMENTO
    # ===============================
    if not documento:
        errores['documento'] = 'El número de documento es obligatorio.'
    elif not documento.isdigit():
        errores['documento'] = 'Solo se permiten números.'
    else:
        # Verificar unicidad del documento
        qs = PerfilUsuario.objects.filter(documento=documento)
        if user_id:
            qs = qs.exclude(user__id=user_id)
        if qs.exists():
            errores['documento'] = 'Ya existe otro usuario con este documento.'

    # ===============================
    # VALIDACIÓN NOMBRE
    # ===============================
    if not first_name:
        errores['first_name'] = 'El nombre es obligatorio.'
    elif not re.match(r'^[A-Za-zÁÉÍÓÚáéíóúÑñ\s]+$', first_name):
        errores['first_name'] = 'El nombre solo puede contener letras.'
    elif len(first_name) > 150:
        errores['first_name'] = 'El nombre no puede exceder 150 caracteres.'

    # ===============================
    # VALIDACIÓN APELLIDO
    # ===============================
    if not last_name:
        errores['last_name'] = 'El apellido es obligatorio.'
    elif not re.match(r'^[A-Za-zÁÉÍÓÚáéíóúÑñ\s]+$', last_name):
        errores['last_name'] = 'El apellido solo puede contener letras.'
    elif len(last_name) > 150:
        errores['last_name'] = 'El apellido no puede exceder 150 caracteres.'

    # ===============================
    # VALIDACIÓN EMAIL
    # ===============================
    if not email:
        errores['email'] = 'El correo electrónico es obligatorio.'
    elif '@' not in email or '.' not in email.split('@')[-1]:
        errores['email'] = 'Correo electrónico inválido.'
    else:
        # Verificar unicidad del email
        qs = User.objects.filter(email=email)
        if user_id:
            qs = qs.exclude(id=user_id)
        if qs.exists():
            errores['email'] = 'Ya existe otro usuario con este correo electrónico.'

    # ===============================
    # VALIDACIÓN USERNAME (opcional)
    # ===============================
    if username:
        if not re.match(r'^[A-Za-z0-9_.-]+$', username):
            errores['username'] = 'El nombre de usuario solo puede contener letras, números, guiones y puntos.'
        elif len(username) < 3:
            errores['username'] = 'El nombre de usuario debe tener al menos 3 caracteres.'
        elif len(username) > 150:
            errores['username'] = 'El nombre de usuario no puede exceder 150 caracteres.'
        else:
            # Verificar unicidad del username
            qs = User.objects.filter(username=username)
            if user_id:
                qs = qs.exclude(id=user_id)
            if qs.exists():
                errores['username'] = 'Ya existe otro usuario con este nombre de usuario.'

    # ===============================
    # VALIDACIÓN TELÉFONO (opcional)
    # ===============================
    if telefono:
        if not telefono.isdigit():
            errores['telefono'] = 'El teléfono solo puede contener números.'
        elif len(telefono) != 10:
            errores['telefono'] = 'Debe tener exactamente 10 dígitos.'

    # ===============================
    # VALIDACIÓN WHATSAPP KEY (opcional)
    # ===============================
    if whatsapp_key:
        if not whatsapp_key.isdigit():
            errores['whatsapp_key'] = 'La clave de WhatsApp solo puede contener números.'

    # ===============================
    # VALIDACIÓN FECHA DE NACIMIENTO (opcional)
    # ===============================
    if fecha_nacimiento_str:
        try:
            fecha = date.fromisoformat(fecha_nacimiento_str)
            if fecha > date.today():
                errores['fecha_nacimiento'] = 'La fecha no puede ser futura.'
            
            # Validar edad mínima (opcional, por ejemplo 18 años)
            edad = (date.today() - fecha).days // 365
            if edad < 18:
                errores['fecha_nacimiento'] = 'El usuario debe ser mayor de 18 años.'
        except ValueError:
            errores['fecha_nacimiento'] = 'Fecha inválida.'

    return errores


def validar_password(password1, password2):
    """
    Valida las contraseñas para registro o cambio
    
    Args:
        password1: contraseña
        password2: confirmación de contraseña
    
    Returns:
        diccionario con los errores encontrados
    """
    errores = {}

    if not password1:
        errores['password1'] = 'La contraseña es obligatoria.'
    elif len(password1) < 8:
        errores['password1'] = 'La contraseña debe tener al menos 8 caracteres.'
    elif not re.search(r'[A-Z]', password1):
        errores['password1'] = 'La contraseña debe contener al menos una letra mayúscula.'
    elif not re.search(r'[a-z]', password1):
        errores['password1'] = 'La contraseña debe contener al menos una letra minúscula.'
    elif not re.search(r'[0-9]', password1):
        errores['password1'] = 'La contraseña debe contener al menos un número.'

    if not password2:
        errores['password2'] = 'Debe confirmar la contraseña.'
    elif password1 != password2:
        errores['password2'] = 'Las contraseñas no coinciden.'

    return errores


def validar_rol(rol):
    """
    Valida que el rol sea uno de los permitidos
    
    Args:
        rol: nombre del rol
    
    Returns:
        diccionario con los errores encontrados
    """
    errores = {}
    
    ROLES_VALIDOS = ['Administrador', 'Auxiliar', 'Colaborador']
    
    if not rol:
        errores['rol'] = 'El rol es obligatorio.'
    elif rol not in ROLES_VALIDOS:
        errores['rol'] = 'Rol inválido.'
    
    return errores
