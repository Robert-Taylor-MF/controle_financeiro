from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('importar/', views.importar_fatura, name='importar_fatura'),
    path('cadastros/', views.central_cadastros, name='central_cadastros'),
    path('dividir/<int:transacao_id>/', views.ratear_transacao, name='ratear_transacao'),
    path('extrato/', views.extrato_faturas, name='extrato_faturas'),
    path('api/atualizar-responsavel/<int:transacao_id>/', views.atualizar_responsavel, name='atualizar_responsavel'),
    path('api/atualizar-categoria/<int:transacao_id>/', views.atualizar_categoria, name='atualizar_categoria'),
    path('sala-de-guerra/', views.sala_de_guerra, name='sala_de_guerra'),
]