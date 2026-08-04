from django.contrib import admin
from .models import Pessoa, CartaoCredito, Categoria, Transacao

@admin.register(Pessoa)
class PessoaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'is_owner', 'ativo')
    list_filter = ('is_owner', 'ativo')

@admin.register(CartaoCredito)
class CartaoCreditoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'limite_total', 'dia_fechamento', 'dia_vencimento')

@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'get_tipo_regra_display', 'orcamento_sugerido')
    list_filter = ('tipo_regra',)

@admin.register(Transacao)
class TransacaoAdmin(admin.ModelAdmin):
    list_display = ('data_compra', 'descricao', 'valor', 'responsavel', 'cartao', 'status','mes_fatura', 'ano_fatura')
    list_filter = ('status', 'cartao', 'responsavel', 'categoria')
    search_fields = ('descricao',)
    date_hierarchy = 'data_compra' # Cria uma linha do tempo navegável no topo do admin