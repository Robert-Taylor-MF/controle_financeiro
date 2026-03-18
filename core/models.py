from django.db import models
from decimal import Decimal

class Pessoa(models.Model):
    """
    Representa você e os amigos para quem você empresta o cartão.
    """
    nome = models.CharField(max_length=100)
    telefone = models.CharField(max_length=20, blank=True, null=True)
    is_owner = models.BooleanField(
        default=False, 
        help_text="Marque True apenas para o seu perfil. False para os amigos."
    )
    ativo = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.nome} ({'Titular' if self.is_owner else 'Terceiro'})"

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