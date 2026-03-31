import base64
import binascii
import re
import uuid

from django import forms
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from .models import GestionAlisado
from clientes.models import Cliente
from personal.models import Personal
from servicios.models import Servicio
from core.form_validations import ValidationFormMixin


class MoneyTextInput(forms.TextInput):
    def format_value(self, value):
        if value is None or value == '':
            return ''

        raw = str(value).strip()
        digits = re.sub(r'[^\d-]', '', raw)
        if digits in ('', '-'):
            return ''

        negative = digits.startswith('-')
        if negative:
            digits = digits[1:]

        try:
            formatted = f'{int(digits):,}'.replace(',', '.')
        except (TypeError, ValueError):
            return raw

        return f'-{formatted}' if negative else formatted


class MoneyIntegerField(forms.IntegerField):
    def to_python(self, value):
        if value in self.empty_values:
            return None
        if isinstance(value, str):
            value = re.sub(r'[^\d-]', '', value.strip())
        return super().to_python(value)


class GestionAlisadoForm(ValidationFormMixin, forms.ModelForm):
    firma_consentimiento_data = forms.CharField(required=False, widget=forms.HiddenInput())
    precio_alisado = MoneyIntegerField(required=True, widget=MoneyTextInput(attrs={
        'class': 'form-control gestion-money-input',
        'min': '0',
        'inputmode': 'numeric',
        'placeholder': 'Precio del alisado en COP',
        'required': 'required',
        'oninput': 'window.gestionAlisadoMoneyInput && window.gestionAlisadoMoneyInput(this)',
        'onblur': 'window.gestionAlisadoMoneyInput && window.gestionAlisadoMoneyInput(this)',
        'onfocus': 'window.gestionAlisadoMoneyFocus && window.gestionAlisadoMoneyFocus(this)',
    }))
    anticipo_cliente = MoneyIntegerField(required=True, widget=MoneyTextInput(attrs={
        'class': 'form-control gestion-money-input',
        'min': '0',
        'inputmode': 'numeric',
        'placeholder': 'Anticipo realizado en COP',
        'required': 'required',
        'oninput': 'window.gestionAlisadoMoneyInput && window.gestionAlisadoMoneyInput(this)',
        'onblur': 'window.gestionAlisadoMoneyInput && window.gestionAlisadoMoneyInput(this)',
        'onfocus': 'window.gestionAlisadoMoneyFocus && window.gestionAlisadoMoneyFocus(this)',
    }))
    saldo_pendiente = MoneyIntegerField(required=False, widget=MoneyTextInput(attrs={
        'class': 'form-control gestion-money-input',
        'min': '0',
        'inputmode': 'numeric',
        'placeholder': 'Saldo pendiente en COP',
        'readonly': 'readonly',
    }))

    class Meta:
        model = GestionAlisado
        fields = [
            'cliente', 'precio_alisado', 'es_oferta_especial', 'descripcion_oferta',
            'anticipo_cliente', 'medio_pago', 'saldo_pendiente',
            'procedimiento_realizado_por', 'tipo_alisado', 'requiere_resellado',
            'porcentaje_alisado', 'porosidad', 'textura', 'forma_natural',
            'elasticidad', 'longitud', 'densidad', 'piel_cabelludo',
            'alopecia', 'caida_cabello', 'lactante', 'gestante', 'caspa',
            'procesos_tintura', 'procesos_decoloracion', 'procesos_ondulados',
            'procesos_extracciones', 'procesos_alisados', 'procesos_super_aclarante',
            'procesos_otro', 'cuenta_con_secador', 'frecuencia_recoge_cabello',
            'realiza_ejercicio', 'frecuencia_ejercicio', 'usa_casco',
            'productos_capilares', 'se_bana_agua_caliente', 'requiere_refuerzo_15dias',
            'sufre_tiroides', 'medicamento_tiroides', 'despunte_hoy',
            'recomendaciones_post_cuidados', 'firma_consentimiento'
        ]
        widgets = {
            'cliente': forms.Select(attrs={
                'class': 'form-select',
                'required': 'required',
                'id': 'selectCliente'
            }),
            'es_oferta_especial': forms.Select(attrs={
                'class': 'form-select',
                'required': 'required'
            }),
            'descripcion_oferta': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Describe la promoción'
            }),
            'medio_pago': forms.Select(attrs={
                'class': 'form-select',
                'required': 'required'
            }),
            'procedimiento_realizado_por': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre del profesional',
                'required': 'required'
            }),
            'tipo_alisado': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Describe el tipo de alisado a realizar',
                'required': 'required'
            }),
            'requiere_resellado': forms.Select(attrs={
                'class': 'form-select',
                'required': 'required'
            }),
            'porcentaje_alisado': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'max': '100',
                'placeholder': 'Porcentaje',
                'required': 'required'
            }),
            'porosidad': forms.Select(attrs={
                'class': 'form-select',
                'required': 'required'
            }),
            'textura': forms.Select(attrs={
                'class': 'form-select',
                'required': 'required'
            }),
            'forma_natural': forms.Select(attrs={
                'class': 'form-select',
                'required': 'required'
            }),
            'elasticidad': forms.Select(attrs={
                'class': 'form-select',
                'required': 'required'
            }),
            'longitud': forms.Select(attrs={
                'class': 'form-select',
                'required': 'required'
            }),
            'densidad': forms.Select(attrs={
                'class': 'form-select',
                'required': 'required'
            }),
            'piel_cabelludo': forms.Select(attrs={
                'class': 'form-select',
                'required': 'required'
            }),
            'alopecia': forms.Select(attrs={
                'class': 'form-select',
                'required': 'required'
            }),
            'caida_cabello': forms.Select(attrs={
                'class': 'form-select',
                'required': 'required'
            }),
            'lactante': forms.Select(attrs={
                'class': 'form-select',
                'required': 'required'
            }),
            'gestante': forms.Select(attrs={
                'class': 'form-select',
                'required': 'required'
            }),
            'caspa': forms.Select(attrs={
                'class': 'form-select',
                'required': 'required'
            }),
            'procesos_tintura': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'procesos_decoloracion': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'procesos_ondulados': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'procesos_extracciones': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'procesos_alisados': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'procesos_super_aclarante': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'procesos_otro': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Especifique otros procesos'
            }),
            'cuenta_con_secador': forms.Select(attrs={
                'class': 'form-select',
                'required': 'required'
            }),
            'frecuencia_recoge_cabello': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Frecuencia con la que recoge su cabello',
                'required': 'required'
            }),
            'realiza_ejercicio': forms.Select(attrs={
                'class': 'form-select',
                'required': 'required'
            }),
            'frecuencia_ejercicio': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Cuántas veces a la semana'
            }),
            'usa_casco': forms.Select(attrs={
                'class': 'form-select',
                'required': 'required'
            }),
            'productos_capilares': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Marca de shampoo, acondicionador y mascarilla',
                'required': 'required'
            }),
            'se_bana_agua_caliente': forms.Select(attrs={
                'class': 'form-select',
                'required': 'required'
            }),
            'requiere_refuerzo_15dias': forms.Select(attrs={
                'class': 'form-select',
                'required': 'required'
            }),
            'sufre_tiroides': forms.Select(attrs={
                'class': 'form-select',
                'required': 'required'
            }),
            'medicamento_tiroides': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Especifique el medicamento'
            }),
            'despunte_hoy': forms.Select(attrs={
                'class': 'form-select',
                'required': 'required'
            }),
            'recomendaciones_post_cuidados': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Recomendaciones o anotaciones sobre post cuidados',
                'required': 'required'
            }),
            'firma_consentimiento': forms.HiddenInput(),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['firma_consentimiento_data'].widget.attrs['form'] = 'gestionAlisadoForm'
        self.fields['firma_consentimiento'].widget.attrs['form'] = 'gestionAlisadoForm'
        # Cargar clientes activos en el dropdown
        self.fields['cliente'].queryset = Cliente.objects.filter(estado='activo').order_by('nombre', 'apellido')
        # Función para mostrar nombre completo y documento
        self.fields['cliente'].label_from_instance = lambda obj: f"{obj.nombre} {obj.apellido} - {obj.numero_documento}"

        colaboradores = Personal.objects.filter(rol='Colaborador', activo=True).order_by('nombres', 'apellidos')
        colaborador_choices = [('', 'Seleccione un colaborador...')]
        colaborador_choices.extend([(str(personal), str(personal)) for personal in colaboradores])

        valor_actual = (self.initial.get('procedimiento_realizado_por') or self.data.get('procedimiento_realizado_por') or '').strip()
        if valor_actual and valor_actual not in {value for value, _ in colaborador_choices}:
            colaborador_choices.append((valor_actual, valor_actual))

        self.fields['procedimiento_realizado_por'] = forms.ChoiceField(
            choices=colaborador_choices,
            required=True,
            widget=forms.Select(attrs={
                'class': 'form-select',
                'required': 'required',
            })
        )
        if valor_actual:
            self.fields['procedimiento_realizado_por'].initial = valor_actual

        servicios = Servicio.objects.filter(activo=True).order_by('nombre')
        servicio_choices = [('', 'Seleccione un servicio...')]
        servicio_choices.extend([(servicio.nombre, servicio.nombre) for servicio in servicios])

        tipo_actual = (self.initial.get('tipo_alisado') or self.data.get('tipo_alisado') or '').strip()
        permitir_valor_actual = self.is_bound or bool(getattr(self.instance, 'pk', None))
        if tipo_actual and permitir_valor_actual and tipo_actual not in {value for value, _ in servicio_choices}:
            servicio_choices.append((tipo_actual, tipo_actual))

        self.fields['tipo_alisado'] = forms.ChoiceField(
            choices=servicio_choices,
            required=True,
            widget=forms.Select(attrs={
                'class': 'form-select',
                'required': 'required',
            })
        )
        if tipo_actual and (permitir_valor_actual or tipo_actual in {value for value, _ in servicio_choices}):
            self.fields['tipo_alisado'].initial = tipo_actual

    @staticmethod
    def _money_to_int(value):
        if value in (None, ''):
            return None
        raw = str(value).strip()
        digits = re.sub(r'[^\d-]', '', raw)
        if digits in ('', '-'):
            return None
        return int(digits)

    def clean(self):
        cleaned_data = super().clean()
        precio = self._money_to_int(cleaned_data.get('precio_alisado'))
        anticipo = self._money_to_int(cleaned_data.get('anticipo_cliente'))
        saldo = self._money_to_int(cleaned_data.get('saldo_pendiente'))

        if precio is not None:
            cleaned_data['precio_alisado'] = precio
        if anticipo is not None:
            cleaned_data['anticipo_cliente'] = anticipo

        # Calcular saldo pendiente autom?ticamente
        if precio is not None and anticipo is not None:
            cleaned_data['saldo_pendiente'] = max(0, precio - anticipo)
        elif saldo is not None:
            cleaned_data['saldo_pendiente'] = saldo

        firma_data = (cleaned_data.get('firma_consentimiento_data') or '').strip()
        tiene_firma_existente = bool(getattr(self.instance, 'firma_consentimiento', None))
        if not firma_data and not tiene_firma_existente:
            self.add_error('firma_consentimiento_data', 'Registra la firma del cliente para continuar.')

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        firma_data = (self.cleaned_data.get('firma_consentimiento_data') or '').strip()

        if firma_data.startswith('data:image'):
            try:
                header, encoded = firma_data.split(',', 1)
                extension = 'png'
                if 'jpeg' in header or 'jpg' in header:
                    extension = 'jpg'
                image_bytes = base64.b64decode(encoded)
                file_name = f'{uuid.uuid4().hex}.{extension}'
                instance.firma_consentimiento.save(file_name, ContentFile(image_bytes), save=False)
            except (ValueError, TypeError, ValidationError, binascii.Error) as exc:
                raise ValidationError({'firma_consentimiento_data': 'No fue posible procesar la firma.'}) from exc

        if commit:
            instance.save()
            self.save_m2m()
        return instance

    def clean_tipo_alisado(self):
        tipo_alisado = (self.cleaned_data.get('tipo_alisado') or '').strip()
        if not tipo_alisado:
            raise forms.ValidationError('Debes seleccionar un servicio.')

        existe_en_catalogo = Servicio.objects.filter(nombre__iexact=tipo_alisado).exists()
        es_valor_existente = bool(
            getattr(self.instance, 'pk', None) and (self.instance.tipo_alisado or '').strip() == tipo_alisado
        )

        if not existe_en_catalogo and not es_valor_existente:
            raise forms.ValidationError('El servicio seleccionado no es válido.')

        return tipo_alisado
