from pathlib import Path
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from app.db import engine
from app.models import init_db
from ml.analytics import add_moving_averages, volatility_score, yoy_change, haversine_km, net_sell_score

app = FastAPI(title="Krishi-Mandi API", version="1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET"], allow_headers=["*"])
init_db()


def _read(sql: str, **params) -> pd.DataFrame:
    return pd.read_sql(text(sql), engine, params=params)


def _prices(crop: str, market_id: int | None = None) -> pd.DataFrame:
    q = """SELECT p.market_id, m.name AS market, m.state, m.lat, m.lon, p.arrival_date, p.modal_price
           FROM mandi_prices p JOIN markets m ON m.id = p.market_id WHERE p.commodity = :c"""
    params = {"c": crop}
    if market_id:
        q += " AND p.market_id = :m"
        params["m"] = market_id
    df = _read(q, **params)
    df["arrival_date"] = pd.to_datetime(df["arrival_date"])
    return df


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/crops")
def crops():
    return _read("SELECT DISTINCT commodity FROM mandi_prices ORDER BY 1")["commodity"].tolist()


@app.get("/api/markets")
def markets(crop: str):
    """One row per mandi: latest price, 7-day change, volatility, YoY. Powers the map."""
    df = _prices(crop)
    if df.empty:
        raise HTTPException(404, f"No data for {crop}")
    out = []
    for mid, g in df.groupby("market_id"):
        g = g.sort_values("arrival_date")
        last = g["modal_price"].iloc[-1]
        wk = g["modal_price"].iloc[-8] if len(g) > 8 else g["modal_price"].iloc[0]
        yo = yoy_change(g)
        out.append(dict(market_id=int(mid), market=g["market"].iloc[0], state=g["state"].iloc[0],
                        lat=float(g["lat"].iloc[0]), lon=float(g["lon"].iloc[0]), price=round(last),
                        change_7d=round((last / wk - 1) * 100, 1),
                        volatility=round(volatility_score(g["modal_price"]), 2),
                        yoy=None if yo is None else round(yo, 1)))
    return out


@app.get("/api/history")
def history(crop: str, market_id: int, days: int = 180):
    df = add_moving_averages(_prices(crop, market_id)).tail(days).copy()
    df["arrival_date"] = df["arrival_date"].dt.strftime("%Y-%m-%d")
    df = df[["arrival_date", "modal_price", "ma7", "ma30"]].round(1)
    return df.astype(object).where(df.notna(), None).to_dict("records")


@app.get("/api/forecast")
def forecast(crop: str, market_id: int):
    df = _read("""SELECT target_date, yhat, lower, upper, model, mape FROM forecasts
                  WHERE commodity = :c AND market_id = :m ORDER BY target_date""", c=crop, m=market_id)
    if df.empty:
        raise HTTPException(404, "No forecast yet. Run: python -m ml.run_forecasts")
    return {"model": df["model"].iloc[0], "mape": float(df["mape"].iloc[0]),
            "points": df.drop(columns=["model", "mape"]).astype({"target_date": str}).round(1).to_dict("records")}


@app.get("/api/best-market")
def best_market(crop: str, lat: float, lon: float,
                transport: float = Query(0.55, ge=0), risk: float = Query(18.0, ge=0)):
    """Rank mandis by forecast net price (after transport + volatility risk) and suggest a sell date."""
    fc = _read("""SELECT f.market_id, m.name, m.state, m.lat, m.lon, f.target_date, f.yhat
                  FROM forecasts f JOIN markets m ON m.id = f.market_id WHERE f.commodity = :c""", c=crop)
    if fc.empty:
        raise HTTPException(404, f"No forecasts for {crop}")
    prices = _prices(crop)
    ranked = []
    for mid, g in fc.groupby("market_id"):
        vol = volatility_score(prices.loc[prices["market_id"] == mid].sort_values("arrival_date")["modal_price"])
        km = haversine_km(lat, lon, g["lat"].iloc[0], g["lon"].iloc[0])
        g = g.assign(net=[net_sell_score(p, km, vol, transport, risk) for p in g["yhat"]])
        best = g.loc[g["net"].idxmax()]
        ranked.append(dict(market_id=int(mid), market=g["name"].iloc[0], state=g["state"].iloc[0],
                           distance_km=round(km), best_date=str(best["target_date"]),
                           expected_price=round(best["yhat"]), net_price=round(best["net"]),
                           volatility=round(vol, 2)))
    return sorted(ranked, key=lambda r: -r["net_price"])


# Serve the web UI at http://localhost:8000 (must be registered after the API routes)
WEB = Path(__file__).resolve().parents[2] / "web"
if WEB.exists():
    app.mount("/", StaticFiles(directory=WEB, html=True), name="web")
