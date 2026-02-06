@echo off
chcp 65001 >nul
title Bot de Publicações - Modo Contínuo (Opus)

echo.
echo ═══════════════════════════════════════════════════════════
echo   BOT DE PUBLICAÇÕES - MODO CONTÍNUO
echo   Versão Opus
echo ═══════════════════════════════════════════════════════════
echo.
echo   O bot ficará executando em loop.
echo   Pressione Ctrl+C para parar.
echo.
echo ═══════════════════════════════════════════════════════════
echo.

REM Verifica se Python está instalado
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python não encontrado!
    pause
    exit /b 1
)

REM Instala dependências se necessário
pip install -r requirements.txt -q

python bot.py --continuo

pause
