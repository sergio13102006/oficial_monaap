from .permisos import construir_permisos_usuario


def permisos_usuario(request):
    user = getattr(request, "user", None)
    return {
        "permisos": construir_permisos_usuario(user) if user else {},
    }
