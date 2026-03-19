from django import forms
from .models import CartaoCredito, Pessoa, Categoria, RendaMensal, Transacao, Instituicao, Cofre
        
class CartaoCreditoForm(forms.ModelForm):
    class Meta:
        model = CartaoCredito
        fields = ['nome', 'limite_total', 'dia_fechamento', 'dia_vencimento']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'w-full bg-slate-900 border border-slate-700 rounded p-2 text-slate-200'}),
            'limite_total': forms.NumberInput(attrs={'class': 'w-full bg-slate-900 border border-slate-700 rounded p-2 text-slate-200'}),
            'dia_fechamento': forms.NumberInput(attrs={'class': 'w-full bg-slate-900 border border-slate-700 rounded p-2 text-slate-200'}),
            'dia_vencimento': forms.NumberInput(attrs={'class': 'w-full bg-slate-900 border border-slate-700 rounded p-2 text-slate-200'}),
        }

class PessoaForm(forms.ModelForm):
    class Meta:
        model = Pessoa
        fields = ['nome', 'telefone', 'chave_pix', 'is_owner', 'foto_perfil']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'w-full bg-slate-900 border border-slate-700 rounded p-2 text-slate-200'}),
            'telefone': forms.TextInput(attrs={'class': 'w-full bg-slate-900 border border-slate-700 rounded p-2 text-slate-200'}),
            'chave_pix': forms.TextInput(attrs={'class': 'w-full bg-slate-900 border border-slate-700 rounded p-2 text-slate-200', 'placeholder': 'CPF, E-mail, Celular ou Aleatória...'}),
            'is_owner': forms.CheckboxInput(attrs={'class': 'w-5 h-5 text-red-600 bg-slate-900 border-slate-700 rounded focus:ring-red-500'}),
            'foto_perfil': forms.FileInput(attrs={
                'class': 'w-full bg-slate-900 border border-slate-700 rounded text-slate-400 cursor-pointer file:mr-4 file:py-2 file:px-4 file:rounded file:border-0 file:text-sm file:font-bold file:bg-emerald-900/50 file:text-emerald-400 hover:file:bg-emerald-800 transition-colors'
            }),
        }

class CategoriaForm(forms.ModelForm):
    class Meta:
        model = Categoria
        fields = ['nome', 'tipo_regra']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'w-full bg-slate-900 border border-slate-700 rounded p-2 text-slate-200'}),
            'tipo_regra': forms.Select(attrs={'class': 'w-full bg-slate-900 border border-slate-700 rounded p-2 text-slate-200'}),
        }

class RendaMensalForm(forms.ModelForm):
    class Meta:
        model = RendaMensal
        fields = ['pessoa', 'mes', 'ano', 'valor_liquido']
        widgets = {
            'pessoa': forms.Select(attrs={'class': 'w-full bg-slate-900 border border-slate-700 rounded p-2 text-slate-200'}),
            'mes': forms.NumberInput(attrs={'class': 'w-full bg-slate-900 border border-slate-700 rounded p-2 text-slate-200', 'placeholder': 'Ex: 3'}),
            'ano': forms.NumberInput(attrs={'class': 'w-full bg-slate-900 border border-slate-700 rounded p-2 text-slate-200', 'placeholder': 'Ex: 2026'}),
            'valor_liquido': forms.NumberInput(attrs={'class': 'w-full bg-slate-900 border border-slate-700 rounded p-2 text-slate-200', 'step': '0.01'}),
        }
        
class DespesaAvulsaForm(forms.ModelForm):
    class Meta:
        model = Transacao
        fields = ['descricao', 'valor', 'data_compra', 'categoria', 'responsavel', 'cartao', 'mes_fatura', 'ano_fatura']
        widgets = {
            'descricao': forms.TextInput(attrs={'class': 'w-full bg-slate-900 border border-slate-700 rounded p-2 text-slate-200', 'placeholder': 'Ex: Conta de Luz, Internet...'}),
            'valor': forms.NumberInput(attrs={'class': 'w-full bg-slate-900 border border-slate-700 rounded p-2 text-slate-200', 'step': '0.01'}),
            'data_compra': forms.DateInput(attrs={'class': 'w-full bg-slate-900 border border-slate-700 rounded p-2 text-slate-200', 'type': 'date'}),
            'categoria': forms.Select(attrs={'class': 'w-full bg-slate-900 border border-slate-700 rounded p-2 text-slate-200'}),
            'responsavel': forms.Select(attrs={'class': 'w-full bg-slate-900 border border-slate-700 rounded p-2 text-slate-200'}),
            'cartao': forms.Select(attrs={'class': 'w-full bg-slate-900 border border-slate-700 rounded p-2 text-slate-200'}),
            'mes_fatura': forms.NumberInput(attrs={'class': 'w-full bg-slate-900 border border-slate-700 rounded p-2 text-slate-200'}),
            'ano_fatura': forms.NumberInput(attrs={'class': 'w-full bg-slate-900 border border-slate-700 rounded p-2 text-slate-200'}),
        }
        
class InstituicaoForm(forms.ModelForm):
    class Meta:
        model = Instituicao
        fields = ['nome']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'w-full bg-slate-900 border border-slate-700 rounded p-2 text-slate-200', 'placeholder': 'Ex: PicPay, Nubank, Digio...'}),
        }

class CofreForm(forms.ModelForm):
    class Meta:
        model = Cofre
        fields = ['nome', 'meta_valor', 'saldo_atual', 'instituicao']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'w-full bg-slate-900 border border-slate-700 rounded p-2 text-slate-200', 'placeholder': 'Ex: Reserva de Emergência'}),
            'meta_valor': forms.NumberInput(attrs={'class': 'w-full bg-slate-900 border border-slate-700 rounded p-2 text-slate-200', 'step': '0.01'}),
            'saldo_atual': forms.NumberInput(attrs={'class': 'w-full bg-slate-900 border border-slate-700 rounded p-2 text-slate-200', 'step': '0.01'}),
            'instituicao': forms.Select(attrs={'class': 'w-full bg-slate-900 border border-slate-700 rounded p-2 text-slate-200'}),
        }