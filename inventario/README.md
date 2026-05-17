# Módulo de Gestión de Inventario

## Descripción
Módulo para registrar y gestionar ingresos y egresos de dinero con seguimiento completo de transacciones.

## Características

✅ **Registro de Transacciones**
- Formulario para ingresar montos de ingreso o egreso
- Campo de texto para describir el motivo de cada transacción
- Registro automático de fecha, hora e ID de transacción único
- Asociación del usuario que realiza la transacción

✅ **Visualización de Datos**
- Panel de resumen con totales:
  - Total de Ingresos (tarjeta verde)
  - Total de Egresos (tarjeta roja)
  - Balance Total (tarjeta azul/amarilla según sea positivo/negativo)
- Lista completa de transacciones ordenadas por fecha de creación (más reciente primero)
- Tabla con toda la información: ID, Tipo, Monto, Motivo, Fecha/Hora, Usuario

✅ **Exportación**
- Botón para exportar todo el historial a archivo TXT
- Archivo incluye:
  - Resumen de totales
  - Detalle completo de cada transacción
  - Fecha y hora de generación
  - Nombre de archivo con timestamp

## Instalación

El módulo ya está instalado y configurado. Los pasos realizados fueron:

1. **Creación de la app:**
   ```bash
   python manage.py startapp inventario
   ```

2. **Registro en INSTALLED_APPS** (settings.py):
   ```python
   INSTALLED_APPS = [
       ...
       'inventario',
   ]
   ```

3. **Configuración de URLs** (MONAPP/urls.py):
   ```python
   path('inventario/', include('inventario.urls')),
   ```

4. **Migraciones:**
   ```bash
   python manage.py makemigrations inventario
   python manage.py migrate
   ```

## Uso

### Acceder al Módulo
1. Inicia el servidor: `python manage.py runserver`
2. Ve a: `http://127.0.0.1:8000/inventario/`
3. Debes estar autenticado para usar el módulo

### Registrar una Transacción
1. En el panel izquierdo "Registrar Transacción"
2. Selecciona el tipo: Ingreso o Egreso
3. Ingresa el monto (debe ser mayor a 0)
4. Escribe el motivo de la transacción
5. Haz clic en "Registrar"

### Ver el Historial
- La tabla del lado derecho muestra todas las transacciones
- Los ingresos se muestran con fondo verde
- Los egresos se muestran con fondo rojo
- Ordenadas por fecha de creación (más reciente primero)

### Exportar a TXT
1. Haz clic en el botón "Exportar TXT" en la parte superior de la tabla
2. Se descargará un archivo con formato: `inventario_reporte_YYYYMMDD_HHMMSS.txt`

## Estructura de Archivos

```
inventario/
├── models.py              # Modelo Transaccion
├── forms.py               # Formulario TransaccionForm
├── views.py               # Vistas caja_vista y exportar_txt
├── urls.py                # URLs del módulo
├── admin.py               # Configuración del admin
├── templates/
│   └── inventario/
│       └── caja.html      # Plantilla principal
└── static/
    └── inventario/
        ├── css/
        │   └── caja.css   # Estilos personalizados
        └── js/
            └── caja.js    # Scripts JavaScript
```

## Modelo de Datos

**Transaccion**
- `id_transaccion`: UUID (clave primaria, generado automáticamente)
- `tipo`: CharField ('ingreso' o 'egreso')
- `monto`: DecimalField (10 dígitos, 2 decimales)
- `motivo`: TextField (descripción de la transacción)
- `fecha_creacion`: DateTimeField (automático)
- `usuario`: ForeignKey a User (opcional)

## Características Técnicas

- **Validaciones**: 
  - Monto debe ser mayor a 0
  - Motivo es obligatorio
  - Validación en frontend y backend

- **Seguridad**: 
  - Requiere autenticación (@login_required)
  - CSRF protection en formularios

- **UI/UX**:
  - Diseño responsive con Bootstrap 5
  - Iconos Font Awesome
  - Animaciones y transiciones CSS
  - Alertas auto-cerradas después de 5 segundos
  - Scroll personalizado en tabla

## Panel de Administración

El modelo también está disponible en el admin de Django:
- URL: `http://127.0.0.1:8000/admin/`
- Filtros por tipo y fecha
- Búsqueda por motivo e ID
- Vista detallada de cada transacción

## Notas Adicionales

- Las transacciones se ordenan automáticamente por fecha (más reciente primero)
- El balance total se calcula en tiempo real: Ingresos - Egresos
- Los IDs de transacción son únicos y se generan automáticamente con UUID4
- El archivo TXT exportado usa codificación UTF-8 para soportar caracteres especiales

## Próximas Mejoras (Opcionales)

- [ ] Filtros por fecha/tipo en la interfaz
- [ ] Gráficos de ingresos vs egresos
- [ ] Exportación a PDF o Excel
- [ ] Categorías de transacciones
- [ ] Paginación para grandes volúmenes de datos
- [ ] Dashboard con estadísticas

