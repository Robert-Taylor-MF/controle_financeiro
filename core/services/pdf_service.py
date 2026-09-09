import os
import json
import time
import pdfplumber
from google import genai
from dotenv import load_dotenv
from core.models import Transacao, Pessoa, CartaoCredito, Categoria
from datetime import datetime, timedelta
from django.core.cache import cache

# 2. Execute a função para carregar o arquivo .env
# Usamos `override=True` para garantir que ele Puxe do .env e ignore qualquer variável global do Windows presa na memória
load_dotenv(override=True)

def obter_melhor_modelo_groq(cliente, override=None, force_refresh=False, exclude_models=None):
    """
    Descobre e retorna dinamicamente o modelo Llama ativo mais recente disponível no Groq.
    Possui sistema de cache e lista de prioridades para evitar chamadas de API em excesso.
    """
    from django.core.cache import cache
    
    if exclude_models is None:
        exclude_models = []
        
    if override and override.strip():
        return override.strip()
        
    cache_key = "groq_active_llama_model"
    if not force_refresh and not exclude_models:
        cached_model = cache.get(cache_key)
        if cached_model:
            return cached_model

    fallback_models = [
        "llama-3.3-70b-versatile",
        "llama-3.1-70b-versatile",
        "llama-3.3-70b-specdec",
        "llama-3.1-8b-instant",
        "llama3-70b-8192",
        "llama3-8b-8192",
    ]

    try:
        models_page = cliente.models.list()
        model_list = models_page.data if hasattr(models_page, 'data') else []
        model_ids = [m.id for m in model_list if hasattr(m, 'id') and 'llama' in m.id.lower() and 'guard' not in m.id.lower() and 'vision' not in m.id.lower() and m.id not in exclude_models]
        
        if not model_ids:
            # Fallback: pega qualquer modelo de texto disponível (ex: Qwen, GPT-OSS)
            model_ids = [m.id for m in model_list if hasattr(m, 'id') and hasattr(m, 'output_modalities') and 'text' in m.output_modalities and 'guard' not in m.id.lower() and 'vision' not in m.id.lower() and m.id not in exclude_models]
        
        if model_ids:
            # Algoritmo de classificação: prioriza 70b/90b versáteis > 70b normais > 8b instant
            def peso_modelo(m_id):
                id_lower = m_id.lower()
                pontos = 0
                if "70b" in id_lower or "90b" in id_lower or "120b" in id_lower:
                    pontos += 100
                elif "8b" in id_lower:
                    pontos += 5
                if "versatile" in id_lower or "oss" in id_lower:
                    pontos += 50
                if "3.3" in id_lower or "qwen3.8" in id_lower:
                    pontos += 40
                elif "3.2" in id_lower or "qwen3.6" in id_lower:
                    pontos += 30
                elif "3.1" in id_lower:
                    pontos += 20
                elif "instant" in id_lower:
                    pontos += 10
                return pontos

            model_ids.sort(key=peso_modelo, reverse=True)
            melhor_modelo = model_ids[0]
            cache.set(cache_key, melhor_modelo, timeout=21600) # Cache por 6 horas
            print(f"[DEBUG Groq] Modelo detectado dinamicamente: {melhor_modelo}")
            return melhor_modelo

    except Exception as e:
        print(f"[DEBUG Groq] Falha ao consultar lista de modelos ({str(e)}). Usando fallback.")

    for fb in fallback_models:
        if fb not in exclude_models:
            return fb
            
    return fallback_models[0]


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

    from core.models import MestreSeguranca
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
    
    # Divide texto_fatura em chunks para não estourar o limite de tokens da IA (Erro 400 - prompt ou completion)
    MAX_CHUNK = 4000
    chunks = []
    if len(texto_fatura) > MAX_CHUNK:
        current_chunk = ""
        for line in texto_fatura.splitlines(True):
            # Previne linhas gigantescas que quebram o chunking
            if len(line) > MAX_CHUNK:
                if current_chunk: chunks.append(current_chunk)
                chunks.append(line[:MAX_CHUNK])
                current_chunk = line[MAX_CHUNK:]
                continue
                
            if len(current_chunk) + len(line) > MAX_CHUNK:
                chunks.append(current_chunk)
                current_chunk = line
            else:
                current_chunk += line
        if current_chunk:
            chunks.append(current_chunk)
    else:
        chunks = [texto_fatura]
        
    dados_extraidos = []
    
    try:
        import time
        import json
        
        for idx, chunk_texto in enumerate(chunks):
            print(f"[DEBUG Oráculo] Processando chunk {idx+1}/{len(chunks)} ({len(chunk_texto)} caracteres)")
            tentativa = 0
            resposta_texto = None
            
            while True:
                if user_id and cache.get(f'cancelar_oraculo_{user_id}'):
                    return False, "Operação cancelada pelo usuário."
    
                try:
                    if usar_groq:
                        groq_override = ms.groq_model_override if ms else None
                        modelos_banidos = []
                        
                        while True:
                            modelo_groq = obter_melhor_modelo_groq(cliente, override=groq_override, force_refresh=(len(modelos_banidos)>0), exclude_models=modelos_banidos)
                            try:
                                response = cliente.chat.completions.create(
                                    messages=[
                                        {"role": "system", "content": prompt},
                                        {"role": "user", "content": f"Texto da Fatura:\\n{chunk_texto}"}
                                    ],
                                    model=modelo_groq,
                                    temperature=0.1
                                )
                                resposta_texto = response.choices[0].message.content
                                break
                            except Exception as e_groq:
                                erro_g = str(e_groq).lower()
                                if ("model" in erro_g and ("not found" in erro_g or "decommissioned" in erro_g or "deprecated" in erro_g or "invalid" in erro_g or "exist" in erro_g or "access" in erro_g)) or "404" in erro_g:
                                    if modelo_groq not in modelos_banidos:
                                        modelos_banidos.append(modelo_groq)
                                        continue
                                    else:
                                        raise Exception(f"Nenhum modelo Groq disponível na conta falhou: {str(e_groq)}")
                                else:
                                    raise e_groq
                    else:
                        modelos_gemini = ['gemini-2.5-flash', 'gemini-1.5-flash', 'gemini-2.0-flash-exp']
                        ultimo_erro = None
                        for mod_gemini in modelos_gemini:
                            try:
                                resposta = cliente.models.generate_content(
                                    model=mod_gemini,
                                    contents=prompt + "\n\nTexto:\n" + chunk_texto
                                )
                                resposta_texto = resposta.text
                                break
                            except Exception as e_gemini:
                                ultimo_erro = e_gemini
                        if not resposta_texto and ultimo_erro:
                            raise ultimo_erro
                        
                    break # Sucesso neste chunk
                except Exception as e:
                    erro_str = str(e)
                    if "503" in erro_str or "unavailable" in erro_str.lower() or "high demand" in erro_str.lower() or "429" in erro_str or "rate limit" in erro_str.lower():
                        tentativa += 1
                        print(f"[DEBUG Oráculo] Oráculo sobrecarregado. Aguardando 5s... (Tentativa {tentativa})")
                        cancelado = False
                        for _ in range(5):
                            if user_id and cache.get(f'cancelar_oraculo_{user_id}'):
                                cancelado = True
                                break
                            time.sleep(1)
                        if cancelado:
                            return False, "Operação cancelada pelo usuário."
                    else:
                        raise e
                        
            texto_ia = resposta_texto.strip()
            
            if '```json' in texto_ia:
                texto_ia = texto_ia.split('```json')[1].split('```')[0].strip()
            elif '```' in texto_ia:
                partes = texto_ia.split('```')
                if len(partes) >= 3:
                    texto_ia = partes[1].strip()
    
            primeiro_colchete = texto_ia.find('[')
            ultimo_colchete = texto_ia.rfind(']')
            if primeiro_colchete != -1 and ultimo_colchete != -1:
                texto_ia = texto_ia[primeiro_colchete:ultimo_colchete+1]
    
            try:
                dados_chunk = json.loads(texto_ia)
                if isinstance(dados_chunk, list):
                    dados_extraidos.extend(dados_chunk)
            except json.JSONDecodeError as e:
                print(f"[DEBUG] Falha ao decodificar JSON do chunk {idx+1}: {e}")
                pass # Continue to next chunk
        
        cartao = CartaoCredito.objects.get(id=cartao_id)
        dono_principal = Pessoa.objects.get(is_owner=True) 
        
        transacoes_criadas = []
        sugestoes_pendentes = []
        
        ignoradas_por_duplicidade = 0
        ids_conciliados = set()
        
        for item in dados_extraidos:
            # Garante que o valor venha como float com segurança máxima
            v = item.get('valor', 0)
            if isinstance(v, (int, float)):
                item['valor'] = float(v)
            else:
                v_str = str(v).replace('R$', '').replace(' ', '').strip()
                if ',' in v_str and '.' in v_str:
                    if v_str.rfind(',') > v_str.rfind('.'):
                        v_str = v_str.replace('.', '').replace(',', '.')
                    else:
                        v_str = v_str.replace(',', '')
                elif ',' in v_str:
                    if v_str.count(',') > 1:
                        v_str = v_str.replace(',', '')
                    else:
                        v_str = v_str.replace(',', '.')
                try:
                    item['valor'] = float(v_str)
                except ValueError:
                    item['valor'] = 0.0
            cat_nome = item.get('categoria_sugerida', '').strip()
            categoria_obj = None
            desc = item['descricao']
            teve_historico = False
            
            # Memória do Oráculo (Histórico)
            transacao_historica = Transacao.objects.filter(descricao__iexact=desc, categoria__isnull=False).order_by('-data_compra').first()
            if transacao_historica:
                categoria_obj = transacao_historica.categoria
                teve_historico = True
                print(f"[DEBUG] Memória do Oráculo lembrou de: '{desc}' -> {categoria_obj}")
            elif cat_nome:
                # Se não achou no histórico, pega a sugestão da IA
                categoria_obj = Categoria.objects.filter(nome__iexact=cat_nome).first()
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
                
            transacao_existente_pendente = None
            eh_duplicata = False
            
            if data_ia:
                # Busca TODAS as transações no mesmo cartão com o exato valor
                candidatas = Transacao.objects.filter(
                    cartao=cartao,
                    valor=item['valor']
                )
                
                # Procura a que mais se aproxima (margem de erro de até 1 dia)
                for t in candidatas:
                    if t.id in ids_conciliados:
                        continue
                        
                    delta = abs((t.data_compra - data_ia).days)
                    if delta <= 1:
                        ids_conciliados.add(t.id)
                        # Se já está faturada ou paga, é duplicata exata!
                        if t.status in ['FATURADO', 'PAGO'] or (t.mes_fatura == int(mes_fatura) and t.ano_fatura == int(ano_fatura)):
                            eh_duplicata = True
                            break
                        # Se está pendente E não foi vinculada a esta fatura ainda, conciliamos!
                        elif t.status == 'PENDENTE':
                            transacao_existente_pendente = t
                            break
            
            if eh_duplicata:
                ignoradas_por_duplicidade += 1
                continue

            if transacao_existente_pendente:
                # MATCH! Encontrou o gasto diário
                transacao_existente_pendente.status = 'FATURADO'
                transacao_existente_pendente.mes_fatura = int(mes_fatura)
                transacao_existente_pendente.ano_fatura = int(ano_fatura)
                
                if teve_historico:
                    if not transacao_existente_pendente.categoria:
                        transacao_existente_pendente.categoria = categoria_obj
                    transacao_existente_pendente.save()
                    transacoes_criadas.append(transacao_existente_pendente)
                    print(f"[DEBUG] Conciliou (com histórico): '{transacao_existente_pendente.descricao}'")
                else:
                    transacao_existente_pendente.save()
                    transacoes_criadas.append(transacao_existente_pendente)
                    if not transacao_existente_pendente.categoria and categoria_obj:
                        sugestoes_pendentes.append({
                            'tipo': 'existente',
                            'id_transacao': transacao_existente_pendente.id,
                            'descricao': desc,
                            'valor': float(item['valor']),
                            'data_compra': item['data_compra'],
                            'categoria_sugerida_id': categoria_obj.id,
                            'categoria_sugerida_nome': categoria_obj.nome
                        })
                        print(f"[DEBUG] Conciliou (pendente IA): '{transacao_existente_pendente.descricao}'")
            else:
                if teve_historico or not categoria_obj:
                    # Tem no histórico ou a IA não sugeriu nada (cria sem categoria)
                    nova_transacao = Transacao.objects.create(
                        descricao=desc,
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
                else:
                    # Não tem histórico, e a IA sugeriu algo -> Pendente de aprovação
                    sugestoes_pendentes.append({
                        'tipo': 'nova',
                        'cartao_id': cartao.id,
                        'mes_fatura': int(mes_fatura),
                        'ano_fatura': int(ano_fatura),
                        'descricao': desc,
                        'valor': float(item['valor']),
                        'data_compra': item['data_compra'],
                        'categoria_sugerida_id': categoria_obj.id,
                        'categoria_sugerida_nome': categoria_obj.nome
                    })
            
        # O retorno agora contém os dados extraídos em tupla para ser manuseado pela view
        msg = f"{len(transacoes_criadas)} despesas extraídas e categorizadas!"
        if ignoradas_por_duplicidade > 0:
            msg += f" (E {ignoradas_por_duplicidade} itens já existiam e foram pulados para evitar duplicidade)."
        return True, (msg, sugestoes_pendentes)

        
    except Exception as e:
        print("\n[DEBUG] ERRO CRÍTICO:", str(e))
        return False, f"Erro na IA ou ao salvar: {str(e)}"

def avaliar_transacoes_em_lote(transacoes, user_id=None):
    """
    Recebe um QuerySet de Transacoes não categorizadas (categoria__isnull=True).
    Usa o histórico (Memória) primeiro. O que sobrar, envia pra IA classificar.
    Retorna uma lista de sugestões pendentes igual ao PDF.
    """
    import time
    from core.models import Categoria, Transacao
    import json
    
    sugestoes_pendentes = []
    transacoes_para_ia = []
    
    from core.services.memoria_service import classificar_por_memoria
    user = Pessoa.objects.filter(id=user_id).first() if user_id else None

    # 1. Tenta classificar usando a Memória Histórica primeiro
    for t in transacoes:
        categoria_sugerida = classificar_por_memoria(t.descricao, user=user)
        if categoria_sugerida:
            t.categoria = categoria_sugerida
            t.save()
        else:
            transacoes_para_ia.append(t)
            
    if not transacoes_para_ia:
        return True, "Nenhuma transação nova para o Oráculo avaliar (todas já conhecidas)."

    # 2. O que sobrou vai para a IA
    categorias_validas = Categoria.objects.values_list('nome', flat=True)
    lista_categorias = ", ".join(categorias_validas)
    
    
    # Dividir transacoes_para_ia em chunks de 15 transações para evitar erro 400
    chunk_size = 15
    transacoes_chunks = [transacoes_para_ia[i:i + chunk_size] for i in range(0, len(transacoes_para_ia), chunk_size)]
    itens = []
    
    prompt = f"""
    Você é um analista de dados financeiros.
    Analise a lista de despesas fornecida e classifique CADA UMA adivinhando a categoria correta.
    
    REGRA ABSOLUTA DE CATEGORIZAÇÃO:
    Você SÓ PODE sugerir um destes nomes exatos de categoria: {lista_categorias}
    Se você não tiver 100% de certeza, deixe o campo "categoria" vazio "".
    
    Formato obrigatório JSON:
    [
      {{
        "id": "O ID da despesa fornecido na lista",
        "categoria": "Nome exato da Categoria ou vazio"
      }}
    ]
    """
    
    try:
        from core.models import MestreSeguranca
        ms = MestreSeguranca.objects.first()
        ai_default = ms.ai_default if ms else 'GEMINI'
        usar_groq = (ai_default == 'GROQ')
        cliente = None
        
        if usar_groq:
            chave_api = ms.get_groq_key() if ms else None
            if not chave_api:
                return False, "Oráculo Groq não configurado."
            from groq import Groq
            cliente = Groq(api_key=chave_api)
        else:
            from google import genai
            import os
            chave_api = (ms.get_api_key() if ms and ms.get_api_key() else os.getenv("GEMINI_API_KEY"))
            if not chave_api:
                return False, "Oráculo Gemini não configurado."
            cliente = genai.Client(api_key=chave_api)
            
        import time
        import json
        
        for idx, t_chunk in enumerate(transacoes_chunks):
            texto_lote = ""
            for t in t_chunk:
                texto_lote += f"- ID: {t.id} | Descrição: {t.descricao} | Valor: {t.valor} | Data: {t.data_compra.strftime('%d/%m/%Y')}\n"
                
            print(f"[DEBUG Lote] Processando lote {idx+1}/{len(transacoes_chunks)} ({len(t_chunk)} transações)")
            
            tentativa = 0
            resposta_texto = None
            
            while True:
                if user_id and cache.get(f'cancelar_oraculo_{user_id}'):
                    return False, "Operação cancelada pelo usuário."
                    
                try:
                    if usar_groq:
                        ms = None
                        try:
                            from core.models import MestreSeguranca
                            ms = MestreSeguranca.objects.first()
                        except: pass
                        groq_override = ms.groq_model_override if ms else None
                        modelos_banidos = []
                        
                        while True:
                            modelo_groq = obter_melhor_modelo_groq(cliente, override=groq_override, force_refresh=(len(modelos_banidos)>0), exclude_models=modelos_banidos)
                            try:
                                response = cliente.chat.completions.create(
                                    messages=[
                                        {"role": "system", "content": prompt},
                                        {"role": "user", "content": f"Lista de Despesas:\\n{texto_lote}"}
                                    ],
                                    model=modelo_groq,
                                    temperature=0.1
                                )
                                resposta_texto = response.choices[0].message.content
                                break
                            except Exception as e_groq:
                                erro_g = str(e_groq).lower()
                                if ("model" in erro_g and ("not found" in erro_g or "decommissioned" in erro_g or "deprecated" in erro_g or "invalid" in erro_g or "exist" in erro_g or "access" in erro_g)) or "404" in erro_g:
                                    if modelo_groq not in modelos_banidos:
                                        modelos_banidos.append(modelo_groq)
                                        continue
                                    else:
                                        raise Exception(f"Nenhum modelo Groq disponível na conta falhou: {str(e_groq)}")
                                else:
                                    raise e_groq
                    else:
                        modelos_gemini = ['gemini-2.5-flash', 'gemini-1.5-flash', 'gemini-2.0-flash-exp']
                        ultimo_erro = None
                        for mod_gemini in modelos_gemini:
                            try:
                                resposta = cliente.models.generate_content(
                                    model=mod_gemini,
                                    contents=prompt + "\n\nLista:\n" + texto_lote
                                )
                                resposta_texto = resposta.text
                                break
                            except Exception as e_gemini:
                                ultimo_erro = e_gemini
                        if not resposta_texto and ultimo_erro:
                            raise ultimo_erro
                            
                    break
                except Exception as e:
                    erro_str = str(e)
                    if "503" in erro_str or "unavailable" in erro_str.lower() or "high demand" in erro_str.lower() or "429" in erro_str or "rate limit" in erro_str.lower():
                        tentativa += 1
                        cancelado = False
                        for _ in range(5):
                            if user_id and cache.get(f'cancelar_oraculo_{user_id}'):
                                cancelado = True
                                break
                            time.sleep(1)
                        if cancelado:
                            return False, "Operação cancelada."
                    else:
                        raise e
                        
            texto_ia = resposta_texto.strip()
            
            if '```json' in texto_ia:
                texto_ia = texto_ia.split('```json')[1].split('```')[0].strip()
            elif '```' in texto_ia:
                partes = texto_ia.split('```')
                if len(partes) >= 3:
                    texto_ia = partes[1].strip()
            
            primeiro_colchete = texto_ia.find('[')
            ultimo_colchete = texto_ia.rfind(']')
            if primeiro_colchete != -1 and ultimo_colchete != -1:
                texto_ia = texto_ia[primeiro_colchete:ultimo_colchete+1]
                
            try:
                dados_chunk = json.loads(texto_ia)
                if isinstance(dados_chunk, list):
                    itens.extend(dados_chunk)
            except json.JSONDecodeError as e:
                pass

        
        # Processar o JSON da IA
        for item in itens:
            t_id = str(item.get('id', ''))
            cat_sugerida = item.get('categoria', '')
            
            # Encontra a transacao
            transacao = next((t for t in transacoes_para_ia if str(t.id) == t_id), None)
            if transacao:
                cat_obj = Categoria.objects.filter(nome__iexact=cat_sugerida).first()
                if cat_obj:
                    sugestoes_pendentes.append({
                        'tipo': 'existente',
                        'id_transacao': transacao.id,
                        'descricao': transacao.descricao,
                        'valor': float(transacao.valor),
                        'data_compra': transacao.data_compra.strftime('%Y-%m-%d'),
                        'categoria_sugerida_id': cat_obj.id,
                        'categoria_sugerida_nome': cat_obj.nome
                    })
                    
        return True, sugestoes_pendentes
        
    except Exception as e:
        print("[DEBUG] Erro em avaliar_transacoes_em_lote:", e)
        return False, str(e)
