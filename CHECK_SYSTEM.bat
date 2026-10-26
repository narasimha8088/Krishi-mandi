@echo off
setlocal EnableExtensions
title Krishi-Mandi system check
cd /d "%~dp0"

set "PY="
for %%V in (3.12 3.13 3.14 3.11 3.10) do (
  if not defined PY (
    py -%%V -c "import sys" >nul 2>nul && set "PY=py -%%V"
  )
)
if defined PY goto :run
python -c "import sys" >nul 2>nul && set "PY=python"
if defined PY goto :run

echo Python was not found on this computer.
echo Install Python 3.12 from https://www.python.org/downloads/
echo and tick "Add python.exe to PATH" on the first screen of the installer.
pause
exit /b 1

:run
%PY% tools\check_system.py
echo.
pause
