"""Utilidades centrales de permisos por rol para el proyecto."""

from dataclasses import dataclass


ROLES_VALIDOS = {"Administrador", "Auxiliar", "Colaborador"}
ROL_ADMIN = "Administrador"
ROL_AUXILIAR = "Auxiliar"
ROL_COLABORADOR = "Colaborador"
ALIAS_ROLES = {
    "administradores": ROL_ADMIN,
    "auxiliares": ROL_AUXILIAR,
    "colaboradores": ROL_COLABORADOR,
}

ROLES_ADMIN_AUX = {ROL_ADMIN, ROL_AUXILIAR}
ROLES_ADMIN_AUX_COL = {ROL_ADMIN, ROL_AUXILIAR, ROL_COLABORADOR}
ROLES_ADMIN = {ROL_ADMIN}


@dataclass(frozen=True)
class PermisoModulo:
    lectura: set[str]
    escritura: set[str]
    eliminacion: set[str]


PERMISOS_MODULOS = {
    "productos": PermisoModulo(ROLES_ADMIN_AUX, ROLES_ADMIN_AUX, ROLES_ADMIN),
    "proveedores": PermisoModulo(ROLES_ADMIN_AUX, ROLES_ADMIN_AUX, ROLES_ADMIN),
    "clientes": PermisoModulo(ROLES_ADMIN_AUX, ROLES_ADMIN_AUX, ROLES_ADMIN),
    "ventas": PermisoModulo(ROLES_ADMIN_AUX, ROLES_ADMIN_AUX, ROLES_ADMIN),
    "personal": PermisoModulo(ROLES_ADMIN_AUX, ROLES_ADMIN_AUX, ROLES_ADMIN),
    "inventario": PermisoModulo(ROLES_ADMIN_AUX, ROLES_ADMIN_AUX, ROLES_ADMIN),
    "compras": PermisoModulo(ROLES_ADMIN_AUX, ROLES_ADMIN_AUX, ROLES_ADMIN),
    "servicios": PermisoModulo(ROLES_ADMIN_AUX, ROLES_ADMIN_AUX, ROLES_ADMIN),
    "productos_web": PermisoModulo(ROLES_ADMIN_AUX, ROLES_ADMIN_AUX, ROLES_ADMIN),
    "promociones": PermisoModulo(ROLES_ADMIN_AUX, ROLES_ADMIN_AUX, ROLES_ADMIN),
    "servicios_web": PermisoModulo(ROLES_ADMIN_AUX, ROLES_ADMIN_AUX, ROLES_ADMIN),
    "usuarios": PermisoModulo(ROLES_ADMIN_AUX, ROLES_ADMIN_AUX, ROLES_ADMIN),
    "notificaciones": PermisoModulo(ROLES_ADMIN_AUX, ROLES_ADMIN_AUX, ROLES_ADMIN),
    "backup": PermisoModulo(ROLES_ADMIN, ROLES_ADMIN, ROLES_ADMIN),
    "gestion_alisados": PermisoModulo(ROLES_ADMIN_AUX_COL, ROLES_ADMIN_AUX_COL, ROLES_ADMIN),
}

PUBLIC_USER_URLS = {
    "login",
    "recuperar",
    "verificar_codigo",
    "nueva_password",
}

USER_PROFILE_URLS = {
    "perfil",
    "logout",
}


def obtener_roles_usuario(user):
    if not getattr(user, "is_authenticated", False):
        return set()
    if getattr(user, "is_superuser", False):
        return {ROL_ADMIN}
    roles = set()
    for nombre in user.groups.values_list("name", flat=True):
        clave = (nombre or "").strip().lower()
        roles.add(ALIAS_ROLES.get(clave, nombre))
    return roles


def es_admin(user):
    return getattr(user, "is_authenticated", False) and (
        getattr(user, "is_superuser", False) or ROL_ADMIN in obtener_roles_usuario(user)
    )


def es_auxiliar(user):
    return getattr(user, "is_authenticated", False) and (
        getattr(user, "is_superuser", False) or ROL_AUXILIAR in obtener_roles_usuario(user)
    )


def es_colaborador(user):
    return getattr(user, "is_authenticated", False) and (
        getattr(user, "is_superuser", False) or ROL_COLABORADOR in obtener_roles_usuario(user)
    )


def tiene_rol(user, *roles):
    if getattr(user, "is_superuser", False):
        return True
    roles_usuario = obtener_roles_usuario(user)
    return bool(roles_usuario.intersection(roles))


def accion_desde_url(url_name: str | None) -> str:
    nombre = (url_name or "").lower()

    if any(clave in nombre for clave in ("eliminar", "delete")):
        return "eliminacion"
    if any(clave in nombre for clave in ("anular", "restaurar")):
        return "eliminacion"
    if any(clave in nombre for clave in ("crear", "nuevo", "editar", "toggle", "desactivar", "reactivar", "cambiar_estado", "marcar_leida")):
        return "escritura"
    return "lectura"


def permisos_para_modulo(modulo: str, accion: str) -> set[str] | None:
    permisos = PERMISOS_MODULOS.get(modulo)
    if not permisos:
        return None
    if accion == "eliminacion":
        return permisos.eliminacion
    if accion == "escritura":
        return permisos.escritura
    return permisos.lectura


def construir_permisos_usuario(user):
    roles = obtener_roles_usuario(user)
    permisos = {}
    for modulo, definicion in PERMISOS_MODULOS.items():
        permisos[modulo] = {
            "ver": bool(roles.intersection(definicion.lectura) or getattr(user, "is_superuser", False)),
            "crear": bool(roles.intersection(definicion.escritura) or getattr(user, "is_superuser", False)),
            "editar": bool(roles.intersection(definicion.escritura) or getattr(user, "is_superuser", False)),
            "eliminar": bool(roles.intersection(definicion.eliminacion) or getattr(user, "is_superuser", False)),
        }

    permisos["roles"] = {
        "es_admin": ROL_ADMIN in roles or getattr(user, "is_superuser", False),
        "es_auxiliar": ROL_AUXILIAR in roles or getattr(user, "is_superuser", False),
        "es_colaborador": ROL_COLABORADOR in roles or getattr(user, "is_superuser", False),
    }
    return permisos
