from decimal import Decimal
from django.db.models import Sum, Q
from core.models import Pessoa, Rateio, Transacao, Quest, QuestStatus

def atualizar_status_quests(mes, ano):
    """
    Verifica o progresso das missões do mês e atualiza o status.
    """
    quests = Quest.objects.filter(mes_vigencia=mes, ano_vigencia=ano)
    
    for quest in quests:
        status_obj, created = QuestStatus.objects.get_or_create(quest=quest)
        
        # Filtra transações. Se a quest tem categoria, filtra por ela
        # Pega todas as transações que pertencem ao dono ou aos rateios
        # Para simplificar, pegamos o total gasto na categoria (se houver) 
        # ou o total geral (se a quest não tiver categoria)
        
        q_transacoes = Transacao.objects.filter(mes_fatura=mes, ano_fatura=ano)
        if quest.categoria_alvo:
            q_transacoes = q_transacoes.filter(categoria=quest.categoria_alvo)
            
        total_gasto = q_transacoes.aggregate(Sum('valor'))['valor__sum'] or Decimal('0.00')
        status_obj.valor_gasto_total = total_gasto
        
        if total_gasto >= quest.meta_valor:
            status_obj.status = 'PERDIDA'
        else:
            status_obj.status = 'PENDENTE'
            # Só ganha de verdade se o mês virar e ele não estourou, mas podemos deixar pendente
        
        status_obj.save()

def get_hp_party(mes, ano):
    """
    Calcula o HP (Vida) da party baseado no orçamento mensal do Owner 
    vs o total gasto no mês.
    """
    owner = Pessoa.objects.filter(is_owner=True).first()
    orcamento = owner.orcamento_mensal if owner and owner.orcamento_mensal else Decimal('0.00')
    
    # Se não tem orçamento, o HP é sempre 100% (Modo passivo)
    if orcamento <= 0:
        return {'hp_atual': 100, 'hp_maximo': 100, 'hp_pct': 100, 'gasto_total': 0, 'status': 'SEGURO'}
        
    # Gasto total = (Total das transações do Dono e Sem Dono) - (Total dos Rateios dos Aliados)
    # 1. Soma transações cujo responsável é o Dono ou Ninguém
    todas_transacoes = Transacao.objects.filter(mes_fatura=mes, ano_fatura=ano)
    gasto_bruto = todas_transacoes.filter(Q(responsavel=owner) | Q(responsavel__isnull=True)).aggregate(Sum('valor'))['valor__sum'] or Decimal('0.00')
    
    # 2. Subtrai os Rateios (o que os Aliados vão pagar dessas transações)
    total_rateios_aliados = Rateio.objects.filter(transacao__mes_fatura=mes, transacao__ano_fatura=ano).exclude(pessoa=owner).aggregate(Sum('valor'))['valor__sum'] or Decimal('0.00')
    
    gasto_total = max(Decimal('0.00'), gasto_bruto - total_rateios_aliados)
    
    hp_atual = max(orcamento - gasto_total, Decimal('0.00'))
    
    pct = (hp_atual / orcamento) * 100
    
    status = 'SEGURO'
    if pct <= 10:
        status = 'PERIGO'
    elif pct <= 30:
        status = 'ALERTA'
        
    return {
        'hp_atual': hp_atual,
        'hp_maximo': orcamento,
        'hp_pct': min(int(pct), 100),
        'gasto_total': gasto_total,
        'status': status
    }

def atualizar_classes_dinamicas(mes, ano):
    """
    Calcula a classe de personagem para todos os membros baseado no tipo de gasto do mês.
    Regras divertidas de exemplo:
    - Maioria em Alimentação (Essencial/Ifood) -> Bardo Boêmio
    - Maioria em Estilo de Vida -> Artífice
    - Mais de 50% em Futuro -> Paladino da Poupança
    - Se gastou muito pouco -> Monge do Silêncio
    """
    pessoas = Pessoa.objects.filter(ativo=True)
    
    for pessoa in pessoas:
        # Acha os rateios da pessoa no mes
        rateios = Rateio.objects.filter(pessoa=pessoa, transacao__mes_fatura=mes, transacao__ano_fatura=ano)
        
        # Agrupa os gastos da pessoa por tipo de categoria
        gastos = {
            'ESSENCIAL': Decimal('0.00'),
            'ESTILO_VIDA': Decimal('0.00'),
            'FUTURO': Decimal('0.00'),
            'SEM_CATEGORIA': Decimal('0.00')
        }
        
        total_pessoa = Decimal('0.00')
        
        for r in rateios:
            cat = r.transacao.categoria
            tipo = cat.tipo_regra if cat else 'SEM_CATEGORIA'
            gastos[tipo] = gastos.get(tipo, Decimal('0.00')) + r.valor
            total_pessoa += r.valor
            
        nova_classe = "Aventureiro" # Classe base
        
        if total_pessoa > 0:
            if gastos['FUTURO'] >= (total_pessoa * Decimal('0.40')):
                nova_classe = "Paladino da Poupança"
            elif gastos['ESTILO_VIDA'] >= (total_pessoa * Decimal('0.50')):
                nova_classe = "Mago Ostentação"
            elif gastos['ESSENCIAL'] >= (total_pessoa * Decimal('0.70')):
                nova_classe = "Guerreiro da Sobrevivência"
        else:
            nova_classe = "Monge do Silêncio"
            
        pessoa.classe_atual = nova_classe
        pessoa.save()
