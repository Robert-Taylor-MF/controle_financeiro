import os
import json
import time
import pdfplumber
from google import genai
from dotenv import load_dotenv
from .models import Transacao, Pessoa, CartaoCredito, Categoria
from datetime import datetime, timedelta

# 2. Execute a função para carregar o arquivo .env
# Usamos `override=True` para garantir que ele Puxe do .env e ignore qualquer variável global do Windows presa na memória
load_dotenv(override=True)

def processar_fatura_pdf(arquivo_pdf, cartao_id, mes_fatura, ano_fatura, user_id=None):
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
    from django.core.cache import cache

    ms = MestreSeguranca.objects.first()
    ai_default = ms.ai_default if ms else 'GEMINI'
    
    usar_groq = (ai_default == 'GROQ')
    cliente = None

    if usar_groq:
        chave_api = ms.get_groq_key() if ms else None
        if not chave_api:
            return False, "O Oráculo está sem magia (Groq). Configure a Chave API do Groq no QG."
        try:
            from groq import Groq
            cliente = Groq(api_key=chave_api)
        except Exception as e:
            return False, f"Falha ao evocar o Oráculo Groq: {str(e)}"
    else:
        chave_api = (ms.get_api_key() if ms and ms.get_api_key() else os.getenv("GEMINI_API_KEY"))
        if not chave_api:
            return False, "O Oráculo está sem magia (Gemini). Configure a Chave API do Gemini no QG ou .env."
        try:
            cliente = genai.Client(api_key=chave_api)
        except Exception as e:
            return False, f"Falha ao evocar o Oráculo Gemini: {str(e)}"

    # Limpa a flag de cancelamento
    if user_id:
        cache.delete(f'cancelar_oraculo_{user_id}')

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
        tentativa = 0
        resposta_texto = None
        
        while True:
            # Verifica se o usuário cancelou antes de tentar
            if user_id and cache.get(f'cancelar_oraculo_{user_id}'):
                return False, "Operação cancelada pelo usuário."

            try:
                if usar_groq:
                    response = cliente.chat.completions.create(
                        messages=[
                            {"role": "system", "content": prompt},
                            {"role": "user", "content": f"Texto da Fatura:\n{texto_fatura}"}
                        ],
                        model="llama-3.3-70b-versatile",
                        temperature=0.1
                    )
                    resposta_texto = response.choices[0].message.content
                else:
                    resposta = cliente.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=prompt + "\n\nTexto:\n" + texto_fatura
                    )
                    resposta_texto = resposta.text
                    
                break # Se der certo, sai do loop
            except Exception as e:
                erro_str = str(e)
                # Verifica se é erro de alta demanda ou indisponibilidade
                if "503" in erro_str or "UNAVAILABLE" in erro_str or "high demand" in erro_str or "429" in erro_str or "rate limit" in erro_str.lower():
                    tentativa += 1
                    print(f"[DEBUG] Oráculo sobrecarregado. Aguardando 5 segundos... (Tentativa {tentativa})")
                    
                    # Aguarda 5 segundos, mas checa a cada 1 segundo se houve cancelamento
                    cancelado = False
                    for _ in range(5):
                        if user_id and cache.get(f'cancelar_oraculo_{user_id}'):
                            cancelado = True
                            break
                        time.sleep(1)
                        
                    if cancelado:
                        return False, "Operação cancelada pelo usuário."
                else:
                    # Se for outro tipo de erro (ex: falha de API key), falha na hora
                    raise e
                    
        texto_ia = resposta_texto.strip()
        
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
            data_ia_str = item.get('data_compra', '')
            data_ia = None
            
            # Tenta converter a data da IA em vários formatos possíveis
            for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%d/%m/%y', '%Y/%m/%d'):
                try:
                    data_ia = datetime.strptime(data_ia_str, fmt).date()
                    break
                except ValueError:
                    pass
                    
            if data_ia:
                # Garante que o item tenha o formato YYYY-MM-DD pro banco de dados não reclamar
                item['data_compra'] = data_ia.strftime('%Y-%m-%d')
            else:
                # Se a IA alucinou totalmente na data, coloca o primeiro dia do mês da fatura pra não quebrar
                data_ia = datetime(int(ano_fatura), int(mes_fatura), 1).date()
                item['data_compra'] = data_ia.strftime('%Y-%m-%d')
                
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