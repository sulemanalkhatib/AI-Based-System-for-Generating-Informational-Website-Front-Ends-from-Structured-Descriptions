@echo off
title Website Generator v2
cd /d "%~dp0"

REM ============================================================================
REM  One-click launcher. First run auto-installs everything; later runs are fast.
REM  Requires: Python 3.12+ on PATH. (Node.js only needed if the built UI in
REM  frontend\dist is missing and has to be rebuilt.)
REM ============================================================================

REM --- 0) Python must be available ---
where python >nul 2>&1
if errorlevel 1 (
  echo.
  echo ERROR: Python was not found on PATH.
  echo Install Python 3.12+ from https://python.org ^(tick "Add to PATH"^) and re-run.
  echo.
  pause
  exit /b 1
)

REM --- 1) Install backend dependencies on first run ---
python -c "import fastapi, uvicorn, aiosqlite, openai, pydantic, dotenv, sse_starlette" >nul 2>&1
if errorlevel 1 (
  echo Installing Python dependencies ^(first run only, may take a minute^)...
  python -m pip install -r "%~dp0backend\requirements.txt"
  if errorlevel 1 (
    echo.
    echo ERROR: pip install failed. See the messages above.
    pause
    exit /b 1
  )
)

REM --- 2) Build the frontend if the built UI is missing ---
if not exist "%~dp0frontend\dist\index.html" (
  where npm >nul 2>&1
  if errorlevel 1 (
    echo.
    echo ERROR: The built UI ^(frontend\dist^) is missing and Node.js/npm was not found.
    echo Install Node.js 18+ from https://nodejs.org and re-run.
    echo.
    pause
    exit /b 1
  )
  echo Building the web UI ^(first run only, may take a minute^)...
  pushd "%~dp0frontend"
  if not exist node_modules ( call npm install )
  call npm run build
  popd
)

REM --- 3) Free port 8000 if a previous run is still holding it ---
cd /d "%~dp0backend"
for /f "tokens=5" %%p in ('netstat -ano ^| findstr "127.0.0.1:8000" ^| findstr "LISTENING"') do (
  echo Stopping a previous instance still on port 8000 ^(PID %%p^)...
  taskkill /F /PID %%p >nul 2>&1
)

REM --- 4) Open the browser as soon as the server answers ---
start "" cmd /c "curl --retry 60 --retry-delay 1 --retry-all-errors -s -o nul http://localhost:8000/ && start http://localhost:8000"

echo.
echo Starting Website Generator on http://localhost:8000   (press CTRL+C to stop)
echo When it opens: click Settings, enter your provider URL + API key, then Save.
echo.
python -m uvicorn app:app --port 8000

echo.
echo *** The server has stopped. If it closed right after starting, read the message above. ***
pause
