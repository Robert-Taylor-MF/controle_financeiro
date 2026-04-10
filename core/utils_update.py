import os
import subprocess
import sys

def check_for_updates():
    """
    Verifica se existem atualizações no GitHub.
    Retorna (update_available, current_commit, remote_commit, error_msg)
    """
    try:
        # Tenta fazer o fetch para atualizar as informações do remoto
        # Usamos check=True para falhar se não houver internet
        subprocess.run(["git", "fetch", "origin", "main"], check=True, capture_output=True, text=True)
        
        # Obtém o hash do commit local
        local_commit = subprocess.check_output(["git", "rev-parse", "HEAD"]).decode().strip()
        
        # Obtém o hash do commit remoto
        remote_commit = subprocess.check_output(["git", "rev-parse", "origin/main"]).decode().strip()
        
        return local_commit != remote_commit, local_commit, remote_commit, None
    except subprocess.CalledProcessError as e:
        return False, None, None, f"Erro ao consultar GitHub: {e.stderr}"
    except Exception as e:
        return False, None, None, str(e)

def trigger_update_signal():
    """
    Cria o arquivo sinalizador para o run.bat e encerra o sistema.
    """
    try:
        with open(".update_pending", "w") as f:
            f.write("trigger")
        return True
    except Exception:
        return False
