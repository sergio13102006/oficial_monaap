from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.index, name='index'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('gestion-datos/', views.gestion_datos_view, name='gestion_datos'),
    path('ayuda/', views.ayuda_view, name='ayuda'),
    path('ayuda/pdf/', views.ayuda_pdf_view, name='ayuda_pdf'),
]