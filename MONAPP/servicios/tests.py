from django.test import TestCase
from django.core.exceptions import ValidationError
from decimal import Decimal
from .models import Servicio


class ServicioModelTest(TestCase):
    """Pruebas unitarias para el modelo Servicio"""
    
    def setUp(self):
        """Configura los datos de prueba"""
        self.servicio = Servicio.objects.create(
            nombre='Corte de Cabello',
            precio=Decimal('50.00'),
            descripcion='Corte de cabello profesional',
            activo=True
        )
    
    def test_crear_servicio_exitosamente(self):
        """Prueba que un servicio se crea correctamente con datos válidos"""
        self.assertEqual(self.servicio.nombre, 'Corte de Cabello')
        self.assertEqual(self.servicio.precio, Decimal('50.00'))
        self.assertEqual(self.servicio.descripcion, 'Corte de cabello profesional')
        self.assertTrue(self.servicio.activo)
        self.assertIsNotNone(self.servicio.id_servicio)
        self.assertIsNotNone(self.servicio.fecha_creacion)
    
    def test_str_method(self):
        """Prueba que el método __str__ devuelve el formato esperado"""
        expected_str = 'Corte de Cabello - $50.00'
        self.assertEqual(str(self.servicio), expected_str)
