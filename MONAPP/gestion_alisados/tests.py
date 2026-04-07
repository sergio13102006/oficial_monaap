from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.urls import reverse

from clientes.models import Cliente
from personal.models import Personal
from servicios.models import Servicio

from .models import AtencionServicio, GestionAlisado, TabletConsentToken, TabletKioskState, TratamientoDatosFirmado
from .services.realtime_notifications import build_runtime_event, notify_session_assigned
from .services.realtime_service import generate_tablet_ws_token, validate_tablet_ws_token
from .services import start_tablet_session


SIGNATURE_PNG = (
    "data:image/png;base64,"
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO7Z0n0AAAAASUVORK5CYII="
)


class GestionAlisadoBaseTestCase(TestCase):
    def setUp(self):
        self.user_model = get_user_model()
        self.staff_user = self.user_model.objects.create_user(
            username="staff",
            password="test12345",
            is_staff=True,
            is_superuser=True,
        )
        self.normal_user = self.user_model.objects.create_user(
            username="normal",
            password="test12345",
            is_staff=False,
        )
        self.cliente = Cliente.objects.create(
            tipo_documento="CC",
            numero_documento="1234567890",
            nombre="Cliente",
            apellido="Test",
            fecha_nacimiento="1990-01-15",
            telefono="3001234567",
            correo="cliente@test.com",
            estado="activo",
        )
        self.personal = Personal.objects.create(
            tipo_documento="CC",
            numero_documento="987654321",
            nombres="Laura",
            apellidos="Diaz",
            correo="laura@test.com",
            telefono="3009876543",
            rol="Colaborador",
            activo=True,
        )
        self.servicio = Servicio.objects.create(
            nombre="Alisado Premium",
            precio=120000,
            descripcion="Servicio de alisado premium para pruebas",
            activo=True,
        )

    def gestion_kwargs(self, **overrides):
        data = {
            "cliente": self.cliente,
            "precio_alisado": 50000,
            "es_oferta_especial": "no",
            "descripcion_oferta": "",
            "anticipo_cliente": 20000,
            "medio_pago": "efectivo",
            "saldo_pendiente": 30000,
            "procedimiento_realizado_por": str(self.personal),
            "tipo_alisado": self.servicio.nombre,
            "requiere_resellado": "no",
            "porcentaje_alisado": 80,
            "porosidad": "media",
            "textura": "normal",
            "forma_natural": "ondulado",
            "elasticidad": "media",
            "longitud": "largo",
            "densidad": "media",
            "piel_cabelludo": "normal",
            "alopecia": "no_presenta",
            "caida_cabello": "baja",
            "lactante": "no",
            "gestante": "no",
            "caspa": "no_presenta",
            "procesos_tintura": False,
            "procesos_decoloracion": False,
            "procesos_ondulados": False,
            "procesos_extracciones": False,
            "procesos_alisados": False,
            "procesos_super_aclarante": False,
            "procesos_otro": "",
            "cuenta_con_secador": "si",
            "frecuencia_recoge_cabello": "Todos los dias",
            "realiza_ejercicio": "si",
            "frecuencia_ejercicio": "3 veces por semana",
            "usa_casco": "no",
            "productos_capilares": "Shampoo de prueba",
            "se_bana_agua_caliente": "no",
            "requiere_refuerzo_15dias": "si",
            "sufre_tiroides": "no",
            "medicamento_tiroides": "",
            "despunte_hoy": "si",
            "recomendaciones_post_cuidados": "No usar agua caliente por 48 horas",
        }
        data.update(overrides)
        return data

    def gestion_form_payload(self, **overrides):
        data = self.gestion_kwargs(**overrides)
        payload = {
            "cliente": str(data["cliente"].pk) if data.get("cliente") else "",
            "precio_alisado": str(data["precio_alisado"]),
            "es_oferta_especial": data["es_oferta_especial"],
            "descripcion_oferta": data["descripcion_oferta"],
            "anticipo_cliente": str(data["anticipo_cliente"]),
            "medio_pago": data["medio_pago"],
            "saldo_pendiente": str(data["saldo_pendiente"]),
            "procedimiento_realizado_por": data["procedimiento_realizado_por"],
            "tipo_alisado": data["tipo_alisado"],
            "requiere_resellado": data["requiere_resellado"],
            "porcentaje_alisado": str(data["porcentaje_alisado"]),
            "porosidad": data["porosidad"],
            "textura": data["textura"],
            "forma_natural": data["forma_natural"],
            "elasticidad": data["elasticidad"],
            "longitud": data["longitud"],
            "densidad": data["densidad"],
            "piel_cabelludo": data["piel_cabelludo"],
            "alopecia": data["alopecia"],
            "caida_cabello": data["caida_cabello"],
            "lactante": data["lactante"],
            "gestante": data["gestante"],
            "caspa": data["caspa"],
            "cuenta_con_secador": data["cuenta_con_secador"],
            "frecuencia_recoge_cabello": data["frecuencia_recoge_cabello"],
            "realiza_ejercicio": data["realiza_ejercicio"],
            "frecuencia_ejercicio": data["frecuencia_ejercicio"],
            "usa_casco": data["usa_casco"],
            "productos_capilares": data["productos_capilares"],
            "se_bana_agua_caliente": data["se_bana_agua_caliente"],
            "requiere_refuerzo_15dias": data["requiere_refuerzo_15dias"],
            "sufre_tiroides": data["sufre_tiroides"],
            "medicamento_tiroides": data["medicamento_tiroides"],
            "despunte_hoy": data["despunte_hoy"],
            "recomendaciones_post_cuidados": data["recomendaciones_post_cuidados"],
            "firma_consentimiento_data": SIGNATURE_PNG,
            "consentimiento_nombre": "Cliente Test",
            "consentimiento_cedula": self.cliente.numero_documento,
            "consentimiento_fecha": "1 de abril de 2026, 10:00",
            "consentimiento_aceptado": "true",
        }

        for boolean_name in [
            "procesos_tintura",
            "procesos_decoloracion",
            "procesos_ondulados",
            "procesos_extracciones",
            "procesos_alisados",
            "procesos_super_aclarante",
        ]:
            if data.get(boolean_name):
                payload[boolean_name] = "on"

        return payload


class GestionAlisadoModelTest(GestionAlisadoBaseTestCase):
    def setUp(self):
        super().setUp()
        self.gestion = GestionAlisado.objects.create(**self.gestion_kwargs())

    def test_crear_gestion_alisado_exitosamente(self):
        self.assertEqual(self.gestion.cliente.nombre, "Cliente")
        self.assertEqual(self.gestion.precio_alisado, 50000)
        self.assertEqual(self.gestion.anticipo_cliente, 20000)
        self.assertEqual(self.gestion.saldo_pendiente, 30000)
        self.assertEqual(self.gestion.medio_pago, "efectivo")
        self.assertEqual(self.gestion.porcentaje_alisado, 80)
        self.assertIsNotNone(self.gestion.id_gestion)
        self.assertIsNotNone(self.gestion.fecha_hora)

    def test_validacion_porcentaje_alisado(self):
        gestion_invalida = GestionAlisado(**self.gestion_kwargs(porcentaje_alisado=150))
        with self.assertRaises(ValidationError):
            gestion_invalida.full_clean()


class GestionAlisadoViewRegressionTest(GestionAlisadoBaseTestCase):
    def setUp(self):
        super().setUp()
        self.gestion = GestionAlisado.objects.create(**self.gestion_kwargs())

    def test_detail_modal_requires_staff(self):
        self.client.force_login(self.normal_user)
        response = self.client.get(
            reverse("gestion_alisados:ver_gestion_alisado_modal_content", args=[self.gestion.pk])
        )
        self.assertEqual(response.status_code, 403)

    def test_modal_create_renders_launcher_shell(self):
        self.client.force_login(self.staff_user)
        response = self.client.get(reverse("gestion_alisados:crear_gestion_alisado") + "?modal=1")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-tablet-start-url-template=')
        self.assertContains(response, 'id="tabletStartProcess"')

    def test_modal_edit_post_returns_json_success(self):
        self.client.force_login(self.staff_user)
        response = self.client.post(
            reverse("gestion_alisados:editar_gestion_alisado", args=[self.gestion.pk]) + "?modal=1",
            data=self.gestion_form_payload(precio_alisado=80000, anticipo_cliente=30000, saldo_pendiente=50000),
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(response.status_code, 200)

        payload = response.json()
        self.assertTrue(payload["success"])
        self.assertNotEqual(payload["gestion_id"], str(self.gestion.pk))
        self.gestion.refresh_from_db()
        self.assertEqual(self.gestion.precio_alisado, 50000)
        self.assertEqual(self.gestion.anticipo_cliente, 20000)
        nueva_gestion = GestionAlisado.objects.get(pk=payload["gestion_id"])
        self.assertEqual(nueva_gestion.precio_alisado, 80000)
        self.assertEqual(nueva_gestion.anticipo_cliente, 30000)
        return

        self.client.force_login(self.staff_user)
        response = self.client.post(
            reverse("gestion_alisados:editar_gestion_alisado", args=[self.gestion.pk]) + "?modal=1",
            data=self.gestion_form_payload(precio_alisado=80000, anticipo_cliente=30000, saldo_pendiente=50000),
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(
            response.content,
            {
                "success": True,
                "message": "GestiÃ³n de alisado actualizada exitosamente.",
                "gestion_id": str(self.gestion.pk),
            },
        )

    def test_create_flow_generates_atencion_and_signed_treatment(self):
        self.client.force_login(self.staff_user)
        response = self.client.post(
            reverse("gestion_alisados:crear_gestion_alisado") + "?modal=1",
            data=self.gestion_form_payload(),
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(response.status_code, 201)

        gestion = GestionAlisado.objects.order_by("-fecha_hora").first()
        self.assertIsNotNone(gestion.atencion)
        self.assertIsNotNone(gestion.tratamiento_firmado)
        self.assertTrue(AtencionServicio.objects.filter(pk=gestion.atencion.pk).exists())
        self.assertTrue(TratamientoDatosFirmado.objects.filter(pk=gestion.tratamiento_firmado.pk).exists())
        self.assertEqual(gestion.atencion.cliente, self.cliente)
        self.assertEqual(gestion.tratamiento_firmado.cliente, self.cliente)
        self.assertEqual(gestion.tratamiento_firmado.atencion, gestion.atencion)
        self.assertEqual(gestion.tratamiento_firmado.estado, TratamientoDatosFirmado.ESTADO_FIRMADA)
        self.assertEqual(
            gestion.tratamiento_firmado.snapshot_cliente["numero_documento"],
            self.cliente.numero_documento,
        )

    def test_signed_treatment_creates_new_record_when_reopened(self):
        self.client.force_login(self.staff_user)
        response = self.client.post(
            reverse("gestion_alisados:crear_gestion_alisado") + "?modal=1",
            data=self.gestion_form_payload(),
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(response.status_code, 201)

        gestion = GestionAlisado.objects.order_by("-fecha_hora").first()
        edit_response = self.client.post(
            reverse("gestion_alisados:editar_gestion_alisado", args=[gestion.pk]) + "?modal=1",
            data=self.gestion_form_payload(precio_alisado=90000, anticipo_cliente=10000, saldo_pendiente=80000),
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(edit_response.status_code, 200)
        gestion.refresh_from_db()
        self.assertEqual(gestion.precio_alisado, 50000)
        self.assertEqual(gestion.saldo_pendiente, 30000)
        payload = edit_response.json()
        self.assertNotEqual(payload["gestion_id"], str(gestion.pk))
        nueva_gestion = GestionAlisado.objects.get(pk=payload["gestion_id"])
        self.assertEqual(nueva_gestion.precio_alisado, 90000)
        self.assertEqual(nueva_gestion.anticipo_cliente, 10000)

    def test_lista_muestra_historial_completo_de_gestiones_del_cliente(self):
        self.client.force_login(self.staff_user)
        response = self.client.post(
            reverse("gestion_alisados:editar_gestion_alisado", args=[self.gestion.pk]) + "?modal=1",
            data=self.gestion_form_payload(precio_alisado=90000, anticipo_cliente=10000, saldo_pendiente=80000),
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(response.status_code, 200)

        list_response = self.client.get(reverse("gestion_alisados:lista_gestion_alisados"))
        self.assertEqual(list_response.status_code, 200)
        self.assertContains(list_response, "1 tratamientos")
        self.assertEqual(list_response.context["gestiones"][0].historial_total, 1)

    def test_historial_modal_excluye_la_gestion_mas_reciente_mostrada_en_tabla(self):
        self.client.force_login(self.staff_user)
        response = self.client.post(
            reverse("gestion_alisados:editar_gestion_alisado", args=[self.gestion.pk]) + "?modal=1",
            data=self.gestion_form_payload(precio_alisado=90000, anticipo_cliente=10000, saldo_pendiente=80000),
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(response.status_code, 200)

        nueva_gestion = GestionAlisado.objects.get(pk=response.json()["gestion_id"])
        historial_response = self.client.get(
            reverse("gestion_alisados:ver_historial_cliente_modal", args=[self.cliente.pk])
        )

        self.assertEqual(historial_response.status_code, 200)
        self.assertContains(historial_response, "1 tratamientos")
        self.assertContains(historial_response, self.gestion.tipo_alisado)
        self.assertNotContains(historial_response, str(nueva_gestion.precio_alisado))

    def test_exports_do_not_break_when_cliente_is_null(self):
        GestionAlisado.objects.create(**self.gestion_kwargs(cliente=None))
        self.client.force_login(self.staff_user)

        csv_response = self.client.get(reverse("gestion_alisados:exportar_reporte_gestion_csv"))
        pdf_response = self.client.get(reverse("gestion_alisados:exportar_reporte_gestion_pdf"))
        detail_response = self.client.get(
            reverse("gestion_alisados:ver_gestion_alisado_modal_content", args=[GestionAlisado.objects.filter(cliente__isnull=True).first().pk])
        )

        self.assertEqual(csv_response.status_code, 200)
        self.assertContains(csv_response, "Sin cliente")
        self.assertEqual(pdf_response.status_code, 200)
        self.assertEqual(detail_response.status_code, 200)
        self.assertContains(detail_response, "Sin cliente")

    def test_tablet_session_state_flow(self):
        token = start_tablet_session(self.cliente, user=self.staff_user, minutos_validos=120)
        self.assertEqual(token.estado_proceso, TabletConsentToken.ESTADO_ENVIADA)

        open_response = self.client.get(
            reverse("gestion_alisados:tablet_gestion_alisado", args=[token.token])
        )
        self.assertEqual(open_response.status_code, 200)
        token.refresh_from_db()
        self.assertEqual(token.estado_proceso, TabletConsentToken.ESTADO_ABIERTA)
        self.assertIsNotNone(token.abierta_en)

        sign_response = self.client.post(
            reverse("gestion_alisados:tablet_gestion_alisado", args=[token.token]),
            data=self.gestion_form_payload(),
        )
        self.assertEqual(sign_response.status_code, 200)
        token.refresh_from_db()
        self.assertEqual(token.estado_proceso, TabletConsentToken.ESTADO_FIRMADA)
        self.assertFalse(token.activo)
        self.assertIsNotNone(token.usado_en)

    def test_tablet_session_expired_state_is_reported(self):
        token = start_tablet_session(self.cliente, user=self.staff_user, minutos_validos=-1)
        response = self.client.get(
            reverse("gestion_alisados:tablet_gestion_alisado", args=[token.token])
        )
        self.assertEqual(response.status_code, 410)
        token.refresh_from_db()
        self.assertEqual(token.estado_proceso, TabletConsentToken.ESTADO_EXPIRADA)
        self.assertFalse(token.activo)

    def test_tablet_wait_view_exposes_websocket_url(self):
        response = self.client.get(reverse("gestion_alisados:tablet_espera"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'const tabletWsUrl = "ws://testserver/ws/gestion')
        self.assertContains(response, "access_token")

    def test_tablet_wait_view_preserves_ready_session(self):
        token = start_tablet_session(self.cliente, user=self.staff_user, minutos_validos=120)
        kiosk_state, _ = TabletKioskState.objects.get_or_create(
            pk=TabletKioskState.SINGLETON_ID,
            defaults={"estado": TabletKioskState.ESTADO_ESPERA},
        )
        kiosk_state.marcar_listo(self.cliente, token)

        response = self.client.get(reverse("gestion_alisados:tablet_espera"))

        self.assertEqual(response.status_code, 200)
        kiosk_state.refresh_from_db()
        self.assertEqual(kiosk_state.estado, TabletKioskState.ESTADO_LISTO)
        self.assertEqual(kiosk_state.token_id, token.token)

        estado_response = self.client.get(reverse("gestion_alisados:tablet_espera_estado"))
        self.assertEqual(estado_response.status_code, 200)
        self.assertJSONEqual(
            estado_response.content,
            {
                "success": True,
                "has_process": True,
                "process_state": token.estado_proceso,
                "process_state_label": token.get_estado_proceso_display(),
                "cliente": {
                    "nombre": f"{self.cliente.nombre} {self.cliente.apellido}",
                    "documento": self.cliente.numero_documento,
                },
                "tablet_process_url": f"http://testserver{reverse('gestion_alisados:tablet_gestion_alisado', args=[token.token])}",
            },
        )

    @override_settings(ENABLE_CHANNELS=False)
    def test_realtime_notifications_fallback_cleanly_when_channels_are_disabled(self):
        token = start_tablet_session(self.cliente, user=self.staff_user, minutos_validos=120)
        sent = notify_session_assigned(
            "default-tablet",
            str(token.token),
            payload={"tablet_process_url": "/fake/process/"},
        )
        self.assertFalse(sent)

    def test_runtime_event_contract_is_uniform(self):
        event = build_runtime_event(
            "session_assigned",
            tablet_id="default-tablet",
            session_id="abc123",
            status="enviada_a_tablet",
            payload={"tablet_process_url": "/fake/process/"},
            source="test_case",
        )
        self.assertEqual(event["type"], "session_assigned")
        self.assertEqual(event["session_id"], "abc123")
        self.assertEqual(event["tablet_id"], "default-tablet")
        self.assertEqual(event["status"], "enviada_a_tablet")
        self.assertEqual(event["source"], "test_case")
        self.assertEqual(event["event_id"], event["message_id"])
        self.assertEqual(event["contract_version"], 1)
        self.assertIn("timestamp", event)
        self.assertEqual(event["payload"]["tablet_process_url"], "/fake/process/")

    def test_tablet_websocket_token_must_match_tablet_id(self):
        access_token = generate_tablet_ws_token("default-tablet")
        self.assertTrue(validate_tablet_ws_token("default-tablet", access_token))
        self.assertFalse(validate_tablet_ws_token("otra-tablet", access_token))
        self.assertFalse(validate_tablet_ws_token("default-tablet", "token-invalido"))
