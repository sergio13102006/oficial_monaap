import re
import socket
from urllib.parse import urlencode
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User, Group
from django.contrib import messages
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST
from django.db.models import Q
from django.http import JsonResponse
from django.template.loader import render_to_string
from .forms import LoginForm, RegistroForm, EditarUsuarioForm, EditarPerfilForm, UsuarioBusquedaForm
from .models import PerfilUsuario
from .models import AuthSecurityEvent, AuthSecurityState
from django.utils import timezone
from django.core.mail import send_mail
from datetime import timedelta
from django.conf import settings
from django.urls import reverse, reverse_lazy
from django.contrib.auth.views import PasswordResetView, PasswordResetConfirmView, PasswordResetDoneView, PasswordResetCompleteView
import traceback
from django.db import transaction

from .security import (
    allow_recovery_request,
    evaluate_login_gate,
    get_client_ip,
    get_security_state,
    normalize_subject,
    register_login_attempt,
    register_login_failure,
    register_login_success,
    register_logout,
    validate_recaptcha,
)
from .forms import IdentifierPasswordResetForm


class PasswordResetRequestView(PasswordResetView):
    form_class = IdentifierPasswordResetForm
    template_name = 'usuarios/password_reset_form.html'
    email_template_name = 'usuarios/password_reset_email.txt'
    html_email_template_name = 'usuarios/password_reset_email.html'
    subject_template_name = 'usuarios/password_reset_subject.txt'
    success_url = reverse_lazy('usuarios:password_reset_done')
    extra_email_context = {
        'brand_name': 'Mona Keratina',
    }

    def form_valid(self, form):
        email = (form.cleaned_data.get('email') or '').strip()
        ip = get_client_ip(self.request)

        if not allow_recovery_request(self.request, namespace='password'):
            register_login_attempt(
                request=self.request,
                username=email,
                success=False,
                event_type=AuthSecurityEvent.EVENT_RECOVERY_REQUESTED,
                subject_type=AuthSecurityState.SUBJECT_IP,
                subject_value=ip,
                details={'reason': 'rate_limited'},
            )
            messages.error(self.request, 'No fue posible procesar la solicitud. Intenta de nuevo más tarde.')
            return self.form_invalid(form)

        register_login_attempt(
            request=self.request,
            username=email,
            success=True,
            event_type=AuthSecurityEvent.EVENT_RECOVERY_REQUESTED,
            subject_type=AuthSecurityState.SUBJECT_IP,
            subject_value=ip,
            details={'identifier': email},
        )
        try:
            return super().form_valid(form)
        except Exception:
            register_login_attempt(
                request=self.request,
                username=email,
                success=False,
                event_type=AuthSecurityEvent.EVENT_RECOVERY_CODE_FAILED,
                subject_type=AuthSecurityState.SUBJECT_IP,
                subject_value=ip,
                details={'reason': 'email_send_failed', 'identifier': email},
            )
            messages.error(self.request, 'No fue posible enviar el enlace en este momento. Intenta de nuevo más tarde.')
            return self.form_invalid(form)

    def form_invalid(self, form):
        email_errors = form.errors.get('email')
        if email_errors:
            messages.error(self.request, email_errors[0])
        return super().form_invalid(form)


class PasswordResetDonePageView(PasswordResetDoneView):
    template_name = 'usuarios/password_reset_done.html'


class PasswordResetCompletePageView(PasswordResetCompleteView):
    template_name = 'usuarios/password_reset_complete.html'


class PasswordResetConfirmNotifyView(PasswordResetConfirmView):
    template_name = 'usuarios/password_reset_confirm.html'
    success_url = reverse_lazy('usuarios:password_reset_complete')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = getattr(self, 'user', None)
        context['password_policy_full_name'] = (user.get_full_name() if user else '') or ''
        context['password_policy_username'] = (user.username if user else '') or ''
        context['password_policy_email'] = (user.email if user else '') or ''
        return context

    def form_valid(self, form):
        user = self.user
        response = super().form_valid(form)

        if user and user.email:
            try:
                send_mail(
                    subject='Tu contraseña fue cambiada - Mona Keratina',
                    message=(
                        f"Hola {user.get_full_name() or user.username},\n\n"
                        "Tu contraseña fue cambiada correctamente.\n"
                        "Si no reconoces esta acción, contacta al equipo de soporte de inmediato.\n\n"
                        "Saludos,\nEquipo Mona Keratina"
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    fail_silently=True,
                )
            except Exception:
                pass

        register_login_attempt(
            request=self.request,
            username=user.username if user else '',
            success=True,
            user=user,
            event_type=AuthSecurityEvent.EVENT_PASSWORD_CHANGED,
            subject_type=AuthSecurityState.SUBJECT_USER if user else '',
            subject_value=normalize_subject(user.username) if user else '',
            details={'source': 'password_reset_flow'},
        )
        return response


def _puede_modificar_usuarios(user):
    grupos = list(user.groups.values_list('name', flat=True))
    return user.is_superuser or 'Administrador' in grupos or 'Auxiliar' in grupos


def _login_portal_url(request):
    params = {"login": "1"}
    next_url = (request.GET.get("next") or request.POST.get("next") or "").strip()
    if next_url:
        params["next"] = next_url
    return f"{reverse('core:index')}?{urlencode(params)}"
# ==================== VISTAS DE AUTENTICACIÃ“N ====================

@csrf_protect
@never_cache
def login_view(request):
    if request.user.is_authenticated:
        return redirect("core:dashboard")

    captcha_enabled = bool(settings.LOGIN_RECAPTCHA_SITE_KEY and settings.LOGIN_RECAPTCHA_SECRET_KEY)
    login_context = {
        "login_recaptcha_site_key": settings.LOGIN_RECAPTCHA_SITE_KEY if captcha_enabled else "",
        "login_recaptcha_enabled": captcha_enabled,
        "login_captcha_required": False,
    }

    if request.method != "POST":
        return redirect(_login_portal_url(request))

    username = (request.POST.get("username") or "").strip()
    password = request.POST.get("password") or ""
    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.POST.get("ajax_login") == "1"
    now = timezone.now()
    ip = get_client_ip(request)
    captcha_token = request.POST.get("g-recaptcha-response") or request.POST.get("captcha_token")
    gate = evaluate_login_gate(request, username, now=now)

    def _error_response(message, *, status=400, blocked=False, decision=None, captcha_required=False):
        payload = {
            "success": False,
            "message": message,
            "blocked": blocked,
            "blocked_minutes": decision.blocked_minutes if decision else gate.blocked_minutes,
            "attempts": decision.user_state.failed_count if decision and decision.user_state else (gate.user_state.failed_count if gate.user_state else 0),
            "captcha_required": captcha_required,
            "captcha_site_key": settings.LOGIN_RECAPTCHA_SITE_KEY if captcha_enabled else "",
        }

        if is_ajax:
            return JsonResponse(payload, status=status)

        login_context.update({
            "login_recaptcha_enabled": captcha_enabled,
            "login_recaptcha_site_key": settings.LOGIN_RECAPTCHA_SITE_KEY if captcha_enabled else "",
            "login_captcha_required": captcha_required,
        })
        messages.error(request, message)
        return redirect(_login_portal_url(request))

    if gate.blocked:
        register_login_attempt(
            request=request,
            username=username,
            success=False,
            event_type=AuthSecurityEvent.EVENT_LOGIN_BLOCKED,
            details={
                "blocked_minutes": gate.blocked_minutes,
                "user_blocked": bool(gate.user_state and gate.user_state.blocked_until and gate.user_state.blocked_until > now),
                "ip_blocked": bool(
                    gate.ip_state
                    and (
                        (gate.ip_state.blocked_until and gate.ip_state.blocked_until > now)
                        or (gate.ip_state.burst_block_until and gate.ip_state.burst_block_until > now)
                        or (gate.ip_state.strong_block_until and gate.ip_state.strong_block_until > now)
                    )
                ),
            },
        )
        return _error_response("Tu acceso quedó pausado por seguridad. Intenta nuevamente más tarde.", status=429, blocked=True, decision=gate, captcha_required=captcha_enabled and gate.captcha_required)

    if captcha_enabled and gate.captcha_required:
        register_login_attempt(
            request=request,
            username=username,
            success=False,
            event_type=AuthSecurityEvent.EVENT_CAPTCHA_REQUIRED,
            details={
                "captcha_enabled": captcha_enabled,
                "ip": ip,
                "attempts": gate.user_state.failed_count if gate.user_state else 0,
            },
        )
        if not captcha_token:
            return _error_response(
                "Completa la verificación de seguridad para continuar.",
                status=400,
                decision=gate,
                captcha_required=True,
            )
        if not validate_recaptcha(captcha_token, ip):
            with transaction.atomic():
                user_state = get_security_state(AuthSecurityState.SUBJECT_USER, normalize_subject(username))
                ip_state = get_security_state(AuthSecurityState.SUBJECT_IP, ip)
                decision = register_login_failure(
                    request=request,
                    username=username,
                    user_state=user_state,
                    ip_state=ip_state,
                    reason="captcha_failed",
                    captcha_used=True,
                )
            return _error_response(
                "Completa la verificación de seguridad para continuar.",
                status=400,
                decision=decision,
                captcha_required=True,
            )

    form = LoginForm(request, data=request.POST)

    if form.is_valid():
        user = form.get_user()
        with transaction.atomic():
            user_state = get_security_state(AuthSecurityState.SUBJECT_USER, normalize_subject(username))
            ip_state = get_security_state(AuthSecurityState.SUBJECT_IP, ip)
            register_login_success(request=request, username=username, user_state=user_state, ip_state=ip_state, user=user)
        login(request, user)

        if not form.cleaned_data.get("remember_me", True):
            request.session.set_expiry(0)

        if is_ajax:
            next_url = request.POST.get("next") or request.GET.get("next") or reverse("core:dashboard")
            return JsonResponse({
                "success": True,
                "message": "Inicio de sesión correcto.",
                "redirect": next_url,
            })
        return redirect("core:dashboard")

    with transaction.atomic():
        user_state = get_security_state(AuthSecurityState.SUBJECT_USER, normalize_subject(username))
        ip_state = get_security_state(AuthSecurityState.SUBJECT_IP, ip)
        decision = register_login_failure(
            request=request,
            username=username,
            user_state=user_state,
            ip_state=ip_state,
            reason="invalid_credentials",
            captcha_used=bool(captcha_enabled and gate.captcha_required),
        )

    return _error_response(
        "Credenciales inválidas.",
        status=400,
        decision=decision,
        captcha_required=captcha_enabled and decision.captcha_required,
    )



@login_required
def logout_view(request):
    register_logout(
        request=request,
        username=request.user.username,
        user=request.user,
    )
    logout(request)
    messages.success(request, 'Has cerrado sesión exitosamente.')
    return redirect('core:index')


# ==================== RECUPERACIÃ“N DE CONTRASEÃ‘A ====================


@csrf_protect
def username_recovery_view(request):
    """Vista para recuperar nombre de usuario por email"""

    if request.method == 'POST':
        email = (request.POST.get('email') or '').strip()
        ip = get_client_ip(request)

        if not allow_recovery_request(request, namespace='username'):
            register_login_attempt(
                request=request,
                username=email,
                success=False,
                event_type=AuthSecurityEvent.EVENT_USERNAME_RECOVERY,
                subject_type=AuthSecurityState.SUBJECT_IP,
                subject_value=ip,
                details={'reason': 'rate_limited'},
            )
            messages.error(request, 'No fue posible procesar la solicitud. Intenta de nuevo más tarde.')
            return render(request, 'usuarios/username_recovery.html')

        if not email:
            messages.error(request, 'No fue posible procesar la solicitud.')
            return render(request, 'usuarios/username_recovery.html')

        user = User.objects.filter(email__iexact=email, is_active=True).select_related('perfil').first()

        if user:
            subject = 'Recuperación de usuario - Mona Keratina'
            message = (
                f"Hola {user.get_full_name() or user.username},\n\n"
                f"Tu nombre de usuario es: {user.username}\n\n"
                "Si no solicitaste esta información, puedes ignorar este correo.\n\n"
                "Saludos,\nEquipo Mona Keratina"
            )

            try:
                send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [email],
                    fail_silently=False,
                )
                register_login_attempt(
                    request=request,
                    username=user.username,
                    success=True,
                    user=user,
                    event_type=AuthSecurityEvent.EVENT_USERNAME_RECOVERY,
                    subject_type=AuthSecurityState.SUBJECT_USER,
                    subject_value=normalize_subject(user.username),
                    details={'email': email},
                )
            except Exception:
                register_login_attempt(
                    request=request,
                    username=user.username,
                    success=False,
                    user=user,
                    event_type=AuthSecurityEvent.EVENT_USERNAME_RECOVERY,
                    subject_type=AuthSecurityState.SUBJECT_USER,
                    subject_value=normalize_subject(user.username),
                    details={'email': email, 'reason': 'send_failed'},
                )
                messages.error(request, 'No fue posible procesar la solicitud. Intenta de nuevo más tarde.')
                return render(request, 'usuarios/username_recovery.html')

        else:
            register_login_attempt(
                request=request,
                username=email,
                success=True,
                event_type=AuthSecurityEvent.EVENT_USERNAME_RECOVERY,
                subject_type=AuthSecurityState.SUBJECT_IP,
                subject_value=ip,
                details={'email': email, 'found': False},
            )

        messages.success(request, 'Si el correo está registrado, recibirás tu nombre de usuario.')
        return redirect(reverse('core:index') + '?login=1')

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


# ==================== RECUPERACIÓN DE USUARIO ====================

@csrf_protect
@never_cache
def solicitar_recuperacion(request):
    return PasswordResetRequestView.as_view()(request)


@csrf_protect
@never_cache
def verificar_codigo(request):
    return redirect('usuarios:recuperar')


@csrf_protect
@never_cache
def nueva_password(request):
    return redirect('usuarios:recuperar')


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





