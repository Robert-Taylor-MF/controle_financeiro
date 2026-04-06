@echo off
color 0A
title Instalador - Controle Financeiro

echo ==============================================================
echo       Instalacao e Configuracao - Controle Financeiro
echo ==============================================================
echo.

REM Verifica se o Python esta instalado
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERRO] Python nao encontrado. Por favor, instale o Python antes de continuar.
    echo Baixe em: https://www.python.org/downloads/
    pause
    exit /b
)

REM Criacao do ambiente virtual
echo [1/4] Criando o ambiente virtual venv...
if exist venv (
    echo [INFO] Ambiente virtual ja existe. Pulando etapa.
) else (
    python -m venv venv
)

REM Ativando o ambiente virtual e instalando as dependencias
echo [2/4] Instalando dependencias...
call venv\Scripts\activate.bat
python -m pip install --upgrade pip >nul
pip install -r requirements.txt

REM Executando as migrations
echo [3/4] Preparando o banco de dados inicial (migrations)...
python manage.py makemigrations
python manage.py migrate

REM Instrui o usuario a criar o super usuario
echo [4/4] Finalizando a instalacao da base...
echo.
echo ==============================================================
echo Instalacao concluida com sucesso!
echo ==============================================================
echo.
echo O ambiente esta pronto para forjar sua financa gamificada.
echo O usuario master podera ser criado abrindo sua interface web no primeiro acesso.
echo.
echo Tudo pronto! Para iniciar o servidor em mode de producao (Waitress), execute run.bat.
pause
