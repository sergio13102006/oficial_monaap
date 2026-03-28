from datetime import date

from .models import Cliente


def _solo_letras_y_espacios(valor):
    valor = (valor or "").strip()
    return bool(valor) and all(ch.isalpha() or ch.isspace() for ch in valor)


def _solo_numeros(valor):
    valor = (valor or "").strip()
    return bool(valor) and valor.isdigit()


def _sin_signos_peligrosos(valor):
    valor = (valor or "").strip()
    return "<" not in valor and ">" not in valor


def _correo_seguro(correo):
    correo = (correo or "").strip()
    if not correo:
        return False

    if not all(ch.isalnum() or ch in "._-@" for ch in correo):
        return False

    partes = correo.split("@")
    if len(partes) != 2:
        return False

    usuario, dominio = partes
    if not usuario or not dominio or "." not in dominio:
        return False

    if usuario.startswith(".") or usuario.endswith("."):
        return False

    if dominio.startswith(".") or dominio.endswith("."):
        return False

    if ".." in correo:
        return False

    return True


def validar_datos_cliente(data, cliente_id=None):
    errores = {}

    tipo_documento = data.get('tipo_documento', '').strip()
    numero_documento = data.get('numero_documento', '').strip()
    nombre = data.get('nombre', '').strip()
    apellido = data.get('apellido', '').strip()
    fecha_nacimiento_str = data.get('fecha_nacimiento', '').strip()
    telefono = data.get('telefono', '').strip()
    correo = data.get('correo', '').strip()

    if not tipo_documento:
        errores['tipo_documento'] = 'El tipo de documento es obligatorio.'

    if not numero_documento:
        errores['numero_documento'] = 'El número de documento es obligatorio.'
    elif not _sin_signos_peligrosos(numero_documento):
        errores['numero_documento'] = 'El número de documento no puede contener signos especiales.'
    elif not _solo_numeros(numero_documento):
        errores['numero_documento'] = 'Solo se permiten números.'
    elif not (6 <= len(numero_documento) <= 12):
        errores['numero_documento'] = 'Debe tener entre 6 y 12 dígitos.'
    else:
        qs = Cliente.objects.filter(numero_documento=numero_documento)
        if cliente_id:
            qs = qs.exclude(id=cliente_id)
        if qs.exists():
            errores['numero_documento'] = 'Ya existe otro cliente con este documento.'

    if not nombre:
        errores['nombre'] = 'El nombre es obligatorio.'
    elif not _sin_signos_peligrosos(nombre):
        errores['nombre'] = 'El nombre no puede contener signos especiales.'
    elif not _solo_letras_y_espacios(nombre):
        errores['nombre'] = 'El nombre solo puede contener letras y espacios.'

    if not apellido:
        errores['apellido'] = 'El apellido es obligatorio.'
    elif not _sin_signos_peligrosos(apellido):
        errores['apellido'] = 'El apellido no puede contener signos especiales.'
    elif not _solo_letras_y_espacios(apellido):
        errores['apellido'] = 'El apellido solo puede contener letras y espacios.'

    if not fecha_nacimiento_str:
        errores['fecha_nacimiento'] = 'La fecha de nacimiento es obligatoria.'
    else:
        try:
            fecha = date.fromisoformat(fecha_nacimiento_str)
            if fecha > date.today():
                errores['fecha_nacimiento'] = 'La fecha no puede ser futura.'
        except ValueError:
            errores['fecha_nacimiento'] = 'Fecha inválida.'

    if telefono:
        if not _sin_signos_peligrosos(telefono):
            errores['telefono'] = 'El teléfono no puede contener signos especiales.'
        elif not _solo_numeros(telefono):
            errores['telefono'] = 'El teléfono solo puede contener números.'
        elif len(telefono) != 10:
            errores['telefono'] = 'Debe tener exactamente 10 dígitos.'

    if correo:
        if not _sin_signos_peligrosos(correo) or not _correo_seguro(correo):
            errores['correo'] = 'Correo electrónico inválido.'

    return errores
