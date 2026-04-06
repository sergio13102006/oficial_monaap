import logging

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from backup.services.backup_service import create_full_backup
from backup.services.config_service import get_backup_config


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Ejecuta una copia automatica segun BackupConfig."

    def handle(self, *args, **options):
        config = get_backup_config()
        logger.info(
            "Scheduler backup: inicio automatico=%s frecuencia_horas=%s incluir_media=%s ruta_backups=%s",
            config.backup_automatico,
            config.frecuencia_horas,
            config.incluir_media,
            config.ruta_backups or "backups/",
        )
        if not config.backup_automatico:
            logger.info("Backup automatico omitido: deshabilitado en configuracion.")
            self.stdout.write(self.style.WARNING("El backup automatico esta deshabilitado."))
            return

        ultimo = config.ultimo_backup
        if ultimo:
            delta_horas = (timezone.now() - ultimo).total_seconds() / 3600
            if delta_horas < max(config.frecuencia_horas, 1):
                logger.info("Backup automatico omitido: frecuencia aun no cumplida.")
                self.stdout.write(
                    self.style.WARNING(
                        f"Aun no corresponde ejecutar backup automatico. Faltan {config.frecuencia_horas - delta_horas:.2f} horas."
                    )
                )
                return
        try:
            logger.info("Iniciando backup automatico. incluir_media=%s", config.incluir_media)
            record = create_full_backup(
                nombre=None,
                usuario=None,
                notas="Backup automatico programado",
                include_media=config.incluir_media,
            )
        except Exception as exc:
            logger.exception("Fallo el backup automatico")
            raise CommandError(str(exc)) from exc

        config.ultimo_backup = record.fecha_creacion
        config.save(update_fields=["ultimo_backup"])
        logger.info(
            "Backup automatico completado. nombre=%s tipo=%s tamano=%s checksum=%s",
            record.nombre,
            record.tipo,
            record.tamano,
            record.checksum,
        )
        self.stdout.write(self.style.SUCCESS(f"Backup automatico creado: {record.nombre}"))
