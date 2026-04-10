import os
import subprocess
import sys

def check_for_updates():
    """
    Verifica se existem atualizações comparando o arquivo version.txt local e remoto.
    Retorna (update_available, local_version, remote_version, error_msg)
    """
    try:
        # 1. Lê a versão local
        version_path = os.path.join(os.getcwd(), "version.txt")
        local_version = "v?"
        if os.path.exists(version_path):
            with open(version_path, "r") as f:
                local_version = f.read().strip()
        
        # 2. Faz o fetch para garantir que o remoto está atualizado
        subprocess.run(["git", "fetch", "origin", "main"], check=True, capture_output=True, text=True)
        
        # 3. Lê a versão remota do GitHub (sem baixar os arquivos ainda)
        remote_version = subprocess.check_output(["git", "show", "origin/main:version.txt"]).decode().strip()
        
        return local_version != remote_version, local_version, remote_version, None
    except subprocess.CalledProcessError as e:
        return False, None, None, "Erro ao conectar com Grande Arquivo (GitHub)."
    except Exception as e:
        return False, None, None, str(e)
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
