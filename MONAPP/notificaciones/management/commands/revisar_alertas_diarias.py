from django.core.management.base import BaseCommand
from django.utils import timezone

from notificaciones.alertas_diarias import destinatarios_admin_aux, generar_alertas_para_usuario


class Command(BaseCommand):
    help = "Crea notificaciones diarias: promociones por vencer y cumpleaños (hoy/mañana)."

    def handle(self, *args, **options):
        hoy = timezone.localdate()
        users = destinatarios_admin_aux()
        for u in users:
            generar_alertas_para_usuario(u, fecha_base=hoy)

        self.stdout.write(self.style.SUCCESS(f"✓ Alertas diarias revisadas para {len(users)} usuario(s)."))

