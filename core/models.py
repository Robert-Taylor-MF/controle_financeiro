from django.db import models
from decimal import Decimal

class Pessoa(models.Model):
    nome = models.CharField(max_length=100)
    telefone = models.CharField(max_length=20, blank=True, null=True)
    is_owner = models.BooleanField(default=False)
    chave_pix = models.CharField(max_length=150, blank=True, null=True)
    level = models.IntegerField(default=1)
    xp_atual = models.IntegerField(default=0)
    
    # ANTI-EXPLOIT: Lembra qual foi o último mês que o jogador derrotou o Boss
    ultimo_mes_fechado = models.CharField(max_length=7, blank=True, null=True) # Ex: '03/2026'
    
    # HISTÓRICO ANTI-FARM: Lembra todos os meses batidos separados por vírgula
    meses_fechados = models.TextField(blank=True, null=True, default="")
    
    # O CAMPO RESGATADO DA FORJA ANTIGA
    ativo = models.BooleanField(default=True)
    
    # ==========================================
    # SISTEMA DE RPG (GAMIFICAÇÃO)
    # ==========================================
    foto_perfil = models.ImageField(upload_to='avatares/', blank=True, null=True)
    level = models.IntegerField(default=1)
    xp_atual = models.IntegerField(default=0)

    # O seu "Hunter Rank" muda conforme o seu level
    def get_titulo(self):
        if self.level <= 5: return "Camponês Endividado"
        elif self.level <= 10: return "Escudeiro de Cobre"
        elif self.level <= 20: return "Caçador de Recompensas"
        elif self.level <= 40: return "Cavaleiro de Prata"
        elif self.level <= 60: return "Mestre da Forja"
        elif self.level < 100: return "Lorde do Tesouro"
        else: return "Dragão Ancião"

    # Quanto de XP falta para upar de nível? (Ex: Nível 1 precisa de 100xp, Nível 2 de 200xp...)
    def xp_para_proximo_level(self):
        return self.level * 100

    # Calcula a % da barra de energia verde que vai ficar embaixo da sua foto
    def progresso_xp(self):
        teto = self.xp_para_proximo_level()
        pct = (self.xp_atual / teto) * 100
        return min(int(pct), 100)

    def ganhar_xp(self, quantidade):
        self.xp_atual += quantidade
        subiu_de_nivel = False
        
        # Um laço de repetição (while) caso você ganhe MUITA XP de uma vez e suba 2 níveis seguidos
        while self.xp_atual >= self.xp_para_proximo_level():
            self.xp_atual -= self.xp_para_proximo_level() # Deduz a XP gasta para upar
            self.level += 1 # LEVEL UP!
            subiu_de_nivel = True
            
        self.save()
        return subiu_de_nivel

    def __str__(self):
        return self.nome

class CartaoCredito(models.Model):
    """
    Seu arsenal de cartões. As datas são cruciais para o algoritmo de fechamento.
    """
    nome = models.CharField(max_length=50, help_text="Ex: Nubank, Itaú Black")
    limite_total = models.DecimalField(max_digits=10, decimal_places=2)
    dia_fechamento = models.IntegerField(help_text="Dia em que a fatura vira")
    dia_vencimento = models.IntegerField(help_text="Dia de pagar o boleto")
    
    def __str__(self):
        return self.nome

class Categoria(models.Model):
    """
    Estrutura que vai sustentar a regra 50/30/20 futuramente.
    """
    TIPO_CHOICES = [
        ('ESSENCIAL', 'Necessidade (50%)'),
        ('ESTILO_VIDA', 'Desejo/Emoção (30%)'),
        ('FUTURO', 'Investimento/Reserva (20%)'),
    ]
    
    nome = models.CharField(max_length=50)
    tipo_regra = models.CharField(max_length=20, choices=TIPO_CHOICES)
    
    # Deixaremos o limite em branco por enquanto, conforme combinamos.
    orcamento_sugerido = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )

    def __str__(self):
        return f"{self.nome} - {self.get_tipo_regra_display()}"

class Transacao(models.Model):
    """
    Onde a mágica acontece e o volume de dados se concentra.
    """
    STATUS_CHOICES = [
        ('PENDENTE', 'Pendente (Na fatura aberta)'),
        ('FATURADO', 'Faturado (Fatura fechada)'),
        ('PAGO', 'Pago/Quitado'),
    ]

    descricao = models.CharField(max_length=255, help_text="Nome que vem na fatura")
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    data_compra = models.DateField()
    mes_fatura = models.IntegerField(help_text="Mês de competência da fatura", default=1)
    ano_fatura = models.IntegerField(help_text="Ano de competência da fatura", default=2026)
    
    # Relacionamentos (Foreign Keys)
    responsavel = models.ForeignKey(
        Pessoa, on_delete=models.PROTECT, related_name='transacoes', null=True, blank=True
    )
    cartao = models.ForeignKey(
        CartaoCredito, on_delete=models.PROTECT, related_name='transacoes', null=True, blank=True
    )
    categoria = models.ForeignKey(
        Categoria, on_delete=models.SET_NULL, null=True, blank=True, related_name='transacoes'
    )
    
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='PENDENTE')
    
    # Campo para controle de parcelamento (opcional, mas muito útil)
    parcela_atual = models.IntegerField(default=1)
    total_parcelas = models.IntegerField(default=1)

    def __str__(self):
        return f"{self.data_compra} - {self.descricao} - R$ {self.valor}"
    
class RendaMensal(models.Model):
    """
    Armazena o salário líquido variável para cada competência (Mês/Ano).
    O motor do sistema usará isso para calcular a regra 50/30/20.
    """
    pessoa = models.ForeignKey(Pessoa, on_delete=models.CASCADE)
    mes = models.IntegerField()
    ano = models.IntegerField()
    valor_liquido = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        # Garante que você não cadastre dois salários para o mesmo mês sem querer
        unique_together = ('pessoa', 'mes', 'ano')

    def __str__(self):
        return f"Renda de {self.pessoa.nome} - {self.mes}/{self.ano}: R$ {self.valor_liquido}"
    
# ==========================================
# BANCO DA GUILDA (WEALTH MANAGEMENT)
# ==========================================

class Instituicao(models.Model):
    nome = models.CharField(max_length=100) # Ex: PicPay, Nubank, Bradesco
    
    def __str__(self):
        return self.nome

class Cofre(models.Model):
    nome = models.CharField(max_length=100) # Ex: Reserva de Emergência, PC Novo
    meta_valor = models.DecimalField(max_digits=10, decimal_places=2, help_text="O valor total (Boss) que você quer atingir")
    saldo_atual = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, help_text="Ouro guardado até o momento")
    instituicao = models.ForeignKey(Instituicao, on_delete=models.CASCADE)
    
    # Esta função calcula automaticamente a % de conclusão da sua meta!
    def progresso(self):
        if self.meta_valor > 0:
            pct = (self.saldo_atual / self.meta_valor) * 100
            return min(int(pct), 100) # Trava em 100% para a barra de XP não vazar da tela
        return 0

    # Esta função calcula quanto falta para vencer a missão
    def falta_para_meta(self):
        faltante = self.meta_valor - self.saldo_atual
        return faltante if faltante > 0 else 0

    def __str__(self):
        return self.nome
    
class HistoricoCofre(models.Model):
    TIPO_CHOICES = [
        ('entrada', 'Depósito (Loot)'),
        ('saida', 'Saque (Resgate)'),
        ('reposicao', 'Reposição de Dívida')
    ]
    
    MOTIVO_CHOICES = [
        ('pessoal', 'Gasto Pessoal / Lazer'),
        ('saude', 'Saúde / Farmácia'),
        ('casa', 'Despesas da Casa / Manutenção'),
        ('emergencia', 'Emergência Imprevista'),
        ('objetivo', 'Objetivo Concluído! (GG)'),
        ('outro', 'Outros Motivos')
    ]

    cofre = models.ForeignKey(Cofre, on_delete=models.CASCADE)
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    data = models.DateTimeField(auto_now_add=True) # Salva a data e hora automaticamente
    motivo = models.CharField(max_length=20, choices=MOTIVO_CHOICES, blank=True, null=True)

    def __str__(self):
        return f"{self.cofre.nome} | {self.get_tipo_display()} | R$ {self.valor}"

from django.contrib.auth.models import User
class MestreSeguranca(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='seguranca')
    pergunta_secreta = models.CharField(max_length=200)
    resposta_secreta = models.CharField(max_length=200)
    gemini_api_key = models.CharField(max_length=255, blank=True, null=True, help_text="Chave da IA para extrair PDFs")

    def __str__(self):
        return f"Segurança do Mestre: {self.user.username}"