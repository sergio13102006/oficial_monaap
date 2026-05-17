# usuarios/urls.py

from django.urls import path
from . import views

app_name = 'usuarios'

urlpatterns = [
    # Autenticación
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Perfil de usuario
    path('perfil/', views.perfil_view, name='perfil'),
    path('recuperar/', views.PasswordResetRequestView.as_view(), name='recuperar'),
    path('recuperar/enviado/', views.PasswordResetDonePageView.as_view(), name='password_reset_done'),
    path('recuperar/<uidb64>/<token>/', views.PasswordResetConfirmNotifyView.as_view(), name='password_reset_confirm'),
    path('recuperar/completado/', views.PasswordResetCompletePageView.as_view(), name='password_reset_complete'),
    # Panel de administración
    path('usuarios/', views.lista_usuarios_view, name='lista_usuarios'),
    path('usuarios/crear/', views.crear_usuario_view, name='crear_usuario'),
    path('usuarios/<int:user_id>/editar/', views.editar_usuario_view, name='editar_usuario'),
    path('usuarios/<int:user_id>/eliminar/', views.eliminar_usuario_view, name='eliminar_usuario'),
    path('usuarios/<int:user_id>/detalle/', views.detalle_usuario_view, name='detalle_usuario'),
    path('usuarios/<int:user_id>/cambiar-contrasena/', views.cambiar_password_usuario_view, name='cambiar_password_usuario'),
    path('usuarios/<int:user_id>/toggle-activo/', views.toggle_activo_usuario_view, name='toggle_activo_usuario'),

    # Validaciones en tiempo real
    path('validar-documento/', views.validar_documento_usuario, name='validar_documento'),
    path('validar-email/', views.validar_email_usuario, name='validar_email'),
]
