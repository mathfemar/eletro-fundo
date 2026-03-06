@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo Ambiente virtual nao encontrado em .venv
  exit /b 1
)

call ".venv\Scripts\activate.bat"
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
