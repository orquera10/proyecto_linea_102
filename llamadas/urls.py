from django.urls import path

from . import views


app_name = 'llamadas'

urlpatterns = [
    path('', views.InformeLlamadaListView.as_view(), name='list'),
    path('nuevo/', views.InformeLlamadaCreateView.as_view(), name='create'),
    path('importar/', views.ImportarLlamadasView.as_view(), name='import'),
    path('estadisticas/', views.EstadisticasLlamadasView.as_view(), name='stats'),
    path('<int:pk>/', views.InformeLlamadaDetailView.as_view(), name='detail'),
    path('<int:pk>/editar/', views.InformeLlamadaUpdateView.as_view(), name='update'),
]
