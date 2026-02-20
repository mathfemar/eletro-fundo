@echo off
cd /d "%~dp0"

if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
)

set PYTHONPATH=%~dp0src;%PYTHONPATH%

python -m uvicorn app.api.main:app --host 0.0.0.0 --port 8528 --reload
pause
