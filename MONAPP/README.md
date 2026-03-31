# MONAPP - Sistema de Gestión Empresarial

MONAPP es un sistema de gestión empresarial desarrollado con Django que incluye módulos para productos, clientes, ventas, inventario, personal y más.

## Características

- Gestión de productos y catálogo
- Control de inventario y stock
- Sistema de ventas y compras
- Gestión de clientes y proveedores
- Administración de personal y roles
- Sistema de promociones y descuentos
- Notificaciones automáticas
- Backup automático de base de datos
- Interfaz web responsiva

## Requisitos

- Python 3.8 o superior
- Git

## Instalación

1. **Clona el repositorio:**
   ```bash
   git clone https://github.com/AstridCarolinaAr/MONAPP.git
   cd MONAPP
   ```

2. **Crea un entorno virtual:**
   ```bash
   python -m venv venv
   # En Windows:
   venv\Scripts\activate
   # En Linux/Mac:
   source venv/bin/activate
   ```

3. **Instala dependencias:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configura variables de entorno:**
   ```bash
   cp .env.example .env
   ```
   Edita `.env` y configura:
   - `SECRET_KEY`: Genera una nueva clave secreta para producción
   - `EMAIL_HOST_PASSWORD`: Tu contraseña de aplicación de Gmail
   - `DEBUG`: True para desarrollo, False para producción

5. **Ejecuta migraciones:**
   ```bash
   python manage.py migrate
   ```

6. **Crea superusuario (opcional):**
   ```bash
   python manage.py createsuperuser
   ```

7. **Ejecuta el servidor:**
   ```bash
   python manage.py runserver
   ```

8. **Accede a la aplicación:**
   Abre http://localhost:8000 en tu navegador

## Configuración de Producción

Para producción:
- Cambia `DEBUG = False` en `.env`
- Configura un servidor web (nginx/apache) para servir archivos estáticos
- Usa una base de datos más robusta (PostgreSQL/MySQL)
- Configura `ALLOWED_HOSTS` con tu dominio

## Contribución

Para contribuir, crea un fork del proyecto y envía un pull request.

## Licencia

Este proyecto está bajo la licencia MIT.

