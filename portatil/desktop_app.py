import os
import sys
import time
import threading
import urllib.request
import webview

# Início do Log para Debug do PyInstaller
log_file = open('desktop_debug.log', 'w', encoding='utf-8')
sys.stdout = log_file
sys.stderr = log_file


# Adiciona o diretório pai (raiz do projeto) ao sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Configura as variáveis de ambiente do Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'setup.settings')

import django
django.setup()

from django.core.management import call_command
from waitress import serve
from setup.wsgi import application

import socket

def get_free_port():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('', 0))
    port = s.getsockname()[1]
    s.close()
    return port

HOST = '127.0.0.1'
PORT = get_free_port()
URL = f'http://{HOST}:{PORT}'

def run_server():
    """Inicia o servidor de produção Waitress em segundo plano."""
    try:
        call_command('migrate', interactive=False)
    except Exception as e:
        print(f"[Desktop App] Aviso nas migrações: {e}")
    
    print(f"[Desktop App] Motor Waitress rodando em {URL}...")
    serve(application, host=HOST, port=PORT, _quiet=True)

def wait_for_server():
    """Aguarda o servidor ficar responsivo antes de abrir a janela."""
    for _ in range(40):
        try:
            with urllib.request.urlopen(URL) as resp:
                if resp.status in (200, 302):
                    return True
        except Exception:
            time.sleep(0.25)
    return False

def main():
    # Sobe o servidor Django/Waitress numa thread daemon
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

    # Aguarda o servidor responder
    wait_for_server()

    print("[Desktop App] Conjurando janela nativa PyWebView...")
    
    # Cria a janela Desktop nativa sem abas de navegador
    window = webview.create_window(
        title='MoneyQuest - Controle Financeiro Gamificado',
        url=URL,
        width=1280,
        height=820,
        min_size=(900, 600),
        resizable=True
    )

    
    # Inicia a janela (fica aberta até o usuário fechar)
    webview.start(private_mode=False)
    
    print("[Desktop App] Janela encerrada. Finalizando aplicação.")
    sys.exit(0)

if __name__ == '__main__':
    main()
