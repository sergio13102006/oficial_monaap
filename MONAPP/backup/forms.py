import re

from django import forms

from .models import BackupConfig


SAFE_NAME_RE = re.compile(r"[a-zA-Z0-9_\-áéíóúñ\s\.]+")


class BackupCreateForm(forms.Form):
    nombre = forms.CharField(required=False, max_length=255)
    notas = forms.CharField(required=False, max_length=500, widget=forms.Textarea)

    def clean_nombre(self):
        nombre = (self.cleaned_data.get("nombre") or "").strip()
        if not nombre:
            return ""
        if len(nombre) < 3:
            raise forms.ValidationError("El nombre debe tener al menos 3 caracteres.")
        if not SAFE_NAME_RE.fullmatch(nombre):
            raise forms.ValidationError(
                "El nombre contiene caracteres no permitidos."
            )
        return nombre


class BackupImportForm(forms.Form):
    archivo_backup = forms.FileField(required=True)
    notas = forms.CharField(required=False, max_length=500, widget=forms.Textarea)
    restaurar_despues = forms.BooleanField(required=False)

    def clean_archivo_backup(self):
        archivo = self.cleaned_data["archivo_backup"]
        if not archivo.name.lower().endswith(".zip"):
            raise forms.ValidationError("Debes seleccionar un archivo ZIP.")
        return archivo


class BackupConfigForm(forms.ModelForm):
    class Meta:
        model = BackupConfig
        fields = (
            "backup_automatico",
            "frecuencia_horas",
            "max_backups",
            "incluir_media",
            "ruta_backups",
        )

    def clean_frecuencia_horas(self):
        value = self.cleaned_data["frecuencia_horas"]
        if value < 1:
            raise forms.ValidationError("La frecuencia debe ser mayor a 0.")
        return value

    def clean_max_backups(self):
        value = self.cleaned_data["max_backups"]
        if value < 1:
            raise forms.ValidationError("Debe conservarse al menos una copia.")
        return value

