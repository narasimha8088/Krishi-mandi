@echo off
cd /d "%~dp0backend"
if not exist .venv\Scripts\activate.bat (echo Run START.bat once first. & pause & exit /b 1)
call .venv\Scripts\activate.bat
python -m pytest -q
pause
