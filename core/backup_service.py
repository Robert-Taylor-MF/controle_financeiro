import os
import shutil
import zipfile
import json
import time
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from django.conf import settings

# Garante que o scheduler inicie apenas uma vez, lidando com o reloader do Django
_scheduler_started = False

# ─────────────────────────────────────────────────────────
#  HELPERS DE STATUS E HISTÓRICO
# ─────────────────────────────────────────────────────────

def _backup_dir():
    """Retorna (e cria se necessário) o diretório de backups."""
    path = os.path.join(settings.BASE_DIR, "backups")
    os.makedirs(path, exist_ok=True)
    return path


def set_backup_status(status: str, message: str):
    """Grava o status atual do backup em status.json (lido por api_status_backup)."""
    try:
        path = os.path.join(_backup_dir(), "status.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"status": status, "message": message, "time": time.time()}, f)
    except Exception:
        pass


def add_backup_history(zip_path: str, destino_extra: str | None = None):
    """Adiciona uma entrada ao histórico de backups (backup_history.json). Mantém os últimos 20."""
    try:
        history_path = os.path.join(_backup_dir(), "backup_history.json")
        history = []
        if os.path.exists(history_path):
            with open(history_path, "r", encoding="utf-8") as f:
                history = json.load(f)

        entry = {
            "timestamp": time.time(),
            "datetime": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            "arquivo": os.path.basename(zip_path),
            "tamanho_kb": round(os.path.getsize(zip_path) / 1024, 1) if os.path.exists(zip_path) else 0,
            "destino_extra": destino_extra,
        }
        history.insert(0, entry)   # Mais recente primeiro
        history = history[:20]     # Mantém só os últimos 20

        with open(history_path, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except Exception as ex:
        print(f"[ForjaDev] Erro ao gravar histórico de backup: {ex}")


def get_backup_history() -> list:
    """Retorna o histórico de backups ou lista vazia."""
    try:
        history_path = os.path.join(_backup_dir(), "backup_history.json")
        if os.path.exists(history_path):
            with open(history_path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return []


def get_last_backup_time() -> float | None:
    """Retorna o timestamp do último backup concluído, ou None."""
    history = get_backup_history()
    if history:
        return history[0].get("timestamp")
    # Fallback: lê o status.json para retrocompatibilidade
    try:
        status_path = os.path.join(_backup_dir(), "status.json")
        if os.path.exists(status_path):
            with open(status_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if data.get("status") == "finished":
                return data.get("time")
    except Exception:
        pass
    return None


# ─────────────────────────────────────────────────────────
#  GERAÇÃO DO ZIP
# ─────────────────────────────────────────────────────────

def gerar_zip_backup() -> str:
    """Captura db.sqlite3 + pasta media e comprime em zip. Retorna o caminho do arquivo."""
    set_backup_status("running", "Forjando o Pergaminho do Tempo... aguarde.")

    db_path = os.path.join(settings.BASE_DIR, "db.sqlite3")
    media_path = os.path.join(settings.BASE_DIR, "media")
    backup_dir = _backup_dir()

    timestamp = datetime.now().strftime("%d-%m-%Y_%H-%M-%S")
    zip_filename = f"Forja_Backup_{timestamp}.zip"
    zip_path = os.path.join(backup_dir, zip_filename)

    try:
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            if os.path.exists(db_path):
                zipf.write(db_path, "db.sqlite3")

            if os.path.exists(media_path):
                for root, dirs, files in os.walk(media_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, settings.BASE_DIR)
                        zipf.write(file_path, arcname)

        # Copia ao diretório customizado (se configurado)
        destino_extra = None
        try:
            from core.models import MestreSeguranca
            ms = MestreSeguranca.objects.first()
            if ms and ms.diretorio_backup:
                target_dir = ms.diretorio_backup
                if os.path.exists(target_dir) and os.path.isdir(target_dir):
                    shutil.copy2(zip_path, target_dir)
                    destino_extra = target_dir
        except Exception as e:
            print(f"[ForjaDev] Erro ao copiar para diretório customizado: {e}")

        # Grava histórico E status de conclusão
        add_backup_history(zip_path, destino_extra)
        set_backup_status(
            "finished",
            f"Backup concluído! {zip_filename} ({round(os.path.getsize(zip_path)/1024, 1)} KB)"
        )
        print(f"[ForjaDev] Backup concluído → {zip_path}")
        return zip_path

    except Exception as e:
        set_backup_status("error", f"Falha ao forjar o backup: {e}")
        print(f"[ForjaDev] ERRO no backup: {e}")
        raise


# ─────────────────────────────────────────────────────────
#  VERIFICAÇÃO DA ROTINA AGENDADA
# ─────────────────────────────────────────────────────────

def verificar_rotina_backup():
    """
    Função agendada que roda a cada minuto.
    1) Verifica se ficou mais de 24h sem backup → backup automático de emergência.
    2) Verifica se é a hora configurada para o backup periódico.
    """
    try:
        from core.models import MestreSeguranca
        ms = MestreSeguranca.objects.first()

        # ── Gap Detection ────────────────────────────────────────────────────
        ultimo = get_last_backup_time()
        if ultimo is not None:
            horas_sem_backup = (time.time() - ultimo) / 3600
            if horas_sem_backup > 24:
                print(
                    f"[ForjaDev] ALERTA: {horas_sem_backup:.1f}h sem backup! "
                    "Disparando backup automático de emergência..."
                )
                gerar_zip_backup()
                return  # Já fez o backup; não precisa checar a rotina normal agora

        # ── Rotina Agendada ──────────────────────────────────────────────────
        if not ms or ms.frequencia_backup == "MANUAL" or not ms.horario_backup:
            return

        agora = datetime.now()

        if agora.hour == ms.horario_backup.hour and agora.minute == ms.horario_backup.minute:
            pode_rodar = False

            if ms.frequencia_backup == "DIARIO":
                pode_rodar = True
            elif ms.frequencia_backup == "SEMANAL" and ms.dias_backup:
                dow = str(agora.weekday())
                dias_configurados = [d.strip() for d in ms.dias_backup.split(",")]
                if dow in dias_configurados:
                    pode_rodar = True

            if pode_rodar:
                print(f"[ForjaDev] Iniciando rotina de Backup Automático ({agora.strftime('%H:%M')})...")
                gerar_zip_backup()

    except Exception as e:
        print(f"[ForjaDev] Falha na verificação de backup: {e}")


def verificar_gap_na_inicializacao():
    """
    Roda uma única vez na inicialização do servidor para checar se o último
    backup tem mais de 24h. Se sim, dispara um backup imediato.
    """
    try:
        ultimo = get_last_backup_time()
        if ultimo is None:
            print("[ForjaDev] Nenhum backup prévio encontrado. Disparando backup inicial...")
            gerar_zip_backup()
            return

        horas = (time.time() - ultimo) / 3600
        if horas > 24:
            print(f"[ForjaDev] Último backup há {horas:.1f}h. Disparando backup automático...")
            gerar_zip_backup()
    except Exception as e:
        print(f"[ForjaDev] Erro na verificação de gap inicial: {e}")


# ─────────────────────────────────────────────────────────
#  AGENDADOR
# ─────────────────────────────────────────────────────────

def iniciar_agendador_backup():
    global _scheduler_started

    # Django reloader trick — evita duplicidade em modo DEBUG
    if os.environ.get("RUN_MAIN", None) != "true" and settings.DEBUG:
        return

    if not _scheduler_started:
        import threading
        # Verifica gap em background após 5s do startup (sem travar o boot)
        t = threading.Timer(5, verificar_gap_na_inicializacao)
        t.daemon = True
        t.start()

        scheduler = BackgroundScheduler()
        scheduler.add_job(verificar_rotina_backup, "cron", minute="*")
        scheduler.start()
        _scheduler_started = True
        print("[ForjaDev] Motor Temporal do Backup engajado.")
