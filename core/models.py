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
    
    # TUTORIAL: Se o usuário já viu o guia de introdução
    tutorial_visto = models.BooleanField(default=False)
    
    # O CAMPO RESGATADO DA FORJA ANTIGA
    ativo = models.BooleanField(default=True)
    
    # GAMIFICAÇÃO 2.0 (HP e Classes)
    orcamento_mensal = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, help_text="HP Base do Mês (Para Owner)")
    classe_atual = models.CharField(max_length=50, default="Aventureiro")
    
    # ==========================================
    # SISTEMA DE RPG (GAMIFICAÇÃO)
    # ==========================================
    foto_perfil = models.ImageField(upload_to='avatares/', blank=True, null=True)
    level = models.IntegerField(default=1)
    xp_atual = models.IntegerField(default=0)

    # ==========================================
    # RANKS DO HERÓI TITULAR (Owner)
    # ==========================================
    def get_titulo_owner(self):
        if self.level <= 5: return "Camponês Endividado"
        elif self.level <= 10: return "Escudeiro de Cobre"
        elif self.level <= 20: return "Caçador de Recompensas"
        elif self.level <= 40: return "Cavaleiro de Prata"
        elif self.level <= 60: return "Mestre da Forja"
        elif self.level < 100: return "Lorde do Tesouro"
        else: return "Dragão Ancião"

    # ==========================================
    # RANKS DA PARTY (Quem usa o cartão alheio)
    # Títulos remetem a "quem gasta muito"
    # ==========================================
    def get_titulo_party(self):
        if self.level <= 5: return "Novato Poupador"
        elif self.level <= 10: return "Gastador Casual"
        elif self.level <= 20: return "Faz-me-Rir no Caixa"
        elif self.level <= 40: return "Devorador de Limite"
        elif self.level <= 60: return "Rei do Parcelamento"
        elif self.level < 100: return "Destruidor de Faturas"
        else: return "Lenda do Gasto Infinito"

    # Retorna o título correto baseado no tipo de pessoa
    def get_titulo(self):
        if self.is_owner:
            return self.get_titulo_owner()
        return self.get_titulo_party()

    # Quanto de XP falta para upar de nível?
    # Owner: level * 100 | Party: level * 150 (mais lento)
    def xp_para_proximo_level(self):
        if self.is_owner:
            return self.level * 100
        return self.level * 150

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

    def atualizar_xp_por_gasto(self, total_gasto):
        """
        Recalcula o XP do membro da Party baseado no total histórico de gastos.
        Regra: 10 XP por R$ 100 gastos (1 XP por R$ 10).
        """
        if self.is_owner:
            return  # Owner tem seu próprio sistema de XP

        xp_merecido = int(float(total_gasto) / 10)  # 10 XP por R$100 = 1 XP por R$10
        
        # Reseta e recalcula do zero para evitar inconsistências
        self.level = 1
        self.xp_atual = 0
        
        if xp_merecido > 0:
            self.xp_atual = xp_merecido
            while self.xp_atual >= self.xp_para_proximo_level():
                self.xp_atual -= self.xp_para_proximo_level()
                self.level += 1
        
        self.save()

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

class DespesaRecorrente(models.Model):
    """
    Contas fixas mensais (Luz, Água, Internet) que são injetadas automaticamente no mês.
    """
    descricao = models.CharField(max_length=255, help_text="Ex: Conta de Luz")
    valor_estimado = models.DecimalField(max_digits=10, decimal_places=2, help_text="Valor aproximado ou fixo da conta")
    dia_vencimento = models.IntegerField(help_text="Dia de vencimento (1 a 31)", default=10)
    categoria = models.ForeignKey(Categoria, on_delete=models.SET_NULL, null=True)
    cartao = models.ForeignKey(CartaoCredito, on_delete=models.SET_NULL, null=True, blank=True, help_text="Opcional. Deixe em branco se for Pix/Boleto.")
    
    def __str__(self):
        return f"{self.descricao} (Dia {self.dia_vencimento})"

class RegistroRecorrencia(models.Model):
    """
    Controla se as contas fixas de um determinado mês já foram injetadas para evitar duplicidade.
    """
    mes = models.IntegerField()
    ano = models.IntegerField()
    data_geracao = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('mes', 'ano')

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
        
    @property
    def valor_real_owner(self):
        # Calcula quanto sobrou para o dono principal pagar aps os rateios
        total_rateio = sum(r.valor for r in self.rateios.all())
        return self.valor - total_rateio
    
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
from cryptography.fernet import Fernet
from django.conf import settings
import base64

def get_fernet():
    key = base64.urlsafe_b64encode(settings.SECRET_KEY.encode()[:32].ljust(32, b'X'))
    return Fernet(key)

class MestreSeguranca(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='seguranca')
    pergunta_secreta = models.CharField(max_length=200)
    resposta_secreta = models.CharField(max_length=500) 
    
    # Configurações de IA
    gemini_api_key = models.CharField(max_length=500, blank=True, null=True, help_text="Chave da IA para extrair PDFs")
    groq_api_key = models.CharField(max_length=500, blank=True, null=True, help_text="Chave da IA Groq (Llama)")
    ai_default = models.CharField(max_length=20, default='GEMINI', choices=[('GEMINI', 'Gemini (Google)'), ('GROQ', 'Groq (Llama)')])
    
    def set_api_key(self, raw_key):
        if raw_key: self.gemini_api_key = get_fernet().encrypt(raw_key.encode('utf-8')).decode('utf-8')
        else: self.gemini_api_key = None

    def get_api_key(self):
        if self.gemini_api_key:
            try: return get_fernet().decrypt(self.gemini_api_key.encode('utf-8')).decode('utf-8')
            except: return self.gemini_api_key # Fallback for old unencrypted
        return None

    def set_groq_key(self, raw_key):
        if raw_key: self.groq_api_key = get_fernet().encrypt(raw_key.encode('utf-8')).decode('utf-8')
        else: self.groq_api_key = None

    def get_groq_key(self):
        if self.groq_api_key:
            try: return get_fernet().decrypt(self.groq_api_key.encode('utf-8')).decode('utf-8')
            except: return self.groq_api_key
        return None

    def set_resposta(self, resp):
        if resp: self.resposta_secreta = get_fernet().encrypt(resp.lower().strip().encode('utf-8')).decode('utf-8')
        else: self.resposta_secreta = ""

    def get_resposta(self):
        if self.resposta_secreta:
            try: return get_fernet().decrypt(self.resposta_secreta.encode('utf-8')).decode('utf-8')
            except: return self.resposta_secreta.lower().strip() # Fallback
        return ""
    
    # Cofre do Tempo (Backup Configuration)
    diretorio_backup = models.CharField(max_length=500, blank=True, null=True, help_text="Caminho do HD ou Google Drive")
    frequencia_backup = models.CharField(max_length=20, default='MANUAL')
    horario_backup = models.TimeField(null=True, blank=True)
    dias_backup = models.CharField(max_length=50, blank=True, null=True, help_text="0,1,2,3,4,5,6")

    def __str__(self):
        return f"Segurança do Mestre: {self.user.username}"


# ==========================================
# GAMIFICAÇÃO 2.0 (Missões e Rateios)
# ==========================================

class Rateio(models.Model):
    """
    Controla como uma única transação é dividida entre membros da party.
    Isso substitui o sistema antigo de duplicar a Transacao.
    """
    transacao = models.ForeignKey(Transacao, on_delete=models.CASCADE, related_name='rateios')
    pessoa = models.ForeignKey(Pessoa, on_delete=models.CASCADE, related_name='rateios')
    valor = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.pessoa.nome} - R$ {self.valor} ({self.transacao.descricao})"

class Quest(models.Model):
    """
    Missão de economia. O mestre cria a missão (ex: Gasto máximo no IFood de R$ 500).
    """
    titulo = models.CharField(max_length=200, help_text="Ex: Cortar o Ifood")
    descricao = models.TextField(blank=True, null=True)
    meta_valor = models.DecimalField(max_digits=10, decimal_places=2, help_text="Limite de gastos (HP do Boss)")
    categoria_alvo = models.ForeignKey(Categoria, on_delete=models.CASCADE, null=True, blank=True)
    recompensa_xp = models.IntegerField(default=500, help_text="XP para a Party se vencer o boss")
    
    # Para qual mês essa missão vale?
    mes_vigencia = models.IntegerField()
    ano_vigencia = models.IntegerField()

    def __str__(self):
        return f"{self.titulo} - Limite: R$ {self.meta_valor}"

class QuestStatus(models.Model):
    """
    Controla o estado final de uma missão (Vencida, Perdida, Pendente)
    """
    STATUS_CHOICES = [
        ('PENDENTE', 'Em combate (Pendente)'),
        ('VENCIDA', 'Vitória! Boss derrotado'),
        ('PERDIDA', 'Derrota! Party aniquilada'),
    ]
    quest = models.OneToOneField(Quest, on_delete=models.CASCADE, related_name='status')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDENTE')
    valor_gasto_total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def __str__(self):
        return f"{self.quest.titulo} - {self.get_status_display()}"