@echo off
rem Usage: LOAD_REAL_DATA.bat YOUR_DATA_GOV_IN_API_KEY
rem Free key: https://data.gov.in  (Register, then My Account, then API key)
if "%~1"=="" (echo Usage: LOAD_REAL_DATA.bat YOUR_API_KEY & pause & exit /b 1)
cd /d "%~dp0backend"
if not exist .venv\Scripts\activate.bat (echo Run START.bat once first. & pause & exit /b 1)
call .venv\Scripts\activate.bat
python -m etl.pipeline --api-key %~1 --commodities Onion Tomato Rice
python -m ml.run_forecasts
echo Done. Run START.bat to view the dashboard.
pause
