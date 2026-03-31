from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from .models import Personal
import re


def validar_datos_personal(data, personal_id=None):
    """
    Valida los datos de un miembro del personal
    
    Args:
        data: diccionario con los datos a validar
        personal_id: ID del personal (None si es creación, ID si es edición)
    
    Returns:
        diccionario con los errores encontrados (vacío si no hay errores)
    """
    errores = {}

    # Extraer y limpiar datos
    tipo_documento = data.get('tipo_documento', '').strip()
    numero_documento = data.get('numero_documento', '').strip()
    nombres = data.get('nombres', '').strip()
    apellidos = data.get('apellidos', '').strip()
    correo = data.get('correo', '').strip()
    telefono = data.get('telefono', '').strip()
    rol = data.get('rol', '').strip()

    # ===============================
    # VALIDACIÓN NÚMERO DE DOCUMENTO
    # ===============================
    if not numero_documento:
        errores['numero_documento'] = 'El número de documento es obligatorio.'
    elif not numero_documento.isdigit():
        errores['numero_documento'] = 'Solo se permiten números.'
    elif not (6 <= len(numero_documento) <= 12):
        errores['numero_documento'] = 'Debe tener entre 6 y 12 dígitos.'
    else:
        # Verificar unicidad del documento
        qs = Personal.objects.filter(numero_documento=numero_documento)
        if personal_id:
            qs = qs.exclude(id=personal_id)
        if qs.exists():
            errores['numero_documento'] = 'Ya existe otro personal con este documento.'

    # ===============================
    # VALIDACIÓN NOMBRES
    # ===============================
    if not nombres:
        errores['nombres'] = 'Los nombres son obligatorios.'
    elif not re.match(r'^[A-Za-zÁÉÍÓÚáéíóúÑñ\s]+$', nombres):
        errores['nombres'] = 'Los nombres solo pueden contener letras.'
    elif len(nombres) > 150:
        errores['nombres'] = 'Los nombres no pueden exceder 150 caracteres.'

    # ===============================
    # VALIDACIÓN APELLIDOS
    # ===============================
    if not apellidos:
        errores['apellidos'] = 'Los apellidos son obligatorios.'
    elif not re.match(r'^[A-Za-zÁÉÍÓÚáéíóúÑñ\s]+$', apellidos):
        errores['apellidos'] = 'Los apellidos solo pueden contener letras.'
    elif len(apellidos) > 150:
        errores['apellidos'] = 'Los apellidos no pueden exceder 150 caracteres.'

    # ===============================
    # VALIDACIÓN ROL
    # ===============================
    ROLES_VALIDOS = ['Administrador', 'Auxiliar', 'Colaborador']
    
    if not rol:
        errores['rol'] = 'El rol es obligatorio.'
    elif rol not in ROLES_VALIDOS:
        errores['rol'] = 'Rol inválido.'

    # ===============================
    # VALIDACIÓN CORREO
    # ===============================
    if not correo:
        errores['correo'] = 'El correo electrónico es obligatorio.'
    else:
        try:
            validate_email(correo)
            # Verificar unicidad del correo
            qs = Personal.objects.filter(correo=correo)
            if personal_id:
                qs = qs.exclude(id=personal_id)
            if qs.exists():
                errores['correo'] = 'Ya existe otro personal con este correo.'
        except ValidationError:
            errores['correo'] = 'Correo electrónico inválido.'

    # ===============================
    # VALIDACIÓN TELÉFONO
    # ===============================
    if not telefono:
        errores['telefono'] = 'El teléfono es obligatorio.'
    elif not telefono.isdigit():
        errores['telefono'] = 'El teléfono solo puede contener números.'
    elif len(telefono) != 10:
        errores['telefono'] = 'Debe tener exactamente 10 dígitos.'

    return errores
