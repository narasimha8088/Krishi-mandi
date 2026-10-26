@echo off
cd /d "%~dp0backend"
del /q data\krishimandi.db 2>nul
echo Database removed. Run START.bat to rebuild it with demo data.
pause
