@echo off
chcp 65001 >nul
title Teste de Configuração - Bot Publicações (Opus)

echo.
echo ═══════════════════════════════════════════════════════════
echo   TESTE DE CONFIGURAÇÃO - Bot de Publicações
echo   Versão Opus
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
python testar_configuracao.py

pause
