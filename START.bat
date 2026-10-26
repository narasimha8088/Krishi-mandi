@echo off
setlocal EnableExtensions
title Krishi-Mandi
cd /d "%~dp0backend"
if errorlevel 1 goto :nofolder
if not exist app\main.py goto :nofolder

rem ---------- find Python ----------
set "PY="
for %%V in (3.12 3.13 3.14 3.11 3.10) do (
  if not defined PY (
    py -%%V -c "import sys" >nul 2>nul && set "PY=py -%%V"
  )
)
if defined PY goto :havepy
python -c "import sys" >nul 2>nul && set "PY=python"
if not defined PY goto :nopython

:havepy
%PY% -c "import sys;sys.exit(0 if sys.version_info>=(3,10) else 1)"
if errorlevel 1 goto :oldpython
%PY% -c "import sys;sys.exit(0 if sys.maxsize>2**32 else 1)"
if errorlevel 1 goto :py32
echo Using:
%PY% --version

rem ---------- virtual environment ----------
if exist .venv\Scripts\python.exe goto :venv_ok
echo [1/4] Creating virtual environment...
%PY% -m venv .venv
if errorlevel 1 goto :venvfail
:venv_ok
call .venv\Scripts\activate.bat

rem ---------- packages ----------
if exist .venv\deps_installed.txt goto :deps_ok
echo [2/4] Installing packages. First run only, takes a few minutes...
set "PIPARGS=--disable-pip-version-check --retries 3 --timeout 40"
if exist wheels\*.whl goto :offline
goto :online

:offline
echo Found a wheels folder. Installing from it without internet...
python -m pip install %PIPARGS% --no-index --find-links=wheels -r requirements.txt
if not errorlevel 1 goto :verify
echo Offline install did not work. Trying the internet instead.

:online
echo Attempt 1 of 3: normal install...
python -m pip install %PIPARGS% -r requirements.txt
if not errorlevel 1 goto :verify
echo.
echo Attempt 2 of 3: using the Windows certificate store...
python -m pip install %PIPARGS% --use-feature=truststore -r requirements.txt
if not errorlevel 1 goto :verify
echo.
echo Attempt 3 of 3: relaxed certificate check for the Python package servers only...
python -m pip install %PIPARGS% --trusted-host pypi.org --trusted-host files.pythonhosted.org -r requirements.txt
if not errorlevel 1 goto :verify
goto :netfail

:verify
python -c "import fastapi, uvicorn, pandas, numpy, statsmodels, sqlalchemy"
if errorlevel 1 goto :importfail
echo ok> .venv\deps_installed.txt
:deps_ok

rem ---------- data and forecasts ----------
if exist data\krishimandi.db goto :datadone
echo [3/4] Loading demo price data...
python -m etl.pipeline --synthetic
if errorlevel 1 goto :datafail
echo Training forecast models. First run only, about a minute...
python -m ml.run_forecasts
if errorlevel 1 goto :datafail
:datadone

rem ---------- start the server ----------
set "PORT=8000"
:findport
netstat -ano | findstr /R /C:":%PORT% .*LISTENING" >nul
if errorlevel 1 goto :portok
set /a PORT+=1
if %PORT% GTR 8010 goto :noport
goto :findport
:portok
echo.
echo [4/4] Starting Krishi-Mandi at http://localhost:%PORT%
echo Keep this window open while you use it. Press Ctrl+C to stop.
start "" /min cmd /c "timeout /t 5 /nobreak >nul & start http://localhost:%PORT%"
python -m uvicorn app.main:app --port %PORT%
echo.
echo The server has stopped.
pause
goto :eof

rem ---------- error messages ----------
:nofolder
echo Could not find the backend folder.
echo Extract the whole zip first (right-click, Extract All), then run START.bat from inside the extracted folder.
pause
exit /b 1

:nopython
echo Python was not found on this computer.
echo Install Python 3.12 from https://www.python.org/downloads/
echo and tick "Add python.exe to PATH" on the first screen of the installer.
echo Then close this window, open a new one and run START.bat again.
pause
exit /b 1

:oldpython
echo Your Python is older than 3.10. Install Python 3.12 from https://www.python.org/downloads/
pause
exit /b 1

:py32
echo This is 32-bit Python. Install the 64-bit version of Python 3.12 from https://www.python.org/downloads/
pause
exit /b 1

:venvfail
echo Could not create the virtual environment.
echo Reinstall Python from python.org with the default options, then run START.bat again.
pause
exit /b 1

:netfail
echo.
echo ------------------------------------------------------------
echo The packages could not be downloaded. This is a network or certificate problem.
echo Try, in this order:
echo   1. Connect to your phone hotspot and run START.bat again.
echo   2. Pause your antivirus web or HTTPS scanning and switch off any VPN.
echo   3. Run CHECK_SYSTEM.bat and read its result.
echo   4. See SETUP_GUIDE.txt, section "If the download keeps failing".
echo ------------------------------------------------------------
pause
exit /b 1

:importfail
echo.
echo The packages installed but could not be loaded. If you see "DLL load failed" above,
echo install the Microsoft Visual C++ Redistributable (x64) from https://aka.ms/vs/17/release/vc_redist.x64.exe
echo then delete the folder backend\.venv and run START.bat again.
pause
exit /b 1

:datafail
echo.
echo Loading the data failed. Read the message above.
if exist data\krishimandi.db del /q data\krishimandi.db
pause
exit /b 1

:noport
echo No free port between 8000 and 8010. Close other programs or restart the computer.
pause
exit /b 1
