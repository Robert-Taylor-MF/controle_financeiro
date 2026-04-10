@echo off
color 0B
title Servidor - Controle Financeiro

echo ==============================================================
echo       Controle Financeiro Gamificado - Motor de Forja
echo ==============================================================
echo.

setlocal enabledelayedexpansion

REM Verifica Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    color 0E
    echo [INFO] Python nao detectado. Preparando instalacao automatica (v3.13.4)...
    echo.
    set "PYTHON_INSTALLER=python_version\python-3.13.4.exe"
    if "%PROCESSOR_ARCHITECTURE%"=="AMD64" set "PYTHON_INSTALLER=python_version\python-3.13.4-amd64.exe"
    
    if exist "!PYTHON_INSTALLER!" (
        echo [INFO] Iniciando instalador: !PYTHON_INSTALLER!
        echo [AVISO] Por favor, aguarde a conclusao da instalacao.
        echo [IMPORTANTE] Estamos configurando para "Add Python to PATH" automaticamente.
        start /wait "" "!PYTHON_INSTALLER!" /passive InstallAllUsers=1 PrependPath=1
        echo.
        echo [OK] Instalacao concluida com sucesso!
        echo [AVISO] Voce precisa FECHAR este terminal e abrir o run.bat novamente para o Windows reconhecer o Python.
        pause
        exit /b
    ) else (
        color 0C
        echo [ERRO CRITICO] O Python nao esta instalado e o instalador nao foi encontrado em:
        echo !PYTHON_INSTALLER!
        echo.
        echo Baixe e instale manualmente pelo site: https://www.python.org/downloads/
        pause
        exit /b
    )
)

REM Cria ou Ativa venv
if not exist venv\Scripts\activate.bat (
    echo [INFO] Primeira execucao detectada! Forjando a magia do ambiente...
    python -m venv venv
    call venv\Scripts\activate.bat
    echo [INFO] Instalando bibliotecas, isso pode demorar um pouco...
    python -m pip install --upgrade pip
    pip install -r requirements.txt
) else (
    call venv\Scripts\activate.bat
)

REM Verifica se bibliotecas essenciais estao presentes
python -c "import waitress, django" >nul 2>&1 || (
    echo [INFO] Detectadas bibliotecas faltantes. Restaurando ambiente...
    python -m pip install --upgrade pip
    pip install -r requirements.txt
)

echo [OK] Ambiente ativado. Preparando estruturas...

REM Garantia de Integridade (Cria o banco e estáticos silenciosamente se ausentes)
python manage.py makemigrations >nul 2>&1
python manage.py migrate >nul 2>&1
python manage.py collectstatic --noinput >nul 2>&1

echo [OK] Tudo Pronto!
echo [SERVER] O Motor Temporal (Waitress) esta rodando em http://localhost:8000
echo.
echo Pressione CTRL+C para derrubar os escudos e parar o servidor.
echo ==============================================================

echo [OPEN] Abrindo Motor de Forja no navegador padrao...
start http://localhost:8000

python -m waitress --port=8000 setup.wsgi:application
