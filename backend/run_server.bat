@echo off
cd /d "%~dp0"

set "PY=%LocalAppData%\Programs\Python\Python312\python.exe"
where python >nul 2>&1
if %ERRORLEVEL%==0 (
  set "PY=python"
)

echo Starting ledger platform on http://0.0.0.0:8000
echo Open http://127.0.0.1:8000 on this PC, or http://^<this-PC-IP^>:8000 from LAN.
"%PY%" -m uvicorn app.main:app --host 0.0.0.0 --port 8000
pause
