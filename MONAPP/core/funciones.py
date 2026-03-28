from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages

def solo_admin_required(view_func):
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if request.user.is_authenticated and request.user.groups.filter(name="Administrador").exists():
            return view_func(request, *args, **kwargs)
        messages.error(request, "No tienes permisos para acceder a esta sección.")
        return redirect("core:dashboard")
    return _wrapped

def no_colaborador_required(view_func):
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if request.user.is_authenticated and not request.user.groups.filter(name="Colaborador").exists():
            return view_func(request, *args, **kwargs)
        messages.error(request, "No tienes permisos para acceder a esta sección.")
        return redirect("core:dashboard")
    return _wrapped