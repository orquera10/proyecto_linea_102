from datetime import datetime

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import InformeLlamada, RegistroLlamada


class InformeLlamadaTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='operador',
            password='ClaveSegura123',
        )

    def test_create_requires_login(self):
        response = self.client.get(reverse('llamadas:create'))

        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response['Location'])

    def test_user_can_create_informe(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse('llamadas:create'),
            {
                'fecha': '2026-06-19',
                'hora': '10:30',
                'telefono': '123456',
                'nombre_llamante': 'Maria',
                'tipo': InformeLlamada.TipoLlamada.CONSULTA,
                'motivo': 'Consulta inicial',
                'descripcion': 'Descripcion de la llamada',
                'intervencion': 'Se orienta a la persona',
                'estado': InformeLlamada.Estado.ABIERTA,
                'requiere_seguimiento': 'on',
                'fecha_seguimiento': '2026-06-20',
            },
        )

        informe = InformeLlamada.objects.get()
        self.assertRedirects(response, informe.get_absolute_url())
        self.assertEqual(informe.creado_por, self.user)

    def test_import_button_only_staff_home(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('home'))

        self.assertNotContains(response, 'Importar CSV')

        self.user.is_staff = True
        self.user.save()
        response = self.client.get(reverse('home'))

        self.assertContains(response, 'Importar CSV')

    def test_non_staff_cannot_access_import_screen(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse('llamadas:import'))

        self.assertRedirects(response, reverse('home'))

    def test_staff_can_import_only_new_cdr_records(self):
        self.user.is_staff = True
        self.user.save()
        self.client.force_login(self.user)
        csv_data = (
            'Numero de llamadas,Numero de destinatario,Tiempo de inicio,Hora de respondida,'
            'Hora de finalizacion,Duracion de la llamada,Tiempo de Conversacion,'
            'Estado de la llamada,ID unico,Campo de usuario de registro,Nombre de origen de la troncal\n'
            '123,200,2026-06-19 10:00:00,2026-06-19 10:00:05,2026-06-19 10:01:00,60,55,ANSWERED,abc-1,Inbound,Linea1\n'
            '456,200,2026-06-19 11:00:00,2026-06-19 11:00:00,2026-06-19 11:00:10,10,0,NO ANSWER,abc-2,Inbound,Linea1\n'
        )
        upload = SimpleUploadedFile('cdr.csv', csv_data.encode('utf-8'), content_type='text/csv')

        response = self.client.post(
            reverse('llamadas:import'),
            {'archivo': upload},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(RegistroLlamada.objects.count(), 2)
        self.assertContains(response, '<td>1</td>', html=True)

        duplicate_upload = SimpleUploadedFile('cdr.csv', csv_data.encode('utf-8'), content_type='text/csv')
        response = self.client.post(
            reverse('llamadas:import'),
            {'archivo': duplicate_upload},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(RegistroLlamada.objects.count(), 2)
        self.assertContains(response, 'Duplicados omitidos')

    def test_staff_can_import_semicolon_csv(self):
        self.user.is_staff = True
        self.user.save()
        self.client.force_login(self.user)
        csv_data = (
            'Numero de llamadas;Numero de destinatario;Tiempo de inicio;Hora de respondida;'
            'Hora de finalizacion;Duracion de la llamada;Tiempo de Conversacion;'
            'Estado de la llamada;ID unico;Campo de usuario de registro;Nombre de origen de la troncal\n'
            '123;200;2026-06-19 10:00:00;2026-06-19 10:00:05;2026-06-19 10:01:00;60;55;ANSWERED;abc-3;Inbound;Linea1\n'
        )
        upload = SimpleUploadedFile('cdr.csv', csv_data.encode('utf-8'), content_type='text/csv')

        response = self.client.post(
            reverse('llamadas:import'),
            {'archivo': upload},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(RegistroLlamada.objects.count(), 1)
        self.assertContains(response, 'Filas procesadas')

    def test_stats_view_requires_login(self):
        response = self.client.get(reverse('llamadas:stats'))

        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response['Location'])

    def test_stats_view_shows_imported_call_metrics_and_filters(self):
        self.client.force_login(self.user)
        RegistroLlamada.objects.create(
            id_unico='stats-1',
            numero_origen='123',
            numero_destino='200',
            linea_origen='Linea 1',
            estado=RegistroLlamada.Estado.ANSWERED,
            inicio=timezone.make_aware(datetime(2026, 6, 19, 10, 0, 0)),
            duracion_segundos=121,
            conversacion_segundos=45,
        )
        RegistroLlamada.objects.create(
            id_unico='stats-2',
            estado=RegistroLlamada.Estado.NO_ANSWER,
            inicio=timezone.make_aware(datetime(2026, 6, 20, 11, 0, 0)),
            duracion_segundos=10,
            conversacion_segundos=0,
        )

        response = self.client.get(reverse('llamadas:stats'), {'year': 2026, 'month': 6, 'day': 19})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Estadisticas de llamadas')
        self.assertContains(response, 'filter-bar')
        self.assertNotContains(response, '>Volver</a>')
        self.assertContains(response, 'Total de llamadas')
        self.assertContains(response, 'Contestada')
        self.assertContains(response, 'Llamadas por hora')
        self.assertContains(response, '<polyline class="line-chart-line"')
        self.assertContains(response, 'Llamadas por tipo')
        self.assertContains(response, 'Llamadas atendidas')
        self.assertContains(response, 'Llamadas no atendidas')
        self.assertContains(response, 'Llamadas efectivas (mayores a 2min)')
        self.assertNotContains(response, 'Duracion total')
        self.assertNotContains(response, 'Conversacion total')
        self.assertContains(response, 'Registros de llamadas')
        self.assertContains(response, '123')
        self.assertContains(response, 'Operador 1')
        self.assertNotContains(response, '200 (Operador 1)')
        self.assertContains(response, 'Efectiva')
        self.assertContains(response, 'Si')
        self.assertNotContains(response, '<th>Linea</th>', html=True)
        self.assertContains(response, '2.0 min')
        self.assertContains(response, '0.8 min')
        self.assertContains(response, 'background: #17633a;')
        self.assertContains(response, '>1</strong>', html=False)

    def test_stats_view_defaults_to_current_month(self):
        self.client.force_login(self.user)
        today = timezone.localdate()
        RegistroLlamada.objects.create(
            id_unico='stats-current',
            estado=RegistroLlamada.Estado.ANSWERED,
            inicio=timezone.make_aware(datetime(today.year, today.month, 1, 10, 0, 0)),
            duracion_segundos=60,
            conversacion_segundos=45,
        )
        RegistroLlamada.objects.create(
            id_unico='stats-old',
            estado=RegistroLlamada.Estado.ANSWERED,
            inicio=timezone.make_aware(datetime(2020, 1, 1, 10, 0, 0)),
            duracion_segundos=60,
            conversacion_segundos=45,
        )

        response = self.client.get(reverse('llamadas:stats'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<strong>1</strong>', html=True)
        self.assertContains(response, f'<option value="{today.year}" selected>{today.year}</option>', html=True)
        self.assertContains(response, f'<option value="{today.month}" selected>')

    def test_stats_view_empty_filters_default_to_current_month_all_days(self):
        self.client.force_login(self.user)
        today = timezone.localdate()

        response = self.client.get(reverse('llamadas:stats'), {'year': '', 'month': '', 'day': ''})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'<option value="{today.year}" selected>{today.year}</option>', html=True)
        self.assertContains(response, f'<option value="{today.month}" selected>')
        self.assertContains(response, '<option value="" selected>Todos</option>', html=True)

# Create your tests here.
