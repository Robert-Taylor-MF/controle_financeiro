@echo off
setlocal enabledelayedexpansion
color 0B
title Servidor - Controle Financeiro

echo ==============================================================
echo       Controle Financeiro Gamificado - Motor de Forja
echo ==============================================================
echo.

REM --- ETAPA 1: LOCALIZAR MOTOR DE COMBUSTAO (PYTHON 3.13) ---
set "PYTHON_EXE="

REM 1. Tenta usar o Python Launcher para a versao 3.13
py -3.13 --version >nul 2>&1
if !errorlevel! equ 0 (
    for /f "tokens=*" %%i in ('py -3.13 -c "import sys; print(sys.executable)"') do set "PYTHON_EXE=%%i"
)

REM 2. Se nao encontrou, tenta buscar em instalacao local previa
if not defined PYTHON_EXE (
    if exist "%CD%\python_dist\python.exe" set "PYTHON_EXE=%CD%\python_dist\python.exe"
)

REM 3. Se ainda nao encontrou, prepara a Forja do Python
if not defined PYTHON_EXE (
    color 0E
    echo [INFO] Motor 3.13 nao detectado. Preparando instalacao isolada...
    
    set "INSTALLER=python_version\python-3.13.4.exe"
    if "%PROCESSOR_ARCHITECTURE%"=="AMD64" set "INSTALLER=python_version\python-3.13.4-amd64.exe"
    
    if exist "!INSTALLER!" (
        echo [INFO] Iniciando instalador: !INSTALLER!
        echo [AVISO] Instalacao sera realizada em: !CD!\python_dist
        echo [AVISO] Por favor, aguarde a conclusao silenciosa...
        
        start /wait "" "!INSTALLER!" /passive InstallAllUsers=0 PrependPath=0 TargetDir="%CD%\python_dist" Include_test=0 Include_doc=0
        
        if exist "%CD%\python_dist\python.exe" (
            set "PYTHON_EXE=%CD%\python_dist\python.exe"
            echo [OK] Motor instalado com sucesso em [python_dist].
        ) else (
            color 0C
            echo [ERRO] Falha na instalacao automatica.
            pause & exit /b
        )
    ) else (
        color 0C
        echo [ERRO CRITICO] Instalador nao encontrado em: !INSTALLER!
        pause & exit /b
    )
)

echo [OK] Motor de Combustao (Python 3.13) localizado:
echo      !PYTHON_EXE!
echo.

REM --- ETAPA 2: FORJAR AMBIENTE TEMPORAL (VENV) ---
if not exist venv\Scripts\activate.bat (
    echo [INFO] Primeira execucao detectada! Forjando a magia do ambiente...
    "!PYTHON_EXE!" -m venv venv
    if !errorlevel! neq 0 (
        echo [ERRO] Falha ao criar ambiente virtual com !PYTHON_EXE!
        pause & exit /b
    )
    call venv\Scripts\activate.bat
    echo [INFO] Instalando bibliotecas necessarias...
    python -m pip install --upgrade pip
    pip install -r requirements.txt
) else (
    call venv\Scripts\activate.bat
)

:SERVER_LOOP
REM --- ETAPA 3: VALIDACAO DO ESCUDO (VIRTUAL ENV CHECK) ---
python -c "import sys, os; sys.exit(0 if os.path.normpath(sys.prefix).lower().startswith(os.path.normpath(r'%CD%\venv').lower()) else 1)" >nul 2>&1
if !errorlevel! neq 0 (
    color 0C
    echo [ERRO] O Escudo de Protecao [venv] nao esta ativo corretamente!
    echo        O script esta tentando usar o Python global. Abortando.
    pause & exit /b
)

REM Verifica bibliotecas (Waitress/Django) de forma robusta
python -c "import waitress, django" >nul 2>&1 || (
    echo [INFO] Detectadas bibliotecas faltantes. Restaurando ambiente...
    python -m pip install --upgrade pip
    pip install -r requirements.txt
)

echo [OK] Ambiente ativado e validado. Preparando estruturas...

REM Garantia de Integridade
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

REM Inicia o Servidor e aguarda finalizacao
python -m waitress --port=8000 setup.wsgi:application

REM --- ETAPA FINAL: VERIFICAR SINAL DE SINCRONIA ---
if exist .update_pending (
    color 0E
    echo.
    echo ==============================================================
    echo [SINCRONIA] Iniciando a Grande Sincronia Arvana...
    echo ==============================================================
    
    timeout /t 2 >nul
    git pull origin main
    
    if !errorlevel! equ 0 (
        echo [OK] Fragmentos recuperados. Atualizando bibliotecas e runas...
        pip install -r requirements.txt
        python manage.py migrate
        del .update_pending
        echo [OK] Sincronia Completa! Reiniciando o Motor...
        timeout /t 2 >nul
        goto SERVER_LOOP
    ) else (
        color 0C
        echo [ERRO] Falha na Sincronia! Verifique sua conexao ou conflitos locais.
        del .update_pending
        pause
    )
)
