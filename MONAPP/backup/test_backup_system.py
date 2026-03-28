#!/usr/bin/env python
"""
Script de prueba para validar el sistema de backups
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'MONAPP.settings')
django.setup()

from backup.services import get_database_stats
from backup.models import BackupRecord, BackupConfig


def main():
    print("=" * 60)
    print("PRUEBA DEL SISTEMA DE BACKUPS")
    print("=" * 60)

    stats = get_database_stats()
    print('\nEstadisticas de Base de Datos:')
    print(f'   - BD Size: {stats["db_size_legible"]}')
    print(f'   - Total Tablas: {stats["total_tablas"]}')
    print(f'   - Total Registros: {stats["total_registros"]}')
    print(f'   - Media Size: {stats["media_size_legible"]}')
    print(f'   - Media Files: {stats["media_files"]}')

    config = BackupConfig.get_config()
    print('\nConfiguracion de Backups:')
    print(f'   - Backup Automatico: {"SI" if config.backup_automatico else "NO"}')
    print(f'   - Frecuencia: {config.frecuencia_horas} horas')
    print(f'   - Max Backups: {config.max_backups}')
    print(f'   - Incluir Media: {"SI" if config.incluir_media else "NO"}')
    ruta = config.ruta_backups if config.ruta_backups else "predeterminada"
    print(f'   - Ruta: {ruta}')

    backups = BackupRecord.objects.all().order_by('-fecha_creacion')[:10]
    print(f'\nUltimos {backups.count()} Backups:')
    if backups:
        for i, b in enumerate(backups, 1):
            archivo_str = "SI" if b.archivo_existe else "NO"
            print(f'   {i}. {b.nombre}')
            print(f'      - Tipo: {b.tipo} | Estado: {b.estado}')
            print(f'      - Tamano: {b.tamano_legible} | Archivo: {archivo_str}')
            print(f'      - Usuario: {b.usuario.username if b.usuario else "Sistema"}')
            print()
    else:
        print("   No hay backups creados aun")

    print("=" * 60)


if __name__ == "__main__":
    main()
