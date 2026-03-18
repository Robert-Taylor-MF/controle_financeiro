import os
import json
import pdfplumber
import google.generativeai as genai
from dotenv import load_dotenv
from .models import Transacao, Pessoa, CartaoCredito, Categoria

# 2. Execute a função para carregar o arquivo .env
load_dotenv()

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

    chave_api = os.getenv("GEMINI_API_KEY")
    genai.configure(api_key=chave_api)
    model = genai.GenerativeModel('gemini-2.5-flash')
    
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
        resposta = model.generate_content(prompt + "\n\nTexto:\n" + texto_fatura)
        texto_ia = resposta.text.strip()
        
        # ==========================================
        # DEBUG 2: O que a IA respondeu?
        # ==========================================
        print("\n[DEBUG] Resposta pura da IA:\n", texto_ia)

        if texto_ia.startswith('```json'):
            texto_ia = texto_ia.replace('```json', '').replace('```', '').strip()
            
        dados_extraidos = json.loads(texto_ia)
        
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