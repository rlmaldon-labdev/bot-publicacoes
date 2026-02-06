@echo off
chcp 65001 >nul
title Bot de Publicações Jurídicas (Opus)

echo.
echo ═══════════════════════════════════════════════════════════
echo   BOT DE PUBLICAÇÕES JURÍDICAS - Versão Opus
echo ═══════════════════════════════════════════════════════════
echo.

REM Verifica se Python está instalado
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python não encontrado!
    echo    Instale Python 3.10+ em: https://www.python.org/downloads/
    pause
    exit /b 1
)

REM Instala dependências se necessário
echo 📦 Verificando dependências...
pip install -r requirements.txt -q

echo.
echo 🚀 Iniciando bot...
echo.

python bot.py

pause
