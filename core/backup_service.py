import os
import shutil
import zipfile
import threading
import json
import time
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from django.conf import settings

# Garante que o scheduler inicie apenas uma vez, lidando com o reloader do Django
_scheduler_started = False

def set_backup_status(status, message):
    try:
        pasta_backups = os.path.join(settings.BASE_DIR, "backups")
        os.makedirs(pasta_backups, exist_ok=True)
        path = os.path.join(pasta_backups, "status.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"status": status, "message": message, "time": time.time()}, f)
    except Exception:
        pass

def gerar_zip_backup():
    """Lógica bruta para capturar o bd.sqlite3 e a pasta media e ejetar num zip"""
    set_backup_status("running", "Iniciando a forja de segurança...")
    
    # Nomes dos arquivos de origem
    db_path = os.path.join(settings.BASE_DIR, 'db.sqlite3')
    media_path = os.path.join(settings.BASE_DIR, 'media')
    
    # Prepara diretório de backup padrão do projeto
    backup_dir = os.path.join(settings.BASE_DIR, 'backups')
    os.makedirs(backup_dir, exist_ok=True)
    
    # Nome do arquivo gerado
    timestamp = datetime.now().strftime('%d-%m-%Y_%H-%M-%S')
    zip_filename = f"Forja_Backup_{timestamp}.zip"
    zip_path = os.path.join(backup_dir, zip_filename)
    
    # Zippando...
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        if os.path.exists(db_path):
            zipf.write(db_path, 'db.sqlite3')
            
        if os.path.exists(media_path):
            for root, dirs, files in os.walk(media_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    # Relativo para manter a estrutura media/dentro-do-zip
                    arcname = os.path.relpath(file_path, settings.BASE_DIR)
                    zipf.write(file_path, arcname)
                    
    # Checa o diretorio customizado do usuário
    from core.models import MestreSeguranca
    try:
        ms = MestreSeguranca.objects.first()
        if ms and ms.diretorio_backup:
            target_dir = ms.diretorio_backup
            if os.path.exists(target_dir) and os.path.isdir(target_dir):
                shutil.copy2(zip_path, target_dir)
    except Exception as e:
        print(f"Erro ao copiar para diretório customizado: {e}")

    return zip_path

def verificar_rotina_backup():
    """Função agendada que roda a cada 1 minuto checando se é a hora do Oráculo"""
    try:
        from core.models import MestreSeguranca
        ms = MestreSeguranca.objects.first()
        if not ms or ms.frequencia_backup == 'MANUAL' or not ms.horario_backup:
            return
            
        agora = datetime.now()
        
        # Verifica se estamos na Hora e Minuto corretos (A rotina roda a cada min, então baterá apenas 1 vez)
        if agora.hour == ms.horario_backup.hour and agora.minute == ms.horario_backup.minute:
            
            pode_rodar = False
            
            if ms.frequencia_backup == 'DIARIO':
                pode_rodar = True
            elif ms.frequencia_backup == 'SEMANAL' and ms.dias_backup:
                # dias da semana no Python: 0=Seg, 1=Ter, ..., 6=Dom
                dow = str(agora.weekday())
                dias_configurados = [d.strip() for d in ms.dias_backup.split(',')]
                if dow in dias_configurados:
                    pode_rodar = True
                    
            if pode_rodar:
                print(f"[ForjaDev] Iniciando rotina de Backup Automático ({agora.strftime('%H:%M')})...")
                gerar_zip_backup()
                
    except Exception as e:
        print(f"[ForjaDev] Falha na verificação de backup: {e}")


def iniciar_agendador_backup():
    global _scheduler_started
    
    # Previne duplicidade caso o runserver seja invocado em multiplas threads
    if os.environ.get('RUN_MAIN', None) != 'true' and settings.DEBUG:
        # Django reloader trick
        return

    if not _scheduler_started:
        scheduler = BackgroundScheduler()
        # Dispara todo minuto no segundo 0 para checar as horas cravadas
        scheduler.add_job(verificar_rotina_backup, 'cron', minute='*')
        scheduler.start()
        _scheduler_started = True
        print("[ForjaDev] Motor Temporal do Backup engajado.")
