from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.template.loader import render_to_string
from .models import Personal
from .forms import PersonalForm, PersonalBusquedaForm


def _puede_modificar_personal(user):
    grupos = set(user.groups.values_list("name", flat=True))
    return user.is_superuser or "Administrador" in grupos or "Auxiliar" in grupos


def _respuesta_no_autorizado_personal(request):
    mensaje = "No tienes permisos para modificar personal."
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse({"success": False, "mensaje": mensaje}, status=403)
    messages.error(request, mensaje)
    return redirect("personal:lista_personal")


@login_required
def lista_personal(request):
    """Lista todo el personal con búsqueda y filtrado"""
    q = request.GET.get("q", "").strip()
    current_sort = request.GET.get("sort", "").strip()
    current_dir = request.GET.get("dir", "asc").strip().lower()
    if current_dir not in {"asc", "desc"}:
        current_dir = "asc"
    grupos = list(request.user.groups.values_list("name", flat=True))

    # Verificar si el usuario actual es Administrador (puede eliminar)
    es_administrador = request.user.is_superuser or "Administrador" in grupos

    # Verificar si puede crear/editar (Administrador o Auxiliar)
    puede_modificar = (
        request.user.is_superuser
        or "Administrador" in grupos
        or "Auxiliar" in grupos
    )

    personal_list = Personal.objects.all()
    form = PersonalBusquedaForm(request.GET or None)

    filtro = "todos"
    if form.is_valid() and form.cleaned_data.get("filtro"):
        filtro = form.cleaned_data.get("filtro")
    elif not request.GET:
        # En carga inicial, establecer el valor del formulario
        form = PersonalBusquedaForm(initial={"filtro": "todos"})

    # BUSQUEDA GLOBAL
    if q:
        query_general = (
            Q(numero_documento__icontains=q) |
            Q(nombres__icontains=q) |
            Q(apellidos__icontains=q) |
            Q(telefono__icontains=q) |
            Q(correo__icontains=q)
        )
        # Solo incluir ID si el termino de busqueda es puramente numerico para evitar ValueError
        if q.isdigit():
            query_general |= Q(id=q)
            
        personal_list = personal_list.filter(query_general)

    # FILTRO (Se ignora si el usuario está usando el buscador global activo para garantizar que encuentre lo que busca)
    if not q:
        if filtro == "activo":
            personal_list = personal_list.filter(activo=True)
        elif filtro == "inactivo":
            personal_list = personal_list.filter(activo=False)
        elif filtro.startswith("rol_"):
            rol_valor = filtro.replace("rol_", "")
            personal_list = personal_list.filter(rol=rol_valor)

    # ORDENAMIENTO SEGURO (whitelist)
    sort_map = {
        "id": ("id",),
        "documento": ("numero_documento",),
        "nombres": ("nombres", "apellidos"),
        "telefono": ("telefono",),
        "correo": ("correo",),
        "rol": ("rol", "nombres", "apellidos"),
        "estado": ("activo", "nombres", "apellidos"),
        "fecha": ("fecha_creacion",),
    }

    if current_sort in sort_map:
        order_fields = []
        for field in sort_map[current_sort]:
            order_fields.append(field if current_dir == "asc" else f"-{field}")
        personal_list = personal_list.order_by(*order_fields)
    else:
        current_sort = ""
        personal_list = personal_list.order_by("nombres", "apellidos", "id")

    context = {
        "personal_list": personal_list,
        "form": form,
        "q": q,
        "puede_modificar": puede_modificar,
        "es_administrador": es_administrador,
        "current_sort": current_sort,
        "current_dir": current_dir,
    }

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return render(request, "personal/lista_personal_global.html", context)

    return render(request, "personal/lista_personal.html", context)
@login_required
def crear_personal(request):
    """Crear nuevo personal"""
    # Verificar si es una petición AJAX para cargar el modal
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    if not _puede_modificar_personal(request.user):
        return _respuesta_no_autorizado_personal(request)
    
    if request.method == 'POST':
        form = PersonalForm(request.POST)
        if form.is_valid():
            personal = form.save()
            
            if is_ajax:
                # Respuesta JSON para AJAX
                return JsonResponse({
                    'success': True,
                    'message': f'Personal {personal.nombres} {personal.apellidos} creado exitosamente.'
                })
            else:
                messages.success(request, f'Personal {personal.nombres} {personal.apellidos} creado exitosamente.')
                return redirect('personal:lista_personal')
        else:
            if is_ajax:
                # Renderizar el formulario con errores para el modal
                html_form = render_to_string('personal/_formulario_personal_modal.html', 
                                            {'form': form}, 
                                            request=request)
                return JsonResponse({
                    'success': False,
                    'html_form': html_form
                })
    else:
        form = PersonalForm()
    
    # Si es AJAX y es GET, retornar el HTML del formulario para el modal
    if is_ajax:
        html_form = render_to_string('personal/_formulario_personal_modal.html', 
                                     {'form': form}, 
                                     request=request)
        return JsonResponse({'html_form': html_form})
    
    # Si no es AJAX, mostrar la página completa (comportamiento anterior)
    context = {'form': form, 'titulo': 'Crear Personal'}
    return render(request, 'personal/formulario_personal.html', context)


@login_required
def editar_personal(request, pk):
    """Editar información del personal"""
    personal = get_object_or_404(Personal, pk=pk)
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    if not _puede_modificar_personal(request.user):
        return _respuesta_no_autorizado_personal(request)
    
    if request.method == 'POST':
        form = PersonalForm(request.POST, instance=personal)
        if form.is_valid():
            form.save()
            
            if is_ajax:
                # Respuesta JSON para AJAX
                return JsonResponse({
                    'success': True,
                    'message': f'Personal {personal.nombres} {personal.apellidos} actualizado exitosamente.'
                })
            else:
                messages.success(request, f'Personal {personal.nombres} {personal.apellidos} actualizado exitosamente.')
                return redirect('personal:lista_personal')
        else:
            if is_ajax:
                # Renderizar el formulario con errores para el modal
                html_form = render_to_string('personal/_formulario_personal_modal.html', 
                                            {'form': form, 'personal': personal, 'editando': True}, 
                                            request=request)
                return JsonResponse({
                    'success': False,
                    'html_form': html_form
                })
    else:
        form = PersonalForm(instance=personal)
    
    # Si es AJAX y es GET, retornar el HTML del formulario para el modal
    if is_ajax:
        html_form = render_to_string('personal/_formulario_personal_modal.html', 
                                     {'form': form, 'personal': personal, 'editando': True}, 
                                     request=request)
        return JsonResponse({'html_form': html_form})
    
    # Si no es AJAX, mostrar la página completa (comportamiento anterior)
    context = {
        'form': form,
        'personal': personal,
        'titulo': f'Editar - {personal.nombres} {personal.apellidos}'
    }
    return render(request, 'personal/formulario_personal.html', context)


@login_required

def eliminar_personal(request, pk):
    """Eliminar personal"""
    personal = get_object_or_404(Personal, pk=pk)
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    if not _puede_modificar_personal(request.user):
        return _respuesta_no_autorizado_personal(request)
    
    if request.method == 'POST':
        nombre_completo = f"{personal.nombres} {personal.apellidos}"
        personal.delete()
        
        if is_ajax:
            return JsonResponse({
                'success': True,
                'message': f'Personal {nombre_completo} eliminado exitosamente.'
            })
        else:
            messages.success(request, f'Personal {nombre_completo} eliminado exitosamente.')
            return redirect('personal:lista_personal')
    
    # Si es AJAX y es GET, retornar el HTML del modal de confirmación
    if is_ajax:
        html_content = render_to_string('personal/_confirmar_eliminar_modal.html', 
                                       {'personal': personal}, 
                                       request=request)
        return JsonResponse({'html_content': html_content})
    
    # Si no es AJAX, mostrar la página completa (comportamiento anterior)
    context = {'personal': personal}
    return render(request, 'personal/confirmar_eliminar_personal.html', context)


@login_required
def detalle_personal(request, pk):
    """Ver detalles del personal"""
    grupos = list(request.user.groups.values_list('name', flat=True))
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    
    # Verificar si el usuario actual es Administrador (puede eliminar)
    es_administrador = request.user.is_superuser or 'Administrador' in grupos
    
    # Verificar si puede crear/editar (Administrador o Auxiliar)
    puede_modificar = request.user.is_superuser or 'Administrador' in grupos or 'Auxiliar' in grupos
    
    personal = get_object_or_404(Personal, pk=pk)
    
    # Si es AJAX, retornar el HTML del modal de detalles
    if is_ajax:
        html_content = render_to_string('personal/_detalle_personal_modal.html', 
                                       {
                                           'personal': personal,
                                           'es_administrador': es_administrador,
                                           'puede_modificar': puede_modificar,
                                       }, 
                                       request=request)
        return JsonResponse({'html_content': html_content})
    
    # Si no es AJAX, mostrar la página completa (comportamiento anterior)
    context = {
        'personal': personal,
        'es_administrador': es_administrador,
        'puede_modificar': puede_modificar,
    }
    return render(request, 'personal/detalle_personal.html', context)


@login_required
@require_POST
def toggle_activo_personal(request, pk):
    """Cambiar el estado activo/inactivo del personal mediante AJAX"""
    if request.method == 'POST':
        if not _puede_modificar_personal(request.user):
            return JsonResponse({'success': False, 'mensaje': 'No tienes permisos para modificar personal.'}, status=403)
        personal = get_object_or_404(Personal, pk=pk)
        personal.activo = not personal.activo
        personal.save()
        
        return JsonResponse({
            'success': True,
            'activo': personal.activo,
            'mensaje': f'Personal {personal.nombres} {personal.apellidos} marcado como {"activo" if personal.activo else "inactivo"}.'
        })
    
    return JsonResponse({'success': False, 'mensaje': 'Método no permitido.'}, status=405)


# ==================== VALIDACIONES EN TIEMPO REAL ====================

def validar_documento_personal(request):
    """
    Endpoint para validar documento de personal en tiempo real
    """
    numero = (request.GET.get('numero') or '').strip()
    personal_id = request.GET.get('personal_id')

    # Validar número
    if not numero.isdigit():
        return JsonResponse({'valido': False, 'mensaje': 'Solo números'})

    if not (6 <= len(numero) <= 12):
        return JsonResponse({'valido': False, 'mensaje': 'Debe tener entre 6 y 12 dígitos'})

    # Normalizar personal_id
    if not personal_id or personal_id in ('undefined', 'null', ''):
        personal_id = None
    else:
        try:
            personal_id = int(personal_id)
        except ValueError:
            personal_id = None

    qs = Personal.objects.filter(numero_documento=numero)

    # Si es edición, excluye el mismo personal
    if personal_id is not None:
        qs = qs.exclude(id=personal_id)

    if qs.exists():
        return JsonResponse({
            'valido': False,
            'mensaje': 'Ya existe otro personal con este documento.'
        })

    return JsonResponse({'valido': True})


def validar_email_personal(request):
    """
    Endpoint para validar email de personal en tiempo real
    """
    email = (request.GET.get('email') or '').strip()
    personal_id = request.GET.get('personal_id')

    # Validar formato de email
    from django.core.validators import validate_email
    from django.core.exceptions import ValidationError

    try:
        validate_email(email)
    except ValidationError:
        return JsonResponse({'valido': False, 'mensaje': 'Correo electrónico inválido'})

    # Normalizar personal_id
    if not personal_id or personal_id in ('undefined', 'null', ''):
        personal_id = None
    else:
        try:
            personal_id = int(personal_id)
        except ValueError:
            personal_id = None

    qs = Personal.objects.filter(correo=email)

    # Si es edición, excluye el mismo personal
    if personal_id is not None:
        qs = qs.exclude(id=personal_id)

    if qs.exists():
        return JsonResponse({
            'valido': False,
            'mensaje': 'Ya existe otro personal con este email.'
        })

    return JsonResponse({'valido': True})
