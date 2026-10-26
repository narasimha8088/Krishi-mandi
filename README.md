# Krishi-Mandi: Smart Market Intelligence and Dynamic Pricing Dashboard

Helps farmers decide **which mandi to sell at, and on which day**, using 15-day price forecasts,
transport cost and price-swing risk.

## Run it (Windows)

Step-by-step: **OPEN_IN_VSCODE.txt** (VS Code) or **SETUP_GUIDE.txt** (plain CMD, with troubleshooting).

1. Install Python 3.10 or newer (3.12 recommended) and tick **Add python.exe to PATH**.
2. Right-click the zip, **Extract All**. Open the extracted folder in VS Code (File, Open Folder), or type `cmd` in the File Explorer address bar.
3. Run `CHECK_SYSTEM.bat`, then `START.bat`. (In PowerShell use `.\START.bat`.)

The first run installs packages, loads demo data and trains forecasts (a few minutes), then opens **http://localhost:8000**.
macOS / Linux: `bash START.sh`.

Other scripts: `RUN_TESTS.bat`, `LOAD_REAL_DATA.bat YOUR_KEY`, `RESET_DATA.bat`.

## Folder layout

    Krishi-Mandi/
      START.bat / START.sh        one-command launchers
      CHECK_SYSTEM.bat            diagnoses Python, internet and certificate problems
      OPEN_IN_VSCODE.txt          how to open and run the project in VS Code
      SETUP_GUIDE.txt             step-by-step setup and troubleshooting
      .vscode/                    VS Code tasks, debugger and settings
      tools/check_system.py       the checker used by CHECK_SYSTEM.bat
      backend/
        etl/pipeline.py           Extract (API / CSV / synthetic), clean, load
        etl/mandi_geo.py          mandi coordinates
        ml/forecast.py            Prophet (if installed) or ARIMA, 15-day horizon, backtest
        ml/analytics.py           moving averages, volatility, YoY, sell score
        ml/run_forecasts.py       forecast every market and crop, store results
        app/main.py               FastAPI endpoints, also serves the web UI
        app/models.py, db.py      tables; SQLite by default, PostgreSQL via DATABASE_URL
        tests/                    pytest
      web/index.html              React + Tailwind + Leaflet map + Plotly charts (no build step)
      docker/                     optional PostgreSQL stack
      demo/offline-demo.html      standalone demo, simulated data, no server needed

## How it works

- **ETL:** pulls Agmarknet data from data.gov.in (or a Kaggle CSV for history), parses dates, removes bad rows,
  clips outliers per market and crop, and loads into the database.
- **Forecasting:** a 15-day forecast with an 80% range for each market and crop, plus a backtest on the
  last 15 known days. ARIMA adds damped recent momentum so forecasts can rise or fall.
- **Descriptive analytics:** 7 and 30-day moving averages, volatility score (std-dev of daily % change over 30 days),
  and 7-day-average change versus a year earlier.
- **Sell score:** `net = forecast price - transport_cost * km - risk * volatility` in Rs per quintal.
  The best date is the day with the highest net price. Transport and risk are adjustable in the UI.

## API (docs at http://localhost:8000/docs)

`/api/crops` `/api/markets?crop=` `/api/history?crop=&market_id=` `/api/forecast?crop=&market_id=`
`/api/best-market?crop=&lat=&lon=&transport=&risk=`

## Notes

- Demo prices are simulated. Backtest errors on them are not a claim about real-world accuracy.
- The page loads React, Tailwind, Leaflet, Plotly and map tiles from the internet.
- Optional: `pip install -r backend/requirements-optional.txt` for Prophet or PostgreSQL (`DATABASE_URL`).



---

## Project Screenshots

### 1. Best Places to Sell
![Best Places to Sell](screenshots/Best%20places%20to%20sell%20from%20your%20farm.png)

### 2. Onion Price Dashboard
![Onion Dashboard](screenshots/Complete%20dashboard%20%E2%80%94%20Onion%20at%20Ahmedabad.png)

### 3. Rice Price Dashboard
![Rice Dashboard](screenshots/Complete%20dashboard%20%E2%80%94%20Rice%20at%20Ahmedabad.png)

### 4. Tomato Price Dashboard
![Tomato Dashboard](screenshots/Complete%20dashboard%20%E2%80%94%20Tomato%20at%20Ahmedabad.png)

### 5. Price Map
![Krishi-Mandi Price Map](screenshots/Krishi-Mandi%20price%20map.png)

### 6. Price History and 15-Day Forecast
![Price Forecast](screenshots/Price%20history%20and%2015-day%20forecast%20graph.png)

### 7. Tomato Analytics at Hubli
![Tomato Analytics at Hubli](screenshots/Tomato%20analytics%20at%20Hubli.png)
