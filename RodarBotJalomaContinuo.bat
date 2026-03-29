@echo off
title Bot de Publicacoes - Modo Jaloma Continuo

echo.
echo ============================================================
echo   BOT DE PUBLICACOES - MODO JALOMA CONTINUO
echo ============================================================
echo.
echo O bot ficara executando em loop.
echo Pressione Ctrl+C para parar.
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo Python nao encontrado.
    pause
    exit /b 1
)

echo Verificando dependencias...
pip install -r requirements.txt -q

echo.
echo Iniciando bot Jaloma em modo continuo...
echo.

python bot_jaloma.py --continuo

pause
