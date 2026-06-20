from django.conf import settings
from django.db import models
from django.urls import reverse


class InformeLlamada(models.Model):
    class TipoLlamada(models.TextChoices):
        CONSULTA = 'consulta', 'Consulta'
        EMERGENCIA = 'emergencia', 'Emergencia'
        DENUNCIA = 'denuncia', 'Denuncia'
        SEGUIMIENTO = 'seguimiento', 'Seguimiento'
        OTRO = 'otro', 'Otro'

    class Estado(models.TextChoices):
        ABIERTA = 'abierta', 'Abierta'
        EN_PROCESO = 'en_proceso', 'En proceso'
        DERIVADA = 'derivada', 'Derivada'
        CERRADA = 'cerrada', 'Cerrada'

    fecha = models.DateField()
    hora = models.TimeField()
    telefono = models.CharField(max_length=30, blank=True)
    nombre_llamante = models.CharField('nombre del llamante', max_length=120, blank=True)
    tipo = models.CharField(max_length=20, choices=TipoLlamada.choices, default=TipoLlamada.CONSULTA)
    motivo = models.CharField(max_length=180)
    descripcion = models.TextField()
    intervencion = models.TextField(blank=True)
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.ABIERTA)
    requiere_seguimiento = models.BooleanField(default=False)
    fecha_seguimiento = models.DateField(blank=True, null=True)
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='informes_llamadas',
    )
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-fecha', '-hora', '-creado']
        verbose_name = 'informe de llamada'
        verbose_name_plural = 'informes de llamadas'

    def __str__(self):
        return f'{self.fecha} {self.hora} - {self.motivo}'

    def get_absolute_url(self):
        return reverse('llamadas:detail', kwargs={'pk': self.pk})


class RegistroLlamada(models.Model):
    class Estado(models.TextChoices):
        ANSWERED = 'ANSWERED', 'Contestada'
        NO_ANSWER = 'NO ANSWER', 'No contestada'
        FAILED = 'FAILED', 'Fallida'
        BUSY = 'BUSY', 'Ocupada'

    id_unico = models.CharField(max_length=80, unique=True)
    numero_origen = models.CharField(max_length=60, blank=True)
    numero_destino = models.CharField(max_length=60, blank=True)
    nombre_llamante = models.CharField(max_length=120, blank=True)
    respondido_por = models.CharField(max_length=80, blank=True)
    linea_origen = models.CharField(max_length=80, blank=True)
    tipo_registro = models.CharField(max_length=40, blank=True)
    estado = models.CharField(max_length=20, choices=Estado.choices)
    inicio = models.DateTimeField()
    respondida = models.DateTimeField(blank=True, null=True)
    finalizacion = models.DateTimeField(blank=True, null=True)
    duracion_segundos = models.PositiveIntegerField(default=0)
    conversacion_segundos = models.PositiveIntegerField(default=0)
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-inicio']
        verbose_name = 'registro de llamada'
        verbose_name_plural = 'registros de llamadas'
        indexes = [
            models.Index(fields=['inicio']),
            models.Index(fields=['estado']),
            models.Index(fields=['linea_origen']),
        ]

    def __str__(self):
        return f'{self.inicio:%Y-%m-%d %H:%M} - {self.get_estado_display()}'
