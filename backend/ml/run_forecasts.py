"""Forecast every (market, commodity) 15 days ahead, backtest it, and cache results in `forecasts`."""
import pandas as pd
from sqlalchemy import insert, delete
from app.db import engine
from app.models import init_db, forecasts
from ml.forecast import forecast_series, backtest_mape


def main():
    init_db()
    prices = pd.read_sql("SELECT market_id, commodity, arrival_date, modal_price FROM mandi_prices", engine,
                         parse_dates=["arrival_date"])
    groups = [(k, g) for k, g in prices.groupby(["market_id", "commodity"]) if len(g) >= 120]
    for i, ((mid, crop), g) in enumerate(groups, 1):
        fc, model = forecast_series(g)
        mape = round(backtest_mape(g), 2)
        recs = [dict(market_id=int(mid), commodity=crop, target_date=r.target_date, yhat=float(r.yhat),
                     lower=float(r.lower), upper=float(r.upper), model=model, mape=mape) for r in fc.itertuples()]
        with engine.begin() as con:
            con.execute(delete(forecasts).where(forecasts.c.market_id == int(mid), forecasts.c.commodity == crop))
            con.execute(insert(forecasts), recs)
        print(f"[{i}/{len(groups)}] {crop:7s} market {mid:<3d} {model:6s} backtest error {mape:.1f}%", flush=True)


if __name__ == "__main__":
    main()
