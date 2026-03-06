@echo off
setlocal
cd /d "%~dp0frontend"

if not exist "node_modules" (
  echo Dependencias nao encontradas. Executando npm install...
  call npm install
  if errorlevel 1 exit /b 1
)

call npm run dev
