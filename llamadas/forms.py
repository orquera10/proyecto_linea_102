from django import forms
from django.utils import timezone

from .models import InformeLlamada


class ImportarLlamadasForm(forms.Form):
    archivo = forms.FileField(
        label='Archivo CSV',
        help_text='Acepta el CSV exportado del sistema telefonico. Los registros ya importados se omiten por ID unico.',
    )

    def clean_archivo(self):
        archivo = self.cleaned_data['archivo']
        if not archivo.name.lower().endswith('.csv'):
            raise forms.ValidationError('El archivo debe tener extension .csv.')
        return archivo


class InformeLlamadaForm(forms.ModelForm):
    class Meta:
        model = InformeLlamada
        fields = (
            'fecha',
            'hora',
            'telefono',
            'nombre_llamante',
            'tipo',
            'motivo',
            'descripcion',
            'intervencion',
            'estado',
            'requiere_seguimiento',
            'fecha_seguimiento',
        )
        widgets = {
            'fecha': forms.DateInput(attrs={'type': 'date'}),
            'hora': forms.TimeInput(attrs={'type': 'time'}),
            'fecha_seguimiento': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        now = timezone.localtime()
        self.fields['fecha'].initial = self.fields['fecha'].initial or now.date()
        self.fields['hora'].initial = self.fields['hora'].initial or now.strftime('%H:%M')
