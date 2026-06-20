import csv
import calendar
from datetime import datetime
from io import TextIOWrapper

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Avg, Count, Q
from django.db.models.functions import ExtractHour
from django.shortcuts import redirect, render
from django.utils import timezone
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from .forms import ImportarLlamadasForm, InformeLlamadaForm
from .models import InformeLlamada, RegistroLlamada


MESES = [
    (1, 'Enero'),
    (2, 'Febrero'),
    (3, 'Marzo'),
    (4, 'Abril'),
    (5, 'Mayo'),
    (6, 'Junio'),
    (7, 'Julio'),
    (8, 'Agosto'),
    (9, 'Septiembre'),
    (10, 'Octubre'),
    (11, 'Noviembre'),
    (12, 'Diciembre'),
]

ESTADO_COLORES = {
    RegistroLlamada.Estado.ANSWERED: '#17633a',
    RegistroLlamada.Estado.NO_ANSWER: '#d99a00',
    RegistroLlamada.Estado.FAILED: '#b42318',
    RegistroLlamada.Estado.BUSY: '#0b6bcb',
}

EXTENSIONES_OPERADORES = {
    '200': 'Operador 1',
}


def csv_value(row, *names):
    for name in names:
        if name in row:
            return (row.get(name) or '').strip()
    return ''


def csv_has_column(headers, *names):
    return any(name in headers for name in names)


def parse_int(value):
    try:
        return int(float(str(value or '0').strip()))
    except ValueError:
        return 0


def parse_datetime(value):
    value = str(value or '').strip()
    if not value:
        return None
    try:
        return timezone.make_aware(datetime.strptime(value, '%Y-%m-%d %H:%M:%S'))
    except ValueError:
        return None


def normalize_status(value):
    status = str(value or '').strip().upper()
    valid_statuses = {choice[0] for choice in RegistroLlamada.Estado.choices}
    return status if status in valid_statuses else ''


def parse_filter_int(request, name, minimum=None, maximum=None):
    value = request.GET.get(name, '').strip()
    if not value:
        return None
    try:
        value = int(value)
    except ValueError:
        return None
    if minimum is not None and value < minimum:
        return None
    if maximum is not None and value > maximum:
        return None
    return value


def format_seconds(seconds):
    seconds = int(seconds or 0)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f'{hours}h {minutes}m {seconds}s'
    if minutes:
        return f'{minutes}m {seconds}s'
    return f'{seconds}s'


def format_minutes(seconds):
    minutes = (int(seconds or 0) / 60)
    return f'{minutes:.1f} min'


def format_extension(value, only_operator=False):
    value = str(value or '').strip()
    if not value:
        return ''
    operador = EXTENSIONES_OPERADORES.get(value)
    if operador:
        if only_operator:
            return operador
        return f'{value} ({operador})'
    return value


class InformeLlamadaListView(LoginRequiredMixin, ListView):
    model = InformeLlamada
    context_object_name = 'informes'
    paginate_by = 15
    template_name = 'llamadas/informe_list.html'

    def get_queryset(self):
        queryset = super().get_queryset().select_related('creado_por')
        search = self.request.GET.get('q', '').strip()
        estado = self.request.GET.get('estado', '').strip()

        if search:
            queryset = queryset.filter(
                Q(motivo__icontains=search)
                | Q(descripcion__icontains=search)
                | Q(telefono__icontains=search)
                | Q(nombre_llamante__icontains=search)
            )

        if estado:
            queryset = queryset.filter(estado=estado)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['estados'] = InformeLlamada.Estado.choices
        context['q'] = self.request.GET.get('q', '')
        context['estado_actual'] = self.request.GET.get('estado', '')
        return context


class InformeLlamadaDetailView(LoginRequiredMixin, DetailView):
    model = InformeLlamada
    context_object_name = 'informe'
    template_name = 'llamadas/informe_detail.html'


class InformeLlamadaCreateView(LoginRequiredMixin, CreateView):
    model = InformeLlamada
    form_class = InformeLlamadaForm
    template_name = 'llamadas/informe_form.html'

    def form_valid(self, form):
        form.instance.creado_por = self.request.user
        return super().form_valid(form)


class InformeLlamadaUpdateView(LoginRequiredMixin, UpdateView):
    model = InformeLlamada
    form_class = InformeLlamadaForm
    template_name = 'llamadas/informe_form.html'
    success_url = reverse_lazy('llamadas:list')


class EstadisticasLlamadasView(LoginRequiredMixin, View):
    template_name = 'llamadas/estadisticas.html'

    def get(self, request):
        today = timezone.localdate()
        year = parse_filter_int(request, 'year', 1, 9999)
        month = parse_filter_int(request, 'month', 1, 12)
        day = parse_filter_int(request, 'day', 1, 31)
        if not year:
            year = today.year
        if not month:
            month = today.month

        queryset = RegistroLlamada.objects.all()
        if year:
            queryset = queryset.filter(inicio__year=year)
        if month:
            queryset = queryset.filter(inicio__month=month)
        if day:
            queryset = queryset.filter(inicio__day=day)

        total = queryset.count()
        agregados = queryset.aggregate(
            duracion_promedio=Avg('duracion_segundos'),
            conversacion_promedio=Avg('conversacion_segundos'),
        )

        conteos_por_estado = {
            row['estado']: row['total']
            for row in queryset.values('estado').annotate(total=Count('id'))
        }
        atendidas = conteos_por_estado.get(RegistroLlamada.Estado.ANSWERED, 0)
        no_atendidas = total - atendidas
        porcentaje_atendidas = round((atendidas / total) * 100, 1) if total else 0
        porcentaje_no_atendidas = round((no_atendidas / total) * 100, 1) if total else 0
        efectivas_si = queryset.filter(duracion_segundos__gt=120).count()
        efectivas_no = total - efectivas_si
        efectivas = [
            {'label': 'Si', 'count': efectivas_si, 'color': '#17633a'},
            {'label': 'No', 'count': efectivas_no, 'color': '#b42318'},
        ]
        estados = []
        for value, label in RegistroLlamada.Estado.choices:
            count = conteos_por_estado.get(value, 0)
            estados.append(
                {
                    'value': value,
                    'label': label,
                    'count': count,
                    'percent': round((count / total) * 100, 1) if total else 0,
                    'color': ESTADO_COLORES.get(value, '#0b6bcb'),
                }
            )

        counts_by_hour = {
            row['periodo']: row['total']
            for row in queryset.annotate(periodo=ExtractHour('inicio'))
            .values('periodo')
            .annotate(total=Count('id'))
        }
        serie = [
            {'label': f'{hour:02d}:00', 'total': counts_by_hour.get(hour, 0)}
            for hour in range(24)
        ]
        serie_titulo = 'Llamadas por hora'

        max_estado = max([estado['count'] for estado in estados] or [0])
        for estado in estados:
            estado['bar_height'] = int((estado['count'] / max_estado) * 100) if max_estado else 0
        max_efectiva = max([item['count'] for item in efectivas] or [0])
        for item in efectivas:
            item['bar_height'] = int((item['count'] / max_efectiva) * 100) if max_efectiva else 0

        max_serie = max([item['total'] for item in serie] or [0])
        for item in serie:
            item['bar_height'] = int((item['total'] / max_serie) * 100) if max_serie else 0
        line_points = ''
        line_area_points = ''
        chart_width = 720
        padding_x = 34
        top = 20
        bottom = 178
        plot_width = chart_width - (padding_x * 2)
        divisor = max(len(serie) - 1, 1)
        points = []
        for index, item in enumerate(serie):
            x = padding_x + (index * plot_width / divisor)
            y = bottom if not max_serie else bottom - ((item['total'] / max_serie) * (bottom - top))
            item['point_x'] = f'{x:.2f}'
            item['point_y'] = f'{y:.2f}'
            item['label_y'] = f'{max(y - 10, 12):.2f}'
            points.append(f'{item["point_x"]},{item["point_y"]}')
        line_points = ' '.join(points)
        line_area_points = f'{padding_x},{bottom} {line_points} {chart_width - padding_x},{bottom}' if points else ''

        years = (
            RegistroLlamada.objects.dates('inicio', 'year', order='DESC')
            if RegistroLlamada.objects.exists()
            else []
        )
        years = sorted({today.year, *[date.year for date in years]}, reverse=True)
        selected_month_days = range(1, 32)
        if year and month:
            selected_month_days = range(1, calendar.monthrange(year, month)[1] + 1)
        registros = []
        for registro in queryset.order_by('-inicio')[:100]:
            registros.append(
                {
                    'inicio': registro.inicio,
                    'numero_origen': format_extension(registro.numero_origen),
                    'numero_destino': format_extension(registro.numero_destino, only_operator=True),
                    'estado': registro.get_estado_display(),
                    'estado_color': ESTADO_COLORES.get(registro.estado, '#0b6bcb'),
                    'duracion': format_minutes(registro.duracion_segundos),
                    'conversacion': format_minutes(registro.conversacion_segundos),
                    'efectiva': 'Si' if registro.duracion_segundos > 120 else 'No',
                    'efectiva_color': '#17633a' if registro.duracion_segundos > 120 else '#b42318',
                }
            )

        return render(
            request,
            self.template_name,
            {
                'total': total,
                'estados': estados,
                'efectivas': efectivas,
                'serie': serie,
                'serie_titulo': serie_titulo,
                'line_points': line_points,
                'line_area_points': line_area_points,
                'years': years,
                'months': MESES,
                'days': selected_month_days,
                'selected_year': year,
                'selected_month': month,
                'selected_day': day,
                'porcentaje_atendidas': porcentaje_atendidas,
                'porcentaje_no_atendidas': porcentaje_no_atendidas,
                'duracion_promedio': format_seconds(agregados['duracion_promedio']),
                'conversacion_promedio': format_seconds(agregados['conversacion_promedio']),
                'registros': registros,
                'registros_mostrados': min(total, 100),
            },
        )


class ImportarLlamadasView(LoginRequiredMixin, UserPassesTestMixin, View):
    template_name = 'llamadas/importar.html'

    def test_func(self):
        return self.request.user.is_staff

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            messages.error(self.request, 'No tenes permiso para importar llamadas.')
            return redirect('home')
        return super().handle_no_permission()

    def get(self, request):
        return render(
            request,
            self.template_name,
            {
                'form': ImportarLlamadasForm(),
                'total_registros': RegistroLlamada.objects.count(),
            },
        )

    def post(self, request):
        form = ImportarLlamadasForm(request.POST, request.FILES)
        if not form.is_valid():
            return render(
                request,
                self.template_name,
                {
                    'form': form,
                    'total_registros': RegistroLlamada.objects.count(),
                },
            )

        archivo = TextIOWrapper(form.cleaned_data['archivo'].file, encoding='utf-8-sig')
        muestra = archivo.read(4096)
        archivo.seek(0)
        try:
            dialect = csv.Sniffer().sniff(muestra, delimiters=',;')
        except csv.Error:
            dialect = csv.excel
        reader = csv.DictReader(archivo, dialect=dialect)
        creados = 0
        duplicados = 0
        errores = []
        procesados = 0
        estadisticas = {
            'contestadas': 0,
            'no_contestadas': 0,
            'fallidas': 0,
            'ocupadas': 0,
        }
        columnas_requeridas = [
            ('Tiempo de inicio',),
            ('Estado de la llamada',),
            ('ID unico', 'ID único', 'ID Ãºnico'),
        ]
        headers = set(reader.fieldnames or [])

        if not headers:
            messages.error(request, 'El CSV esta vacio o no tiene encabezados.')
            return render(
                request,
                self.template_name,
                {
                    'form': ImportarLlamadasForm(),
                    'errores': ['No se encontraron encabezados en el archivo.'],
                    'total_registros': RegistroLlamada.objects.count(),
                },
            )

        faltantes = [
            ' / '.join(names)
            for names in columnas_requeridas
            if not csv_has_column(headers, *names)
        ]
        if faltantes:
            messages.error(request, 'El CSV no tiene todas las columnas necesarias.')
            return render(
                request,
                self.template_name,
                {
                    'form': ImportarLlamadasForm(),
                    'errores': [f'Falta la columna: {columna}.' for columna in faltantes],
                    'total_registros': RegistroLlamada.objects.count(),
                },
            )

        for numero_fila, row in enumerate(reader, start=2):
            procesados += 1
            status = normalize_status(csv_value(row, 'Estado de la llamada'))
            inicio = parse_datetime(csv_value(row, 'Tiempo de inicio'))
            id_unico = csv_value(row, 'ID unico', 'ID único')
            conversacion = parse_int(csv_value(row, 'Tiempo de Conversacion', 'Tiempo de Conversación'))

            if not id_unico:
                errores.append(f'Fila {numero_fila}: falta ID unico.')
                continue
            if not inicio:
                errores.append(f'Fila {numero_fila}: fecha de inicio invalida.')
                continue
            if not status:
                errores.append(f'Fila {numero_fila}: estado de llamada invalido.')
                continue

            _, created = RegistroLlamada.objects.get_or_create(
                id_unico=id_unico,
                defaults={
                    'numero_origen': csv_value(row, 'Numero de llamadas', 'Número de llamadas'),
                    'numero_destino': csv_value(row, 'Numero de destinatario'),
                    'nombre_llamante': csv_value(row, 'Nombre del llamante'),
                    'respondido_por': csv_value(row, 'Respondido Por'),
                    'linea_origen': csv_value(row, 'Nombre de origen de la troncal'),
                    'tipo_registro': csv_value(row, 'Campo de usuario de registro'),
                    'estado': status,
                    'inicio': inicio,
                    'respondida': parse_datetime(csv_value(row, 'Hora de respondida')),
                    'finalizacion': parse_datetime(csv_value(row, 'Hora de finalizacion', 'Hora de finalización')),
                    'duracion_segundos': parse_int(csv_value(row, 'Duracion de la llamada', 'Duración de la llamada')),
                    'conversacion_segundos': conversacion,
                },
            )

            if created:
                creados += 1
                if status == RegistroLlamada.Estado.ANSWERED:
                    estadisticas['contestadas'] += 1
                elif status == RegistroLlamada.Estado.NO_ANSWER:
                    estadisticas['no_contestadas'] += 1
                elif status == RegistroLlamada.Estado.FAILED:
                    estadisticas['fallidas'] += 1
                elif status == RegistroLlamada.Estado.BUSY:
                    estadisticas['ocupadas'] += 1
            else:
                duplicados += 1

        if creados:
            messages.success(request, f'Se importaron {creados} registros de llamadas.')
        if duplicados:
            messages.warning(request, f'Se omitieron {duplicados} registros duplicados.')
        if errores:
            messages.error(request, 'Algunas filas no se importaron.')

        return render(
            request,
            self.template_name,
            {
                'form': ImportarLlamadasForm(),
                'errores': errores[:100],
                'estadisticas': estadisticas,
                'procesados': procesados,
                'creados': creados,
                'duplicados': duplicados,
                'total_registros': RegistroLlamada.objects.count(),
            },
        )
