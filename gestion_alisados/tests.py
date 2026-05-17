from django.test import TestCase
from django.utils import timezone
from clientes.models import Cliente
from .models import GestionAlisado


class GestionAlisadoModelTest(TestCase):
    """Pruebas unitarias para el modelo GestionAlisado"""
    
    def setUp(self):
        """Configura los datos de prueba"""
        # Crear un cliente de prueba
        self.cliente = Cliente.objects.create(
            tipo_documento='CC',
            numero_documento='1234567890',
            nombre='Cliente',
            apellido='Test',
            fecha_nacimiento='1990-01-15',
            telefono='3001234567',
            correo='cliente@test.com',
            estado='activo'
        )
        
        # Crear una gestión de alisado
        self.gestion = GestionAlisado.objects.create(
            cliente=self.cliente,
            precio_alisado=50000,
            es_oferta_especial='no',
            anticipo_cliente=20000,
            medio_pago='efectivo',
            saldo_pendiente=30000,
            procedimiento_realizado_por='Colaborador Test',
            tipo_alisado='Alisado Brasileño',
            requiere_resellado='no',
            porcentaje_alisado=80,
            porosidad='media',
            textura='normal',
            forma_natural='ondulado',
            elasticidad='media',
            longitud='largo',
            densidad='media',
            piel_cabelludo='normal',
            alopecia='no_presenta',
            caida_cabello='baja',
            lactante='no',
            gestante='no',
            caspa='no_presenta',
            cuenta_con_secador='si',
            frecuencia_recoge_cabello='Todos los días',
            realiza_ejercicio='si',
            usa_casco='no',
            productos_capilares='TRESemmé',
            se_bana_agua_caliente='no',
            requiere_refuerzo_15dias='si',
            sufre_tiroides='no',
            despunte_hoy='si',
            recomendaciones_post_cuidados='No usar agua caliente por 48 horas'
        )
    
    def test_crear_gestion_alisado_exitosamente(self):
        """Prueba que una gestión de alisado se crea correctamente"""
        self.assertEqual(self.gestion.cliente.nombre, 'Cliente')
        self.assertEqual(self.gestion.precio_alisado, 50000)
        self.assertEqual(self.gestion.anticipo_cliente, 20000)
        self.assertEqual(self.gestion.saldo_pendiente, 30000)
        self.assertEqual(self.gestion.medio_pago, 'efectivo')
        self.assertEqual(self.gestion.porcentaje_alisado, 80)
        self.assertIsNotNone(self.gestion.id_gestion)
        self.assertIsNotNone(self.gestion.fecha_hora)
    
    def test_validacion_porcentaje_alisado(self):
        """Prueba que el porcentaje de alisado debe estar entre 0 y 100"""
        # Intenta crear una gestión con porcentaje inválido
        gestion_invalida = GestionAlisado(
            cliente=self.cliente,
            precio_alisado=50000,
            anticipo_cliente=20000,
            medio_pago='efectivo',
            procedimiento_realizado_por='Test',
            tipo_alisado='Alisado Test',
            porcentaje_alisado=150,  # Inválido, mayor a 100
            porosidad='media',
            textura='normal',
            forma_natural='liso',
            elasticidad='media',
            longitud='largo',
            densidad='media',
            piel_cabelludo='normal',
            alopecia='no_presenta',
            caida_cabello='baja',
            lactante='no',
            gestante='no',
            caspa='no_presenta',
            cuenta_con_secador='si',
            frecuencia_recoge_cabello='Todos los días',
            realiza_ejercicio='si',
            usa_casco='no',
            productos_capilares='Test',
            se_bana_agua_caliente='no',
            requiere_refuerzo_15dias='no',
            sufre_tiroides='no',
            despunte_hoy='no',
            recomendaciones_post_cuidados='Test'
        )
        # Validar que lanza excepción de validación
        from django.core.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            gestion_invalida.full_clean()
