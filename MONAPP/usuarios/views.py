import re
import socket
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User, Group
from django.contrib import messages
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST
from django.core.cache import cache
from django.db.models import Q
from django.http import JsonResponse
from django.template.loader import render_to_string
from .forms import LoginForm, RegistroForm, EditarUsuarioForm, EditarPerfilForm, UsuarioBusquedaForm
from .models import PerfilUsuario
import random
import smtplib
from django.utils import timezone
from django.core.mail import send_mail
from datetime import timedelta, datetime
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.urls import reverse
import traceback


def _login_rate_limit_key(request, username):
    ip = _get_client_ip(request)
    normalized = (username or '').strip().lower() or 'anon'
    return f'login_attempts:{ip}:{normalized}'


def _login_ip_rate_limit_key(request):
    ip = _get_client_ip(request)
    return f'login_ip_attempts:{ip}'


def _get_client_ip(request):
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if forwarded:
        return forwarded.split(',')[0].strip() or request.META.get('REMOTE_ADDR', '0.0.0.0')
    return request.META.get('REMOTE_ADDR', '0.0.0.0')


def _login_session_key(username, suffix):
    normalized = (username or '').strip().lower() or 'anon'
    safe = re.sub(r'[^a-z0-9_]+', '_', normalized)
    return f'login_{suffix}_{safe}'


def _login_attempts_snapshot(request, username):
    """Combina cache y sesiÃ³n para que el estado no dependa solo de la cache."""
    ip = _get_client_ip(request)
    cache_key = _login_rate_limit_key(request, username)
    ip_cache_key = _login_ip_rate_limit_key(request)

    attempt_data = cache.get(cache_key, {'count': 0, 'blocked_until': None})
    ip_attempt_data = cache.get(ip_cache_key, {'count': 0, 'blocked_until': None})

    session_attempts = int(request.session.get(_login_session_key(username, 'attempts')) or 0)
    session_ip_attempts = int(request.session.get(_login_session_key(ip, 'ip_attempts')) or 0)

    attempts_total = max(
        int(attempt_data.get('count') or 0),
        int(ip_attempt_data.get('count') or 0),
        session_attempts,
        session_ip_attempts,
    )

    return cache_key, ip_cache_key, attempt_data, ip_attempt_data, attempts_total, ip


def _recovery_code_attempts_key(request):
    user_id = request.session.get('recovery_user') or 'anon'
    return f'recovery_code_attempts:{user_id}'


def _recovery_code_block_key(request):
    user_id = request.session.get('recovery_user') or 'anon'
    return f'recovery_code_block:{user_id}'


def _puede_modificar_usuarios(user):
    grupos = list(user.groups.values_list('name', flat=True))
    return user.is_superuser or 'Administrador' in grupos or 'Auxiliar' in grupos

# ==================== VISTAS DE AUTENTICACIÃ“N ====================

@csrf_protect
@never_cache
def login_view(request):
    # Si el usuario ya estÃ¡ autenticado, lo enviamos al dashboard
    if request.user.is_authenticated:
        return redirect('core:dashboard')

    if request.method != 'POST':
        return redirect(reverse('core:index') + '?login=1')

    if request.method == 'POST':
        username = (request.POST.get('username') or '').strip()
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.POST.get('ajax_login') == '1'
        cache_key, ip_cache_key, attempt_data, ip_attempt_data, attempts_total, ip = _login_attempts_snapshot(request, username)
        blocked_until = attempt_data.get('blocked_until')
        ip_blocked_until = ip_attempt_data.get('blocked_until')
        session_block_until = request.session.get(_login_session_key(username, 'block_until'))
        session_block_until_ip = request.session.get(_login_session_key(ip, 'ip_block_until'))
        now = timezone.now()

        session_blocks = [dt for dt in [blocked_until, ip_blocked_until] if dt]
        session_time_blocks = []
        for raw_ts in [session_block_until, session_block_until_ip]:
            try:
                if raw_ts:
                    session_time_blocks.append(datetime.fromtimestamp(float(raw_ts), tz=timezone.get_current_timezone()))
            except (TypeError, ValueError, OverflowError):
                pass

        active_block_until = max(session_blocks + session_time_blocks, default=None)
        if active_block_until and active_block_until > now:
            remaining = int((active_block_until - now).total_seconds() // 60) or 1
            message = f'Has superado los intentos permitidos. Intenta nuevamente en {remaining} minuto(s).'
            if is_ajax:
                return JsonResponse({
                    'success': False,
                    'message': message,
                    'attempts': attempts_total,
                    'blocked': True,
                    'blocked_minutes': remaining,
                }, status=429)
            messages.error(request, message)
            return redirect(request.META.get('HTTP_REFERER', 'core:index'))

        form = LoginForm(request, data=request.POST)

        if form.is_valid():
            user = form.get_user()
            cache.delete(cache_key)
            cache.delete(ip_cache_key)
            request.session.pop(_login_session_key(username, 'block_until'), None)
            request.session.pop(_login_session_key(ip, 'ip_block_until'), None)
            request.session.pop(_login_session_key(username, 'attempts'), None)
            request.session.pop(_login_session_key(ip, 'ip_attempts'), None)
            login(request, user)
            if is_ajax:
                next_url = request.POST.get('next') or request.GET.get('next') or reverse('core:dashboard')
                return JsonResponse({
                    'success': True,
                    'message': 'Inicio de sesiÃ³n correcto.',
                    'redirect': next_url,
                })
            return redirect('core:dashboard')

        current_count = int(attempt_data.get('count') or 0) + 1
        ip_current_count = int(ip_attempt_data.get('count') or 0) + 1
        block_until = None
        if current_count >= 5 and current_count % 5 == 0:
            wait_minutes = max(1, current_count // 5)
            block_until = now + timedelta(minutes=wait_minutes)

        ip_block_until = None
        if ip_current_count >= 5 and ip_current_count % 5 == 0:
            wait_minutes = max(1, ip_current_count // 5)
            ip_block_until = now + timedelta(minutes=wait_minutes)

        cache.set(
            cache_key,
            {
                'count': current_count,
                'blocked_until': block_until,
            },
            timeout=24 * 60 * 60,
        )
        if block_until:
            request.session[_login_session_key(username, 'block_until')] = block_until.timestamp()
        request.session[_login_session_key(username, 'attempts')] = current_count
        cache.set(
            ip_cache_key,
            {
                'count': ip_current_count,
                'blocked_until': ip_block_until,
            },
            timeout=24 * 60 * 60,
        )
        if ip_block_until:
            request.session[_login_session_key(ip, 'ip_block_until')] = ip_block_until.timestamp()
        request.session[_login_session_key(ip, 'ip_attempts')] = ip_current_count

        error_message = 'Usuario o contraseÃ±a incorrectos.'
        attempts_total = max(current_count, ip_current_count, attempts_total)
        if is_ajax:
            blocked_minutes = 0
            active_until = max([dt for dt in [block_until, ip_block_until] if dt], default=None)
            if active_until and active_until > now:
                blocked_minutes = int((active_until - now).total_seconds() // 60) or 1
            return JsonResponse({
                'success': False,
                'message': error_message,
                'attempts': attempts_total,
                'blocked': blocked_minutes > 0,
                'blocked_minutes': blocked_minutes,
            }, status=400)

        messages.error(request, error_message)
        return redirect(request.META.get('HTTP_REFERER', 'core:index'))
    else:
        # Para peticiones GET, creamos un formulario vacÃ­o
        form = LoginForm()

    return render(request, 'usuarios/login.html', {
        'form': form
    })



@login_required
def logout_view(request):
    logout(request)
    messages.success(request, 'Has cerrado sesiÃ³n exitosamente.')
    return redirect('core:index')


# ==================== RECUPERACIÃ“N DE CONTRASEÃ‘A ====================


@csrf_protect
def username_recovery_view(request):
    """Vista para recuperar nombre de usuario por email"""
    
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        
        if not email:
            messages.error(request, 'Por favor ingresa un correo electrÃ³nico.')
            return render(request, 'usuarios/username_recovery.html')
        
        try:
            user = User.objects.get(email=email, is_active=True)
            
            # Enviar email con el username
            subject = 'RecuperaciÃ³n de Usuario - Mona Keratina'
            message = f"""
            Hola {user.get_full_name()},
            
            Tu nombre de usuario es: {user.username}
            
            Si no solicitaste esta informaciÃ³n, puedes ignorar este correo.
            
            Saludos,
            Equipo Mona Keratina
            """
            
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=False,
            )
            
            messages.success(
                request,
                'Se ha enviado tu nombre de usuario al correo registrado.'
            )
            return redirect(reverse('core:index') + '?login=1')
            
        except User.DoesNotExist:
            messages.success(
                request,
                'Si existe una cuenta con ese correo, recibirÃ¡s tu nombre de usuario.'
            )
            return redirect(reverse('core:index') + '?login=1')
        except Exception as e:
            messages.error(
                request,
                'Error al enviar el correo. Por favor intenta mÃ¡s tarde.'
            )
            return render(request, 'usuarios/username_recovery.html')
    
    return render(request, 'usuarios/username_recovery.html')


# ==================== PANEL DE USUARIOS (ADMIN / AUX) ====================

@login_required
def lista_usuarios_view(request):
    grupos = list(request.user.groups.values_list('name', flat=True))

    es_administrador = request.user.is_superuser or 'Administrador' in grupos
    puede_modificar  = request.user.is_superuser or 'Administrador' in grupos or 'Auxiliar' in grupos

    # âœ… form se crea PRIMERO
    form = UsuarioBusquedaForm(request.GET)

    usuarios = User.objects.select_related('perfil').all()
    current_sort = (request.GET.get('sort') or '').strip()
    current_dir = (request.GET.get('dir') or 'asc').strip().lower()
    if current_dir not in {'asc', 'desc'}:
        current_dir = 'asc'

    if form.is_valid():
        busqueda = form.cleaned_data.get('busqueda')
        filtro   = form.cleaned_data.get('filtro')

        if busqueda:
            usuarios = usuarios.filter(
                Q(username__icontains=busqueda)   |
                Q(first_name__icontains=busqueda) |
                Q(last_name__icontains=busqueda)  |
                Q(email__icontains=busqueda)      |
                Q(perfil__documento__icontains=busqueda)
            )

        if filtro:
            if filtro == 'activo':
                usuarios = usuarios.filter(is_active=True)
            elif filtro == 'inactivo':
                usuarios = usuarios.filter(is_active=False)
            elif filtro.startswith('rol_'):
                rol_valor = filtro.replace('rol_', '')
                usuarios = usuarios.filter(groups__name=rol_valor)

    sort_map = {
        'username': ('username',),
        'nombre': ('first_name', 'last_name', 'username'),
        'email': ('email', 'username'),
        'estado': ('is_active', 'username'),
        'registro': ('date_joined',),
    }

    if current_sort in sort_map:
        order_fields = []
        for field in sort_map[current_sort]:
            order_fields.append(field if current_dir == 'asc' else f'-{field}')
        usuarios = usuarios.order_by(*order_fields)
    else:
        current_sort = ''
        usuarios = usuarios.order_by('-date_joined')

    q = form.cleaned_data.get('busqueda', '') if form.is_valid() else ''
    context = {
        'titulo'          : 'GestiÃ³n de Usuarios',
        'usuarios'        : usuarios,
        'form'            : form,
        'es_administrador': es_administrador,
        'puede_modificar' : puede_modificar,
        'q'               : q,
        'current_sort'    : current_sort,
        'current_dir'     : current_dir,
    }

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, 'usuarios/lista_usuarios_global.html', context)

    return render(request, 'usuarios/lista_usuarios.html', context)

@login_required
#@no_colaborador_required()
def crear_usuario_view(request):
    grupos = list(request.user.groups.values_list('name', flat=True))
    if not _puede_modificar_usuarios(request.user):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'message': 'No tienes permisos para crear usuarios.'}, status=403)
        messages.error(request, 'No tienes permisos para crear usuarios.')
        return redirect('usuarios:lista_usuarios')
    
    # Verificar si es una peticiÃ³n AJAX para cargar el modal
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    if request.method == 'POST':
        form = RegistroForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save()
            
            if is_ajax:
                # Respuesta JSON para AJAX
                return JsonResponse({
                    'success': True,
                    'message': f'Usuario {user.get_full_name()} creado exitosamente.'
                })
            else:
                messages.success(
                    request,
                    f'Usuario {user.get_full_name()} creado exitosamente.'
                )
                return redirect('usuarios:lista_usuarios')
        else:
            if is_ajax:
                # Renderizar el formulario con errores para el modal
                html_form = render_to_string('usuarios/_formulario_usuario_modal.html', 
                                            {'form': form}, 
                                            request=request)
                return JsonResponse({
                    'success': False,
                    'html_form': html_form
                })
    else:
        form = RegistroForm()
    
    # Si es AJAX y es GET, retornar el HTML del formulario para el modal
    if is_ajax:
        html_form = render_to_string('usuarios/_formulario_usuario_modal.html', 
                                     {'form': form}, 
                                     request=request)
        return JsonResponse({'html_form': html_form})

    # Si no es AJAX, mostrar la pÃ¡gina completa (comportamiento anterior)
    return render(
        request,
        'crear_usuario.html',
        {
            'titulo': 'Crear Usuario',
            'form': form,
        }
    )


@login_required
def editar_usuario_view(request, user_id):
    usuario = get_object_or_404(User, id=user_id)
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    if not _puede_modificar_usuarios(request.user):
        if is_ajax:
            return JsonResponse({'success': False, 'message': 'No tienes permisos para editar usuarios.'}, status=403)
        messages.error(request, 'No tienes permisos para editar usuarios.')
        return redirect('usuarios:lista_usuarios')

    try:
        perfil, _ = PerfilUsuario.objects.get_or_create(user=usuario)

        if request.method == 'POST':
            form_usuario = EditarUsuarioForm(request.POST, instance=usuario)
            form_perfil = EditarPerfilForm(
                request.POST,
                request.FILES,
                instance=perfil
            )

            if form_usuario.is_valid() and form_perfil.is_valid():
                user_updated = form_usuario.save(commit=False)
                rol = str(form_usuario.cleaned_data.get('rol', '')).strip()
                if rol:
                    user_updated.groups.clear()
                    grupo, _ = Group.objects.get_or_create(name=rol)
                    user_updated.groups.add(grupo)
                    user_updated.is_staff = rol in ['Administrador', 'Auxiliar']

                user_updated.save()
                form_perfil.save()

                if is_ajax:
                    return JsonResponse({
                        'success': True,
                        'message': f'Usuario {usuario.get_full_name() or usuario.username} actualizado exitosamente.'
                    })

                messages.success(
                    request,
                    f'Usuario {usuario.get_full_name() or usuario.username} actualizado.'
                )
                return redirect('usuarios:lista_usuarios')

            if is_ajax:
                html_form = render_to_string(
                    'usuarios/_formulario_editar_usuario_modal.html',
                    {
                        'form_usuario': form_usuario,
                        'form_perfil': form_perfil,
                        'usuario': usuario,
                    },
                    request=request
                )
                return JsonResponse({
                    'success': False,
                    'html_form': html_form
                }, status=400)

        else:
            form_usuario = EditarUsuarioForm(instance=usuario)
            form_perfil = EditarPerfilForm(instance=perfil)

        if is_ajax:
            html_form = render_to_string(
                'usuarios/_formulario_editar_usuario_modal.html',
                {
                    'form_usuario': form_usuario,
                    'form_perfil': form_perfil,
                    'usuario': usuario,
                },
                request=request
            )
            return JsonResponse({
                'success': True,
                'html_form': html_form
            })

        return render(
            request,
            'usuarios/editar_usuario.html',
            {
                'titulo': f'Editar Usuario: {usuario.get_full_name() or usuario.username}',
                'form_usuario': form_usuario,
                'form_perfil': form_perfil,
                'usuario': usuario,
            }
        )

    except Exception as e:
        print("ERROR EDITAR USUARIO:")
        print(traceback.format_exc())

        if is_ajax:
            return JsonResponse({
                'success': False,
                'message': str(e),
                'trace': traceback.format_exc()
            }, status=500)
        raise

@login_required
# @solo_admin_required()
def eliminar_usuario_view(request, user_id):
    grupos = list(request.user.groups.values_list('name', flat=True))

    usuario = get_object_or_404(User, id=user_id)
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    if not _puede_modificar_usuarios(request.user):
        if is_ajax:
            return JsonResponse({'success': False, 'message': 'No tienes permisos para desactivar usuarios.'}, status=403)
        messages.error(request, 'No tienes permisos para desactivar usuarios.')
        return redirect('usuarios:lista_usuarios')

    if usuario == request.user:
        if is_ajax:
            return JsonResponse({
                'success': False,
                'message': 'No puedes eliminarte a ti mismo.'
            })
        messages.error(request, 'No puedes eliminarte a ti mismo.')
        return redirect('usuarios:lista_usuarios')

    if request.method == 'POST':
        nombre_completo = usuario.get_full_name()
        usuario.is_active = False
        usuario.save(update_fields=['is_active'])
        
        if is_ajax:
            return JsonResponse({
                'success': True,
                'message': f'Usuario {nombre_completo} desactivado exitosamente.'
            })
        else:
            messages.success(
                request,
                f'Usuario {nombre_completo} desactivado.'
            )
            return redirect('usuarios:lista_usuarios')

    # Si es AJAX y es GET, retornar el HTML del modal de confirmaciÃ³n
    if is_ajax:
        try:
            html_content = render_to_string('usuarios/_confirmar_eliminar_modal.html', 
                                           {'usuario': usuario}, 
                                           request=request)
            return JsonResponse({'html_content': html_content})
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error al cargar el contenido: {str(e)}'
            }, status=500)

    # Si no es AJAX, mostrar la pÃ¡gina completa (comportamiento anterior)
    return render(
        request,
        'usuarios/eliminar_usuario.html',
        {
            'titulo': 'Desactivar Usuario',
            'usuario': usuario,
        }
    )


@login_required
def detalle_usuario_view(request, user_id):
    """Ver detalles de un usuario vÃ­a AJAX."""
    grupos = list(request.user.groups.values_list('name', flat=True))
    es_administrador = request.user.is_superuser or 'Administrador' in grupos
    puede_modificar = request.user.is_superuser or 'Administrador' in grupos or 'Auxiliar' in grupos

    usuario = get_object_or_404(User, id=user_id)
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    if is_ajax:
        html_content = render_to_string(
            'usuarios/_detalle_usuario_modal.html',
            {
                'usuario': usuario,
                'es_administrador': es_administrador,
                'puede_modificar': puede_modificar,
            },
            request=request
        )
        return JsonResponse({'html_content': html_content})

    return redirect('usuarios:lista_usuarios')


@login_required
@require_POST
def toggle_activo_usuario_view(request, user_id):
    """Cambia el estado activo/inactivo de un usuario vÃ­a AJAX."""
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    if not is_ajax or request.method != 'POST':
        return JsonResponse({'success': False, 'mensaje': 'Solicitud no vÃ¡lida.'}, status=400)

    if not _puede_modificar_usuarios(request.user):
        return JsonResponse({'success': False, 'mensaje': 'No tienes permisos para modificar usuarios.'}, status=403)

    usuario = get_object_or_404(User, id=user_id)

    if usuario == request.user:
        return JsonResponse({'success': False, 'mensaje': 'No puedes cambiar tu propio estado.'}, status=403)

    usuario.is_active = not usuario.is_active
    usuario.save(update_fields=['is_active'])

    estado = 'activo' if usuario.is_active else 'inactivo'
    return JsonResponse({
        'success': True,
        'activo': usuario.is_active,
        'mensaje': f'Usuario "{usuario.username}" marcado como {estado}.'
    })


@login_required
# @admin_o_aux_required()
def perfil_view(request):
    usuario = request.user

    if request.method == 'POST':
        form_usuario = EditarUsuarioForm(request.POST, instance=usuario)
        form_perfil = EditarPerfilForm(
            request.POST,
            request.FILES,
            instance=usuario.perfil
        )

        if form_usuario.is_valid() and form_perfil.is_valid():
            form_usuario.save()
            form_perfil.save()
            messages.success(request, 'Perfil actualizado.')
            return redirect('usuarios:perfil')

    else:
        form_usuario = EditarUsuarioForm(instance=usuario)
        form_perfil = EditarPerfilForm(instance=usuario.perfil)

    return render(
        request,
        'usuarios/perfil.html',
        {
            'titulo': 'Mi Perfil',
            'form_usuario': form_usuario,
            'form_perfil': form_perfil,
        }
    )


# ==================== VALIDACIONES AJAX EN TIEMPO REAL ====================

@login_required
# @no_colaborador_required()
def validar_documento_ajax(request):
    """
    Endpoint AJAX para validar documento en tiempo real
    """
    if request.method == 'GET':
        documento = request.GET.get('documento', '').strip()
        
        if not documento:
            return JsonResponse({
                'valido': False,
                'mensaje': 'El documento es requerido'
            })
        
        # Validar que solo contenga nÃºmeros
        if not documento.isdigit():
            return JsonResponse({
                'valido': False,
                'mensaje': 'El documento solo puede contener nÃºmeros'
            })
        
        # Validar longitud mÃ­nima
        if len(documento) < 6:
            return JsonResponse({
                'valido': False,
                'mensaje': 'El documento debe tener al menos 6 dÃ­gitos'
            })
        
        # Verificar si ya existe
        if PerfilUsuario.objects.filter(documento=documento).exists():
            return JsonResponse({
                'valido': False,
                'mensaje': 'Este documento ya estÃ¡ registrado'
            })
        
        return JsonResponse({
            'valido': True,
            'mensaje': 'Documento vÃ¡lido'
        })
    
    return JsonResponse({'error': 'MÃ©todo no permitido'}, status=405)


# ==================== RECUPERACIÃ“N DE USUARIO ====================

@csrf_protect
@never_cache
def solicitar_recuperacion(request):
    if request.method == 'POST':
        email = (request.POST.get('email') or '').strip()

        user = User.objects.filter(email__iexact=email, is_active=True).first()
        if not user:
            request.session.pop('recovery_user', None)
            request.session['codigo_validado'] = False
            messages.error(request, 'Ingresa un correo vÃ¡lido registrado en el sistema.')
            return render(request, 'usuarios/recuperar.html')

        codigo = str(random.randint(100000, 999999))

        perfil = user.perfil
        PerfilUsuario.objects.filter(pk=perfil.pk).update(
            recovery_code=codigo,
            recovery_code_created=timezone.now(),
        )

        html_content = render_to_string('usuarios/correo.html', {
            'codigo': codigo,
            'year': timezone.now().year
        })

        email_msg = EmailMultiAlternatives(
            subject='âœ¨ RecuperaciÃ³n de contraseÃ±a - MONAPP',
            body='Tu cliente de correo no soporta HTML',
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[email],
        )

        email_msg.attach_alternative(html_content, "text/html")

        try:
            email_msg.send()
        except smtplib.SMTPAuthenticationError:
            PerfilUsuario.objects.filter(pk=perfil.pk).update(
                recovery_code=None,
                recovery_code_created=None,
            )
            request.session.pop('recovery_user', None)
            request.session['codigo_validado'] = False
            messages.error(
                request,
                'No se pudo enviar el correo. Gmail rechazÃ³ la autenticaciÃ³n. '
                'Debes usar una contraseÃ±a de aplicaciÃ³n vÃ¡lida.'
            )
            return render(request, 'usuarios/recuperar.html')
        except (smtplib.SMTPException, socket.gaierror, OSError, TimeoutError):
            PerfilUsuario.objects.filter(pk=perfil.pk).update(
                recovery_code=None,
                recovery_code_created=None,
            )
            request.session.pop('recovery_user', None)
            request.session['codigo_validado'] = False
            messages.error(
                request,
                'No se pudo enviar el correo en este momento. Intenta de nuevo mÃ¡s tarde.'
            )
            return render(request, 'usuarios/recuperar.html')

        request.session['recovery_user'] = user.id
        request.session['codigo_validado'] = False
        request.session[_recovery_code_attempts_key(request)] = 0
        request.session.pop(_recovery_code_block_key(request), None)
        messages.success(
            request,
            'Si el correo estÃ¡ registrado, recibirÃ¡s un cÃ³digo de recuperaciÃ³n.'
        )

        return redirect('usuarios:verificar_codigo')

    return render(request, 'usuarios/recuperar.html')

@csrf_protect
@never_cache
def verificar_codigo(request):
    user_id = request.session.get('recovery_user')
    user = User.objects.filter(id=user_id).select_related('perfil').first() if user_id else None
    perfil = getattr(user, 'perfil', None)
    attempts_key = _recovery_code_attempts_key(request)
    block_key = _recovery_code_block_key(request)
    blocked_until = request.session.get(block_key)
    now = timezone.now()

    if not user or not perfil:
        return redirect(reverse('core:index') + '?login=1')

    if blocked_until and hasattr(blocked_until, 'tzinfo') and blocked_until > now:
        restantes = int((blocked_until - now).total_seconds() // 60) or 1
        return render(request, 'usuarios/verificar_codigo.html', {
            'error': f'Has superado los intentos permitidos. Espera {restantes} minuto(s) e intenta nuevamente.'
        })
    if blocked_until and hasattr(blocked_until, 'tzinfo') and blocked_until <= now:
        request.session.pop(block_key, None)
        request.session[attempts_key] = 0

    if request.method == 'POST':
        codigo = request.POST.get('codigo')

        if not user or not perfil:
            return redirect(reverse('core:index') + '?login=1')

        if perfil.recovery_code_created and (now - perfil.recovery_code_created) > timedelta(minutes=5):
            perfil.recovery_code = None
            perfil.recovery_code_created = None
            perfil.save(update_fields=['recovery_code', 'recovery_code_created'])
            request.session.pop(block_key, None)
            request.session[attempts_key] = 0
            return render(request, 'usuarios/verificar_codigo.html', {
                'error': 'El cÃ³digo ha expirado. Solicita uno nuevo.'
            })

        if perfil.recovery_code != codigo:
            current_attempts = int(request.session.get(attempts_key, 0)) + 1
            request.session[attempts_key] = current_attempts

            if current_attempts >= 5 and current_attempts % 5 == 0:
                wait_minutes = max(1, current_attempts // 5)
                request.session[block_key] = now + timedelta(minutes=wait_minutes)

            return render(request, 'usuarios/verificar_codigo.html', {
                'error': 'CÃ³digo incorrecto'
            })

        request.session.pop(block_key, None)
        request.session[attempts_key] = 0
        request.session['codigo_validado'] = True
        return redirect('usuarios:nueva_password')

    return render(request, 'usuarios/verificar_codigo.html')

@csrf_protect
@never_cache
def nueva_password(request):
    if not request.session.get('codigo_validado'):
        return redirect(reverse('core:index') + '?login=1')

    user_id = request.session.get('recovery_user')
    user = User.objects.filter(id=user_id).select_related('perfil').first() if user_id else None
    if not user:
        return redirect(reverse('core:index') + '?login=1')

    if request.method == 'POST':
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')

        if not password1 or not password2:
            messages.error(request, 'Debes ingresar ambas contraseÃ±as.')
            return render(request, 'usuarios/nueva_password.html')

        if password1 != password2:
            messages.error(request, 'Las contraseÃ±as no coinciden.')
            return render(request, 'usuarios/nueva_password.html')

        if len(password1) < 8:
            messages.error(request, 'La contraseÃ±a debe tener al menos 8 caracteres.')
            return render(request, 'usuarios/nueva_password.html')

        if not re.search(r'[A-Z]', password1):
            messages.error(request, 'La contraseÃ±a debe contener al menos una letra mayÃºscula.')
            return render(request, 'usuarios/nueva_password.html')

        if not re.search(r'[0-9]', password1):
            messages.error(request, 'La contraseÃ±a debe contener al menos un nÃºmero.')
            return render(request, 'usuarios/nueva_password.html')

        if not re.search(r'[^A-Za-z0-9]', password1):
            messages.error(request, 'La contraseÃ±a debe incluir al menos un carÃ¡cter especial (ej: @, #, !, %).')
            return render(request, 'usuarios/nueva_password.html')

        user.set_password(password1)
        user.save()

        # Limpiar cÃ³digo
        perfil = user.perfil
        perfil.recovery_code = None
        perfil.recovery_code_created = None
        perfil.save()

        login_username = (user.username or '').strip()
        client_ip = _get_client_ip(request)
        cache.delete(_login_rate_limit_key(request, login_username))
        cache.delete(_login_ip_rate_limit_key(request))
        request.session.pop(_login_session_key(login_username, 'attempts'), None)
        request.session.pop(_login_session_key(login_username, 'block_until'), None)
        request.session.pop(_login_session_key(client_ip, 'ip_attempts'), None)
        request.session.pop(_login_session_key(client_ip, 'ip_block_until'), None)

        request.session.pop(_recovery_code_attempts_key(request), None)
        request.session.pop(_recovery_code_block_key(request), None)
        request.session.flush()
        messages.success(request, 'Tu contraseÃ±a ha sido actualizada exitosamente.')
        return redirect(reverse('core:index') + '?login=1')

    return render(request, 'usuarios/nueva_password.html')


# ==================== VALIDACIONES EN TIEMPO REAL ====================

@login_required
def validar_documento_usuario(request):
    """
    Endpoint para validar documento de usuario en tiempo real
    """
    numero = (request.GET.get('numero') or '').strip()
    user_id = request.GET.get('user_id')

    # Validar nÃºmero
    if not numero.isdigit():
        return JsonResponse({'valido': False, 'mensaje': 'Solo nÃºmeros'})

    # Normalizar user_id
    if not user_id or user_id in ('undefined', 'null', ''):
        user_id = None
    else:
        try:
            user_id = int(user_id)
        except ValueError:
            user_id = None

    qs = PerfilUsuario.objects.filter(documento=numero)

    # Si es ediciÃ³n, excluye el mismo usuario
    if user_id is not None:
        qs = qs.exclude(user__id=user_id)

    if qs.exists():
        return JsonResponse({
            'valido': False,
            'mensaje': 'Ya existe otro usuario con este documento.'
        })

    return JsonResponse({'valido': True})


@login_required
def validar_email_usuario(request):
    """
    Endpoint para validar email de usuario en tiempo real
    """
    email = (request.GET.get('email') or '').strip()
    user_id = request.GET.get('user_id')

    # Validar formato de email (solo verificar @ y .)
    if '@' not in email or '.' not in email.split('@')[-1]:
        return JsonResponse({'valido': False, 'mensaje': 'Correo electrÃ³nico invÃ¡lido'})

    # Normalizar user_id
    if not user_id or user_id in ('undefined', 'null', ''):
        user_id = None
    else:
        try:
            user_id = int(user_id)
        except ValueError:
            user_id = None

    qs = User.objects.filter(email=email)

    # Si es ediciÃ³n, excluye el mismo usuario
    if user_id is not None:
        qs = qs.exclude(id=user_id)

    if qs.exists():
        return JsonResponse({
            'valido': False,
            'mensaje': 'Ya existe otro usuario con este email.'
        })

    return JsonResponse({'valido': True})

