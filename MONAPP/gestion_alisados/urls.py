from django.urls import path
from . import views

app_name = 'gestion_alisados'

urlpatterns = [
    path('', views.lista_gestion_alisados, name='lista_gestion_alisados'),
    path('reporte/preview/', views.reporte_gestion_preview, name='reporte_gestion_preview'),
    path('reporte.pdf', views.exportar_reporte_gestion_pdf_v2, name='exportar_reporte_gestion_pdf'),
    path('reporte.csv', views.exportar_reporte_gestion_csv, name='exportar_reporte_gestion_csv'),
    path('crear/', views.crear_gestion_alisado, name='crear_gestion_alisado'),
    path('ultima-gestion-cliente/', views.ultima_gestion_cliente, name='ultima_gestion_cliente'),
    path('<uuid:pk>/detalle-modal/', views.ver_gestion_alisado_modal_content, name='ver_gestion_alisado_modal_content'),
    path('<uuid:pk>/', views.ver_gestion_alisado, name='ver_gestion_alisado'),
    path('<uuid:pk>/editar/', views.editar_gestion_alisado, name='editar_gestion_alisado'),
    path('<uuid:pk>/eliminar/', views.eliminar_gestion_alisado, name='eliminar_gestion_alisado'),
    path('form_gestion_alisado_modal_content/', views.form_gestion_alisado_modal_content, name='form_gestion_alisado_modal_content'),
    # path('<uuid:pk>/pdf/',  views.generar_pdf_gestion_alisado,  name='generar_pdf_gestion_alisado'),
    # path('<uuid:pk>/word/', views.generar_word_gestion_alisado, name='generar_word_gestion_alisado'),
]
