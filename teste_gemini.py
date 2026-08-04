import os
import google.generativeai as genai
from dotenv import load_dotenv

# Carrega as variáveis ocultas do arquivo .env
load_dotenv()

# Configura a API com a sua chave
CHAVE_API = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=CHAVE_API)

# Escolhemos o modelo mais rápido e eficiente para texto
model = genai.GenerativeModel('gemini-2.5-flash')

# O "System Prompt": as regras estritas para a IA
prompt_instrucao = """
Você é um extrator de dados financeiros de faturas de cartão de crédito.
Sua única função é ler o texto bagunçado da fatura e retornar um array JSON.
Não responda com saudações, não explique o código. Retorne APENAS o JSON válido.

Formato esperado:
[
  {
    "data_compra": "YYYY-MM-DD",
    "descricao": "Nome do estabelecimento",
    "valor": 99.99
  }
]

Texto da fatura para extrair:
"""

# Um texto bagunçado simulando você copiando e colando da fatura em PDF
texto_fatura_suja = """
12/03/2026 UBER *TRIP SAO PAULO 45,90
15 MAR PAG*MERCADOLIVRE OSASCO 120.00
16/03 IFOOD *BURGERKING 35,50
"""

print("Enviando para o Gemini... aguarde.")

# Fazendo a requisição
resposta = model.generate_content(prompt_instrucao + texto_fatura_suja)

print("\n--- RESPOSTA DA IA (JSON PURO) ---")
print(resposta.text)