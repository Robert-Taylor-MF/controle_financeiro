@echo off
color 0B
title Servidor - Controle Financeiro

echo ==============================================================
echo       Controle Financeiro Gamificado - Motor de Forja
echo ==============================================================
echo.

REM Verifica Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    color 0C
    echo [ERRO CRITICO] O Python nao esta instalado no Windows!
    echo Baixe e instale pelo site: https://www.python.org/downloads/
    pause
    exit /b
)

REM Cria venv se nao existir
if not exist venv\Scripts\activate.bat (
    echo [INFO] Primeira execucao detectada! Forjando a magia do ambiente...
    python -m venv venv
    call venv\Scripts\activate.bat
    echo [INFO] Instalando bibliotecas (Pode demorar um pouco)...
    python -m pip install --upgrade pip >nul 2>&1
    pip install -r requirements.txt >nul 2>&1
) else (
    call venv\Scripts\activate.bat
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

waitress-serve --port=8000 setup.wsgi:application
