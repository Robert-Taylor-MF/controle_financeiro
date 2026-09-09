import csv
import io
from datetime import datetime
from core.models import Transacao, Pessoa, CartaoCredito

def processar_fatura_csv(arquivo_csv, cartao_id, mes_fatura, ano_fatura, user_id):
    """
    Processa um arquivo CSV, extraindo Data, Descrição e Valor.
    Retorna uma tupla (sucesso, mensagem/sugestoes_pendentes)
    """
    try:
        # Lê o arquivo
        conteudo = arquivo_csv.read().decode('utf-8-sig', errors='ignore')
        leitor = csv.reader(io.StringIO(conteudo), delimiter=';')
        linhas = list(leitor)
        
        # Se falhou, tenta com vírgula
        if len(linhas) > 0 and len(linhas[0]) == 1:
            leitor = csv.reader(io.StringIO(conteudo), delimiter=',')
            linhas = list(leitor)
            
        if not linhas:
            return False, "O arquivo CSV está vazio."
            
        cabecalho = [str(c).strip().lower() for c in linhas[0]]
        
        # Encontra os índices das colunas
        idx_data = -1
        idx_desc = -1
        idx_valor = -1
        
        for i, col in enumerate(cabecalho):
            if any(p in col for p in ['data', 'lançamento', 'lancamento']):
                idx_data = i
            elif any(p in col for p in ['descrição', 'descricao', 'nome', 'histórico', 'historico']):
                idx_desc = i
            elif any(p in col for p in ['valor', 'quantia', 'saída', 'saida']):
                idx_valor = i
                
        if idx_data == -1 or idx_desc == -1 or idx_valor == -1:
            return False, f"O CSV precisa ter colunas para Data, Descrição e Valor. Cabeçalhos encontrados: {', '.join(cabecalho)}"
            
        cartao = CartaoCredito.objects.get(id=cartao_id)
        dono = Pessoa.objects.filter(id=user_id).first() if user_id else Pessoa.objects.filter(is_owner=True).first()
        
        transacoes_criadas = []
        
        for linha in linhas[1:]:
            if len(linha) <= max(idx_data, idx_desc, idx_valor):
                continue
                
            data_str = linha[idx_data].strip()
            desc = linha[idx_desc].strip()
            valor_str = linha[idx_valor].strip()
            
            if not desc or not valor_str:
                continue
                
            # Trata o valor numérico
            valor_str = valor_str.replace('R$', '').replace(' ', '').replace(',', '.')
            try:
                valor = float(valor_str)
            except ValueError:
                continue
                
            # Como é despesa, garante que fique positivo para o DB (a menos que a regra local peça negativo)
            # Geralmente despesas são positivas no BD deste app
            valor = abs(valor)
            
            # Trata a data (tenta DD/MM/YYYY)
            try:
                if len(data_str) == 5: # DD/MM
                    data_str = f"{data_str}/{ano_fatura}"
                data_compra = datetime.strptime(data_str, "%d/%m/%Y").date()
            except ValueError:
                # Fallback, usa 01/mes/ano
                data_compra = datetime.strptime(f"01/{mes_fatura}/{ano_fatura}", "%d/%m/%Y").date()
                
            # Cria a transação (pendente de categoria)
            # Evita duplicidade simples
            existe = Transacao.objects.filter(
                cartao=cartao, 
                descricao=desc, 
                valor=valor, 
                data_compra=data_compra,
                mes_fatura=mes_fatura,
                ano_fatura=ano_fatura
            ).exists()
            
            if not existe:
                t = Transacao(
                    responsavel=dono,
                    cartao=cartao,
                    descricao=desc,
                    valor=valor,
                    data_compra=data_compra,
                    mes_fatura=mes_fatura,
                    ano_fatura=ano_fatura,
                    tipo='despesa'
                )
                t.save()
                transacoes_criadas.append(t)
                
        # Agora manda classificar (isso usará primeiro a memória, depois IA se sobrar)
        from core.services.pdf_service import avaliar_transacoes_em_lote
        if transacoes_criadas:
            sucesso, resultado = avaliar_transacoes_em_lote(transacoes_criadas, user_id=user_id)
            return sucesso, resultado
        else:
            return True, "Nenhuma transação nova importada (já existiam no banco ou arquivo sem linhas válidas)."
            
    except Exception as e:
        return False, f"Erro ao processar CSV: {str(e)}"
