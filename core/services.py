import os
import json
import pdfplumber
from google import genai
from dotenv import load_dotenv
from .models import Transacao, Pessoa, CartaoCredito, Categoria
from datetime import datetime, timedelta

# 2. Execute a função para carregar o arquivo .env
# Usamos `override=True` para garantir que ele Puxe do .env e ignore qualquer variável global do Windows presa na memória
load_dotenv(override=True)

def processar_fatura_pdf(arquivo_pdf, cartao_id, mes_fatura, ano_fatura):
    texto_fatura = ""
    try:
        with pdfplumber.open(arquivo_pdf) as pdf:
            for pagina in pdf.pages:
                texto_extraido = pagina.extract_text()
                if texto_extraido:
                    texto_fatura += texto_extraido + "\n"
    except Exception as e:
        return False, f"Erro ao ler o PDF: {str(e)}"

    if not texto_fatura.strip():
        return False, "O PDF parece estar vazio ou é uma imagem sem texto."

    # 1. Busca as categorias do banco
    categorias_db = Categoria.objects.all()
    # Cria uma lista com o nome exato das categorias. Ex: ['Lazer', 'Alimentação', 'Investimento']
    nomes_categorias = [c.nome for c in categorias_db]
    string_categorias = ", ".join(nomes_categorias)

    # ==========================================
    # DEBUG 1: O que o Python achou no banco?
    # ==========================================
    print("\n[DEBUG] Categorias enviadas para a IA:", string_categorias)

    from .models import MestreSeguranca
    ms = MestreSeguranca.objects.first()
    chave_api = (ms.gemini_api_key if ms and ms.gemini_api_key else os.getenv("GEMINI_API_KEY"))
    
    if not chave_api:
        return False, "O Oráculo está sem magia. Configure a Chave API do Gemini no QG (Central de Cadastros) ou no arquivo local."

    try:
        client = genai.Client(api_key=chave_api)
    except Exception as e:
        return False, f"Falha ao evocar o Oráculo (Erro na Chave): {str(e)}"
    
    # Prompt blindado
    prompt = f"""
    Você é um analista de dados financeiros.
    Extraia as despesas do texto da fatura e classifique CADA UMA tentando adivinhar a categoria correta.
    
    REGRA ABSOLUTA DE CATEGORIZAÇÃO:
    Você SÓ PODE preencher o campo "categoria_sugerida" com um destes nomes exatos: {string_categorias}
    Se você não tiver 100% de certeza, preencha o campo com uma string vazia "". Não invente categorias novas.
    
    Formato obrigatório JSON:
    [
      {{
        "data_compra": "YYYY-MM-DD",
        "descricao": "Nome da despesa/estabelecimento",
        "valor": 99.99,
        "categoria_sugerida": "Nome exato da Categoria ou vazio"
      }}
    ]
    """
    
    try:
        resposta = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt + "\n\nTexto:\n" + texto_fatura
        )
        texto_ia = resposta.text.strip()
        
        # ==========================================
        # DEBUG 2: O que a IA respondeu?
        # ==========================================
        print("\n[DEBUG] Resposta pura da IA:\n", texto_ia)

        # Tenta extrair apenas o bloco JSON caso a IA tenha adicionado texto explicativo antes ou depois
        if '```json' in texto_ia:
            texto_ia = texto_ia.split('```json')[1].split('```')[0].strip()
        elif '```' in texto_ia:
            partes = texto_ia.split('```')
            if len(partes) >= 3:
                texto_ia = partes[1].strip()

        # Se houver sujeira, isola apenas o que está entre os colchetes do Array JSON
        primeiro_colchete = texto_ia.find('[')
        ultimo_colchete = texto_ia.rfind(']')
        if primeiro_colchete != -1 and ultimo_colchete != -1:
            texto_ia = texto_ia[primeiro_colchete:ultimo_colchete+1]

        try:
            dados_extraidos = json.loads(texto_ia)
        except json.JSONDecodeError as e:
            return False, f"O Oráculo se confundiu na profecia (Erro de JSON): {str(e)}. Tente novamente."
        
        cartao = CartaoCredito.objects.get(id=cartao_id)
        dono_principal = Pessoa.objects.get(is_owner=True) 
        
        transacoes_criadas = []
        for item in dados_extraidos:
            cat_nome = item.get('categoria_sugerida', '').strip()
            categoria_obj = None
            
            # Se a IA sugeriu algo, tenta achar no banco ignorando maiúsculas/minúsculas
            if cat_nome:
                categoria_obj = Categoria.objects.filter(nome__iexact=cat_nome).first()
                # ==========================================
                # DEBUG 3: O Python conseguiu casar o nome da IA com o Banco?
                # ==========================================
                print(f"[DEBUG] IA sugeriu: '{cat_nome}' -> Banco encontrou: {categoria_obj}")

            # ==========================================
            # ALGORITMO DE CONCILIAÇÃO BANCÁRIA (O Feitiço de Fusão)
            # ==========================================
            try:
                # Converte a data_compra devolvida pela IA (YYYY-MM-DD) para um objeto date do Python
                data_ia = datetime.strptime(item['data_compra'], '%Y-%m-%d').date()
            except ValueError:
                data_ia = None
                
            transacao_existente = None
            
            if data_ia:
                # Busca transações PENDENTES no mesmo cartão com o exato valor
                candidatas = Transacao.objects.filter(
                    cartao=cartao,
                    valor=item['valor'],
                    status='PENDENTE'
                )
                
                # Procura a que mais se aproxima (margem de erro de até 1 dia pela transição de fuso ou sistema da maquininha)
                for t in candidatas:
                    delta = abs((t.data_compra - data_ia).days)
                    if delta <= 1:
                        transacao_existente = t
                        break

            if transacao_existente:
                # MATCH! Encontrou o gasto diário
                # Altera o status para faturado e vincula competência
                transacao_existente.status = 'FATURADO'
                transacao_existente.mes_fatura = int(mes_fatura)
                transacao_existente.ano_fatura = int(ano_fatura)
                
                # Se não tinha categoria na manual mas a IA sugeriu, aproveita a sugestão
                if not transacao_existente.categoria and categoria_obj:
                    transacao_existente.categoria = categoria_obj
                    
                transacao_existente.save()
                transacoes_criadas.append(transacao_existente)
                print(f"[DEBUG] Conciliou: '{transacao_existente.descricao}' (Manual) com '{item['descricao']}' (Fatura)")
            else:
                # Sem manual ou sem bater os dados? Cria uma nova (o registro do PDF)
                nova_transacao = Transacao.objects.create(
                    descricao=item['descricao'],
                    valor=item['valor'],
                    data_compra=item['data_compra'],
                    responsavel=None,
                    cartao=cartao,
                    categoria=categoria_obj,
                    status='PENDENTE',
                    mes_fatura=int(mes_fatura),
                    ano_fatura=int(ano_fatura)
                )
                transacoes_criadas.append(nova_transacao)
            
        return True, f"{len(transacoes_criadas)} despesas extraídas e categorizadas!"
        
    except Exception as e:
        print("\n[DEBUG] ERRO CRÍTICO:", str(e))
        return False, f"Erro na IA ou ao salvar: {str(e)}"