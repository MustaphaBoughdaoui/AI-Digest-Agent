@echo off
echo ========================================
echo   Mini-Perplexity ACE Server
echo ========================================
echo.
echo Demarrage du serveur...
echo.
cd /d "%~dp0"
python -m uvicorn app.api:app --host 127.0.0.1 --port 8000
pause
