@echo off
echo ==============================================
echo Encerrando a versao atual (se estiver aberta)...
echo ==============================================
taskkill /IM MoneyQuest.exe /F 2>nul

echo.
echo ==============================================
echo Gerando o novo arquivo portatil...
echo Isso pode levar em torno de 1 minuto. Por favor aguarde.
echo ==============================================
call venv\Scripts\python.exe portatil\build_exe.py

echo.
echo ==============================================
echo Compilacao finalizada! O arquivo MoneyQuest.exe
echo foi atualizado na pasta portatil\dist\MoneyQuest
echo ==============================================
pause
