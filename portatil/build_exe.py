import os
import sys
import subprocess
import shutil

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PORTATIL_DIR = os.path.join(BASE_DIR, 'portatil')
ENTRY_POINT = os.path.join(PORTATIL_DIR, 'desktop_app.py')
DIST_DIR = os.path.join(PORTATIL_DIR, 'dist')
BUILD_DIR = os.path.join(PORTATIL_DIR, 'build')

def build():
    print("==========================================================")
    print("       FORJANDO EXECUTÁVEL PORTÁTIL (PyInstaller)         ")
    print("==========================================================")
    print(f"Diretório Raiz: {BASE_DIR}")
    print(f"Ponto de Entrada: {ENTRY_POINT}")
    print()

    # Separação de dados com delimitador correspondente ao OS (;) no Windows
    sep = ';' if sys.platform.startswith('win') else ':'

    ICON_PATH = os.path.join(PORTATIL_DIR, 'app_icon.ico')

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name=MoneyQuest",
        f"--icon={ICON_PATH}",
        "--noconsole",          # Oculta a janela preta do terminal CMD
        "--onedir",             # Pasta portátil com binários organizados
        "--noconfirm",          # Sobrescreve a pasta de saída sem confirmação
        "--clean",              # Limpa arquivos temporários de compilações anteriores


        f"--distpath={DIST_DIR}",
        f"--workpath={BUILD_DIR}",
        f"--add-data={os.path.join(BASE_DIR, 'core', 'templates')}{sep}{os.path.join('core', 'templates')}",
        f"--add-data={os.path.join(BASE_DIR, 'core', 'static')}{sep}{os.path.join('core', 'static')}",
        f"--add-data={os.path.join(BASE_DIR, 'version.txt')}{sep}.",
        "--collect-all=core",
        "--hidden-import=waitress",
        "--hidden-import=setup.wsgi",
        "--hidden-import=setup.urls",
        "--hidden-import=setup.settings",
        "--hidden-import=core.apps",
        "--hidden-import=core.middleware",
        "--hidden-import=core.context_processors",
        "--hidden-import=core.backup_service",
        "--hidden-import=core.services",
        "--hidden-import=core.forms",
        "--hidden-import=core.urls",
        "--hidden-import=core.views",
        "--hidden-import=core.models",
        "--hidden-import=django.contrib.admin",
        "--hidden-import=django.contrib.auth",
        "--hidden-import=django.contrib.contenttypes",
        "--hidden-import=django.contrib.sessions",
        "--hidden-import=django.contrib.messages",
        "--hidden-import=django.contrib.staticfiles",
        ENTRY_POINT
    ]


    print("[INFO] Executando PyInstaller...")
    result = subprocess.run(cmd, cwd=BASE_DIR)

    if result.returncode == 0:
        exe_path = os.path.join(DIST_DIR, 'MoneyQuest', 'MoneyQuest.exe')
        print()
        print("==========================================================")
        print(" [OK] EXECUTÁVEL PORTÁTIL GERADO COM SUCESSO!")
        print(f" Local: {exe_path}")
        print("==========================================================")

    else:
        print()
        print("==========================================================")
        print(" [ERRO] FALHA NA COMPILAÇÃO DO EXECUTÁVEL.")
        print("==========================================================")

if __name__ == '__main__':
    build()
