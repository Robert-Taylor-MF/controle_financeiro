@echo off
color 0B
title Servidor - Controle Financeiro

echo ==============================================================
echo       Inicializando o Sistema Controle Financeiro
echo ==============================================================
echo.

REM Verifica se o ambiente virtual existe, se não, pede para executar o install.bat
if not exist venv\Scripts\activate.bat (
    color 0C
    echo [ERRO] Ambiente virtual (venv) nao encontrado. 
    echo Por favor, execute o 'install.bat' primeiro para instalar e preparar o projeto.
    pause
    exit /b
)

REM Ativa venv e executa em produção usando Waitress
call venv\Scripts\activate.bat
echo [OK] Ambiente virtual ativado.
echo [SERVER] Servidor de producao (Waitress) rodando em http://localhost:8000
echo.
echo Pressione CTRL+C na janela para interromper e parar o servidor.
echo.

REM Execute o WSGI do Django via waitress-serve
waitress-serve --port=8000 setup.wsgi:application
