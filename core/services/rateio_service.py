from decimal import Decimal
from core.models import Pessoa, Rateio, Transacao
from django.contrib import messages

def processar_rateio(nova_transacao, valores_rateio, request=None):
    """
    Processa o rateio de uma transação.
    :param nova_transacao: A instância da Transacao recém salva.
    :param valores_rateio: Dicionário onde a chave é pessoa.id e o valor é o Decimal do rateio.
    :param request: Request do Django para mensagens (opcional).
    """
    soma_party = sum(valores_rateio.values())
    valor_total = nova_transacao.valor
    
    # Se a soma da party for menor ou igual ao valor total, podemos ratear
    # (O que sobrar fica com o dono, ou 0 se ele pagou tudo pra eles e ele nao arca com nada)
    if soma_party <= valor_total:
        valor_dono = valor_total - soma_party
        
        # O Dono original da transação é o "responsavel", mas se for None (ou seja, Party),
        # assumimos o Owner principal do sistema
        owner = nova_transacao.responsavel
        if not owner:
            owner = Pessoa.objects.filter(is_owner=True).first()

        # Cria a fatia do dono, se houver
        if valor_dono > 0 and owner:
            Rateio.objects.create(
                transacao=nova_transacao,
                pessoa=owner,
                valor=valor_dono
            )

        # Cria as fatias para a Party selecionada
        pessoas = Pessoa.objects.in_bulk(valores_rateio.keys())
        
        for pessoa_id, valor_fatia in valores_rateio.items():
            if valor_fatia > 0:
                aliado = pessoas.get(int(pessoa_id))
                if aliado:
                    Rateio.objects.create(
                        transacao=nova_transacao,
                        pessoa=aliado,
                        valor=valor_fatia
                    )
                    
        if request:
            messages.success(request, f"Dano rateado dinamicamente com {len(valores_rateio)} membros da guilda!")
        return True
    else:
        if request:
            messages.error(request, "A soma do rateio excedeu o valor total. Rateio ignorado, gasto registrado integralmente para você.")
        return False

def fragmentar_transacao_existente(transacao_original, valores_rateio, request=None):
    """
    Função de uso para a tela de rateio individual posterior.
    Recebe a transação original e os valores de quem paga o quê.
    """
    soma_rateio = sum(valores_rateio.values())
    
    if soma_rateio != transacao_original.valor:
        if request:
            messages.error(request, f"A soma da divisão (R$ {soma_rateio}) não bate com o valor original (R$ {transacao_original.valor}).")
        return False
        
    # Deleta os rateios antigos se existirem
    transacao_original.rateios.all().delete()
    
    pessoas = Pessoa.objects.in_bulk(valores_rateio.keys())
    
    for pessoa_id, valor_decimal in valores_rateio.items():
        if valor_decimal > 0:
            aliado = pessoas.get(int(pessoa_id))
            if aliado:
                Rateio.objects.create(
                    transacao=transacao_original,
                    pessoa=aliado,
                    valor=valor_decimal
                )
                
    if request:
        messages.success(request, "Despesa fragmentada com sucesso (Rateio aplicado)!")
    return True
