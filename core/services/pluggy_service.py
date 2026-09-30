import requests
from datetime import datetime
from decimal import Decimal
from core.models import CartaoCredito, Transacao, Pessoa, MestreSeguranca, Rateio
from core.services.memoria_service import classificar_por_memoria

PLUGGY_BASE_URL = "https://api.pluggy.ai"

def get_pluggy_token():
    seguranca = MestreSeguranca.objects.first()
    if not seguranca:
        return None
    client_id = seguranca.get_pluggy_client_id()
    client_secret = seguranca.get_pluggy_client_secret()
    
    if not client_id or not client_secret:
        return None

    response = requests.post(
        f"{PLUGGY_BASE_URL}/auth",
        json={"clientId": client_id, "clientSecret": client_secret}
    )
    if response.status_code == 200:
        return response.json().get("apiKey")
    return None

def sync_pluggy_transactions():
    """
    Sincroniza todas as transações dos cartões configurados no Pluggy
    """
    token = get_pluggy_token()
    if not token:
        return False, "Credenciais do Pluggy (Client ID/Secret) não configuradas ou inválidas."

    headers = {
        "X-API-KEY": token,
        "accept": "application/json"
    }

    # Pega todos os cartões que têm um account ID do Pluggy configurado
    cartoes_pluggy = CartaoCredito.objects.exclude(pluggy_account_id__isnull=True).exclude(pluggy_account_id="")
    
    if not cartoes_pluggy.exists():
        return False, "Nenhum Cartão de Crédito ou Conta possui um 'ID da Conta no Pluggy' configurado. Configure no QG primeiro."

    # Definir o dono para fallback e para a memória
    owner = Pessoa.objects.filter(is_owner=True).first()
    
    # Mês e ano atual para faturamento padrão (pode ser ajustado)
    hoje = datetime.now()

    novas_transacoes = 0

    for cartao in cartoes_pluggy:
        # Busca transações dos últimos 30 dias na API
        url = f"{PLUGGY_BASE_URL}/transactions?accountId={cartao.pluggy_account_id}"
        
        try:
            resp = requests.get(url, headers=headers)
            if resp.status_code != 200:
                continue
                
            dados = resp.json()
            results = dados.get("results", [])
            
            for item in results:
                # O Pluggy usa IDs unicos pra cada transação
                pluggy_id = item.get("id")
                descricao = item.get("description", "Compra Pluggy")
                amount = item.get("amount", 0)
                
                # Vamos considerar apenas despesas (geralmente negative amount para cartão, ou positive pra debitos, 
                # Pluggy: CREDIT expenses are positive, DEBIT expenses are negative.
                # Aqui simplificamos: pegamos o valor absoluto pra despesa. Se for income, ignoramos.
                # O type no Pluggy: CREDIT (pra compras) / DEBIT (pra debito) etc
                # Vamos tratar tudo como despesa (valor absoluto) para cartões de crédito.
                valor_absoluto = abs(amount)
                
                if valor_absoluto == 0:
                    continue

                # Evitar duplicadas
                if Transacao.objects.filter(pluggy_id=pluggy_id).exists():
                    continue
                
                data_iso = item.get("date") # "YYYY-MM-DD..."
                if data_iso:
                    data_compra = datetime.fromisoformat(data_iso.replace("Z", "+00:00")).date()
                else:
                    data_compra = hoje.date()

                # Tentar classificar por memória (IA do banco)
                categoria_sugerida = classificar_por_memoria(descricao, user=owner)
                
                # Tentar achar se essa compra já foi de alguém específico no passado
                responsavel_sugerido = owner
                transacao_anterior = Transacao.objects.filter(descricao__iexact=descricao).order_by('-data_compra').first()
                rateios_anteriores = []
                
                if transacao_anterior:
                    responsavel_sugerido = transacao_anterior.responsavel
                    # Se tinha rateio, vamos clonar a estrutura de rateio!
                    rateios_anteriores = transacao_anterior.rateios.all()

                # Salvar a transação nova
                t_nova = Transacao.objects.create(
                    descricao=descricao,
                    valor=Decimal(str(valor_absoluto)),
                    data_compra=data_compra,
                    mes_fatura=hoje.month, # Simplificação, ideal seria usar dia de fechamento
                    ano_fatura=hoje.year,
                    cartao_credito=cartao,
                    pluggy_id=pluggy_id,
                    responsavel=responsavel_sugerido,
                    categoria=categoria_sugerida
                )

                # Se havia rateio na transação histórica idêntica, a gente clona os rateios proporcionalmente
                if rateios_anteriores:
                    valor_original = transacao_anterior.valor
                    if valor_original > 0:
                        for r_old in rateios_anteriores:
                            proporcao = r_old.valor / valor_original
                            Rateio.objects.create(
                                transacao=t_nova,
                                pessoa=r_old.pessoa,
                                valor=Decimal(str(valor_absoluto)) * proporcao
                            )

                novas_transacoes += 1

        except Exception as e:
            print(f"Erro ao sincronizar Pluggy para cartao {cartao.nome}: {e}")
            continue

    return True, f"Sincronização concluída! {novas_transacoes} novas transações importadas com sucesso e memorizadas."
