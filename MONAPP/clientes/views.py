from datetime import date

from django.contrib import messages
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST

from .models import Cliente
from .validaciones import validar_datos_cliente


@login_required
def crear_cliente(request):
    """
    Crea un cliente. 
    - Si es AJAX: devuelve JSON (éxito o errores).
    - Si es POST normal: redirige siempre en éxito. En error renderiza la lista.
    """
    if request.method != 'POST':
        return redirect('clientes:lista')

    datos = request.POST
    errores = validar_datos_cliente(datos)

    es_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    if errores:
        if es_ajax:
            return JsonResponse({
                'success': False,
                'errores': errores
            }, status=400)

        messages.error(request, 'No se pudo registrar el cliente. Por favor verifica los datos.')
        # Al renderizar aquí, si el usuario recarga, el navegador intentará re-enviar el POST.
        # Por eso priorizaremos AJAX en el frontend.
        return render(request, 'clientes/lista_clientes.html', {
            'clientes': Cliente.objects.all(),
            'abrir_modal_cliente': True,
            'errores': errores,
            'datos': datos,
        })

    cliente = Cliente.objects.create(
        tipo_documento=datos['tipo_documento'],
        numero_documento=datos['numero_documento'],
        nombre=datos['nombre'],
        apellido=datos['apellido'],
        fecha_nacimiento=datos['fecha_nacimiento'],
        telefono=datos.get('telefono', ''),
        correo=datos.get('correo', ''),
        estado='activo'
    )

    if es_ajax:
        return JsonResponse({
            'success': True,
            'cliente': {
                'id': cliente.id,
                'nombre': cliente.nombre,
                'apellido': cliente.apellido,
                'numero_documento': cliente.numero_documento
            }
        }, status=201)

    messages.success(request, 'Cliente registrado correctamente.')
    return redirect('clientes:lista')


@login_required
def validar_cliente_ajax(request):
    """
    Vista para validaciones en tiempo real desde el frontend.
    Llama a la lógica de validaciones.py campo por campo.
    """
    if request.method != 'GET':
        return JsonResponse({'error': 'Método no permitido'}, status=405)
    
    # Obtenemos los datos que vienen del input
    datos = request.GET.dict()
    cliente_id = request.GET.get('cliente_id')
    
    # Validamos usando tu lógica existente
    errores = validar_datos_cliente(datos, cliente_id=cliente_id)
    
    # Solo nos interesa devolver los errores de los campos que se enviaron en el GET
    errores_filtrados = {k: v for k, v in errores.items() if k in datos}
    
    return JsonResponse({
        'valido': len(errores_filtrados) == 0,
        'errores': errores_filtrados
    })


@login_required
def editar_cliente(request, cliente_id):
    cliente = get_object_or_404(Cliente, id=cliente_id)
    es_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    if request.method == 'POST':
        datos = request.POST
        errores = validar_datos_cliente(datos, cliente_id=cliente.id)

        if errores:
            if es_ajax:
                return JsonResponse({
                    'success': False,
                    'errores': errores
                }, status=400)
            messages.error(request, 'No se pudieron guardar los cambios.')
            return render(request, 'clientes/editar_cliente.html', {
                'cliente': cliente,
                'errores': errores,
                'datos': datos,
            })

        cliente.tipo_documento = datos['tipo_documento']
        cliente.numero_documento = datos['numero_documento']
        cliente.nombre = datos['nombre']
        cliente.apellido = datos['apellido']
        cliente.fecha_nacimiento = datos['fecha_nacimiento']
        cliente.telefono = datos.get('telefono', '')
        cliente.correo = datos.get('correo', '')
        cliente.estado = datos['estado']
        cliente.save()

        if es_ajax:
            return JsonResponse({'success': True}, status=200)
        messages.success(request, 'Cliente actualizado correctamente.')
        return redirect('clientes:lista')

    if es_ajax:
        return JsonResponse({
            'tipo_documento': cliente.tipo_documento,
            'numero_documento': cliente.numero_documento,
            'nombre': cliente.nombre,
            'apellido': cliente.apellido,
            'fecha_nacimiento': cliente.fecha_nacimiento.isoformat() if cliente.fecha_nacimiento else '',
            'telefono': cliente.telefono or '',
            'correo': cliente.correo or '',
            'estado': cliente.estado,
        })

    return render(request, 'clientes/editar_cliente.html', {
        'cliente': cliente
    })


@login_required
def lista_clientes(request):
    """
    Lista con filtros. NO abre modal por recarga.
    """
    q = request.GET.get('q', '').strip()
    estado = request.GET.get('estado', '').strip()
    edad = request.GET.get('edad', '').strip()
    orden = request.GET.get('orden', '').strip()
    current_sort = request.GET.get('sort', '').strip()
    current_dir = request.GET.get('dir', 'asc').strip().lower()
    if current_dir not in {'asc', 'desc'}:
        current_dir = 'asc'

    clientes = Cliente.objects.all()

    if estado == 'activo':
        clientes = clientes.filter(estado='activo')
    elif estado == 'inactivo':
        clientes = clientes.filter(estado='inactivo')
    else:
        clientes = clientes.filter(estado='activo')

    if q:
        clientes = clientes.filter(
            Q(nombre__icontains=q) |
            Q(apellido__icontains=q) |
            Q(numero_documento__icontains=q) |
            Q(codigo_cliente__icontains=q)
        )

    hoy = date.today()
    if edad == 'menor':
        fecha_limite = date(hoy.year - 18, hoy.month, hoy.day)
        clientes = clientes.filter(fecha_nacimiento__gt=fecha_limite)
    elif edad == 'mayor':
        fecha_limite = date(hoy.year - 18, hoy.month, hoy.day)
        clientes = clientes.filter(fecha_nacimiento__lte=fecha_limite)

    ordenamientos = {
        'codigo_asc': ('codigo_cliente',),
        'codigo_desc': ('-codigo_cliente',),

        'nombre_asc': ('nombre', 'apellido'),
        'nombre_desc': ('-nombre', '-apellido'),

        'apellido_asc': ('apellido', 'nombre'),
        'apellido_desc': ('-apellido', '-nombre'),

        'documento_asc': ('numero_documento',),
        'documento_desc': ('-numero_documento',),

        'telefono_asc': ('telefono',),
        'telefono_desc': ('-telefono',),

        'estado_asc': ('estado', 'nombre'),
        'estado_desc': ('-estado', 'nombre'),

        'fecha_asc': ('fecha_nacimiento',),
        'fecha_desc': ('-fecha_nacimiento',),

        'registro_asc': ('fecha_registro',),
        'registro_desc': ('-fecha_registro',),
    }

    sort_map = {
        'codigo': ('codigo_cliente',),
        'cliente': ('nombre', 'apellido'),
        'documento': ('numero_documento',),
        'telefono': ('telefono',),
        'estado': ('estado', 'nombre', 'apellido'),
        'registro': ('fecha_registro',),
    }

    if current_sort in sort_map:
        order_fields = []
        for field in sort_map[current_sort]:
            order_fields.append(field if current_dir == 'asc' else f'-{field}')
        clientes = clientes.order_by(*order_fields)
    elif orden in ordenamientos:
        clientes = clientes.order_by(*ordenamientos[orden])
    else:
        current_sort = ''

    context = {
        'clientes': clientes,
        'q': q,
        'estado': estado,
        'edad': edad,
        'orden': orden,
        'current_sort': current_sort,
        'current_dir': current_dir,

        'abrir_modal_cliente': False,
        'registro_fallido': False,
        'errores': {},
        'datos': {},

        'mostrar_modal_gestion': False,
        'cliente_creado_id': None,
        'cliente_creado_nombre': "",
    }

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return render(request, 'clientes/lista_clientes_global.html', context)

    return render(request, 'clientes/lista_clientes.html', context)

@login_required
def validar_documento(request):
    numero = (request.GET.get('numero') or '').strip()
    cliente_id = request.GET.get('cliente_id')

    if not numero.isdigit():
        return JsonResponse({'valido': False, 'mensaje': 'Solo números'})

    if not (6 <= len(numero) <= 12):
        return JsonResponse({'valido': False, 'mensaje': 'Debe tener entre 6 y 12 dígitos'})

    # normalizar cliente_id
    if not cliente_id or cliente_id in ('undefined', 'null', ''):
        cliente_id = None
    else:
        try:
            cliente_id = int(cliente_id)
        except ValueError:
            cliente_id = None

    qs = Cliente.objects.filter(numero_documento=numero)

    # si es edición, excluye el mismo cliente
    if cliente_id is not None:
        qs = qs.exclude(id=cliente_id)

    if qs.exists():
        return JsonResponse({
            'valido': False,
            'mensaje': 'Ya existe otro cliente con este documento.'
        })

    return JsonResponse({'valido': True})


@login_required
@require_POST
def eliminar_cliente(request, cliente_id):
    cliente = get_object_or_404(Cliente, id=cliente_id)

    if request.method == 'POST':
        cliente.delete()
        messages.success(request, "Cliente eliminado correctamente.")
        return redirect('clientes:lista')

    # Si alguien entra por GET, lo mandamos a lista (o puedes renderizar confirmación si tienes template)
    return redirect('clientes:lista')

@login_required
@require_POST
def cambiar_estado_cliente(request, cliente_id):
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'mensaje': 'Método no permitido'}, status=405)

    try:
        cliente = Cliente.objects.get(id=cliente_id)
    except Cliente.DoesNotExist:
        return JsonResponse({'ok': False, 'mensaje': 'Cliente no encontrado'}, status=404)

    nuevo_estado = 'inactivo' if cliente.estado == 'activo' else 'activo'
    Cliente.objects.filter(id=cliente_id).update(estado=nuevo_estado)

    return JsonResponse({
        'ok': True,
        'success': True,
        'estado': nuevo_estado,
    })
