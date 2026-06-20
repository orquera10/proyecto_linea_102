from django.contrib import admin

from .models import InformeLlamada, RegistroLlamada


@admin.register(InformeLlamada)
class InformeLlamadaAdmin(admin.ModelAdmin):
    list_display = (
        'fecha',
        'hora',
        'motivo',
        'tipo',
        'estado',
        'requiere_seguimiento',
        'creado_por',
    )
    list_filter = ('tipo', 'estado', 'requiere_seguimiento', 'fecha')
    search_fields = ('motivo', 'descripcion', 'telefono', 'nombre_llamante')
    readonly_fields = ('creado', 'actualizado')


@admin.register(RegistroLlamada)
class RegistroLlamadaAdmin(admin.ModelAdmin):
    list_display = (
        'inicio',
        'numero_origen',
        'numero_destino',
        'estado',
        'duracion_segundos',
        'conversacion_segundos',
        'linea_origen',
    )
    list_filter = ('estado', 'linea_origen', 'inicio')
    search_fields = ('numero_origen', 'numero_destino', 'nombre_llamante', 'id_unico')
    readonly_fields = ('creado',)
