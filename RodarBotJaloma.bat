@echo off
title Bot de Publicacoes - Modo Jaloma

echo.
echo ============================================================
echo   BOT DE PUBLICACOES - MODO JALOMA
echo ============================================================
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
echo Iniciando bot Jaloma...
echo.

python bot_jaloma.py

pause
