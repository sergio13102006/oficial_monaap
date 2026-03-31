from django.urls import path
from . import views

app_name = 'personal'

urlpatterns = [
    # URLs para personal (auxiliares y colaboradores)
    path('', views.lista_personal, name='lista_personal'),
    path('crear/', views.crear_personal, name='crear_personal'),
    path('<int:pk>/editar/', views.editar_personal, name='editar_personal'),
    path('<int:pk>/eliminar/', views.eliminar_personal, name='eliminar_personal'),
    path('<int:pk>/detalle/', views.detalle_personal, name='detalle_personal'),
    path('<int:pk>/toggle-activo/', views.toggle_activo_personal, name='toggle_activo_personal'),
    
    # Validaciones en tiempo real
    path('validar-documento/', views.validar_documento_personal, name='validar_documento'),
    path('validar-email/', views.validar_email_personal, name='validar_email'),
]
