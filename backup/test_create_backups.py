#!/usr/bin/env python
"""
Script para crear backups de prueba y validar su funcionamiento
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'MONAPP.settings')
django.setup()

from backup.services import crear_backup_base_datos, crear_backup_completo, crear_backup_media
from backup.models import BackupRecord
from django.contrib.auth.models import User


def main():
    print("=" * 70)
    print("CREANDO BACKUPS DE PRUEBA")
    print("=" * 70)

    admin = User.objects.filter(is_superuser=True).first()
    if not admin:
        admin = User.objects.create_superuser('admin', 'admin@test.com', 'admin')
        print(f"Usuario admin creado: {admin.username}\n")

    try:
        print("\nPRUEBA 1: Creando backup de BASE DE DATOS...")
        try:
            backup_bd = crear_backup_base_datos(
                nombre='test_backup_bd',
                usuario=admin,
                notas='Backup de prueba - solo base de datos'
            )
            print("   Backup creado exitosamente")
            print(f"     - ID: {backup_bd.id}")
            print(f"     - Nombre: {backup_bd.nombre}")
            print(f"     - Tipo: {backup_bd.tipo}")
            print(f"     - Estado: {backup_bd.estado}")
            print(f"     - Tamano: {backup_bd.tamano_legible}")
            print(f"     - Archivo existe: {'SI' if backup_bd.archivo_existe else 'NO'}")
        except Exception as e:
            print(f"   Error: {str(e)}")

        print("\nPRUEBA 2: Creando backup COMPLETO (BD + Media)...")
        try:
            backup_completo = crear_backup_completo(
                nombre='test_backup_completo',
                usuario=admin,
                notas='Backup de prueba - completo'
            )
            print("   Backup creado exitosamente")
            print(f"     - ID: {backup_completo.id}")
            print(f"     - Nombre: {backup_completo.nombre}")
            print(f"     - Tipo: {backup_completo.tipo}")
            print(f"     - Estado: {backup_completo.estado}")
            print(f"     - Tamano: {backup_completo.tamano_legible}")
            print(f"     - Archivo existe: {'SI' if backup_completo.archivo_existe else 'NO'}")
        except Exception as e:
            print(f"   Error: {str(e)}")

        print("\nPRUEBA 3: Creando backup de MEDIA...")
        try:
            backup_media = crear_backup_media(
                nombre='test_backup_media',
                usuario=admin,
                notas='Backup de prueba - solo media'
            )
            print("   Backup creado exitosamente")
            print(f"     - ID: {backup_media.id}")
            print(f"     - Nombre: {backup_media.nombre}")
            print(f"     - Tipo: {backup_media.tipo}")
            print(f"     - Estado: {backup_media.estado}")
            print(f"     - Tamano: {backup_media.tamano_legible}")
            print(f"     - Archivo existe: {'SI' if backup_media.archivo_existe else 'NO'}")
        except Exception as e:
            print(f"   Error: {str(e)}")

        print("\n" + "=" * 70)
        print("RESUMEN DE BACKUPS CREADOS")
        print("=" * 70)

        backups = BackupRecord.objects.all().order_by('-fecha_creacion')
        print(f"\nTotal de backups en sistema: {backups.count()}\n")

        for i, b in enumerate(backups, 1):
            archivo_str = "SI" if b.archivo_existe else "NO"
            print(f"{i}. {b.nombre}")
            print(f"   - Tipo: {b.tipo} | Estado: {b.estado}")
            print(f"   - Tamano: {b.tamano_legible} | Duracion: {b.duracion_segundos}s")
            print(f"   - Usuario: {b.usuario.username if b.usuario else 'Sistema'} | Archivo: {archivo_str}")
            print()

    except Exception as e:
        print(f"\nError general: {str(e)}")
        import traceback
        traceback.print_exc()

    print("=" * 70)
    print("PRUEBAS COMPLETADAS")
    print("=" * 70)


if __name__ == "__main__":
    main()
