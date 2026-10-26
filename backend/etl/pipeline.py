"""ETL: Agmarknet (data.gov.in) or CSV -> clean -> database.

Usage (from the backend folder):
  python -m etl.pipeline --synthetic                                       # offline demo data
  python -m etl.pipeline --api-key KEY --commodities Onion Tomato Rice     # live government data
  python -m etl.pipeline --csv kaggle_agmarknet.csv                        # historical backfill
"""
import argparse
import numpy as np
import pandas as pd
import requests
from sqlalchemy import select, insert, delete
from app.db import engine
from app.models import init_db, markets, mandi_prices
from etl.mandi_geo import MANDIS

RESOURCE = "https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070"
COLS = ["state", "district", "market", "commodity", "variety", "arrival_date",
        "min_price", "max_price", "modal_price"]


# ---------- Extract ----------
def fetch_api(api_key: str, commodity: str, page_size: int = 500, max_pages: int = 40) -> pd.DataFrame:
    rows = []
    for page in range(max_pages):
        r = requests.get(RESOURCE, params={
            "api-key": api_key, "format": "json", "limit": page_size,
            "offset": page * page_size, "filters[commodity]": commodity,
        }, timeout=30)
        r.raise_for_status()
        recs = r.json().get("records", [])
        if not recs:
            break
        rows += recs
    return pd.DataFrame(rows)


def read_csv(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    return df.rename(columns={"price_date": "arrival_date", "market_name": "market"})


# ---------- Transform ----------
def clean(df: pd.DataFrame) -> pd.DataFrame:
    df = df[[c for c in COLS if c in df.columns]].copy()
    df["arrival_date"] = pd.to_datetime(df["arrival_date"], dayfirst=True, errors="coerce")
    for c in ("min_price", "max_price", "modal_price"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=["arrival_date", "modal_price", "market", "commodity"])
    df = df[df["modal_price"] > 0]
    for c in ("market", "commodity", "state", "district"):
        if c in df:
            df[c] = df[c].astype(str).str.strip().str.title()
    df["market"] = df["market"].str.replace(r"\(.*?\)", "", regex=True).str.strip()  # "Lasalgaon(Niphad)" -> "Lasalgaon"
    # Winsorise data-entry errors per (market, commodity): clip to the 1st-99th percentile
    g = df.groupby(["market", "commodity"])["modal_price"]
    df["modal_price"] = df["modal_price"].clip(g.transform(lambda s: s.quantile(.01)),
                                               g.transform(lambda s: s.quantile(.99)))
    return df.drop_duplicates(["market", "commodity", "arrival_date"])


def synthetic(days: int = 900, seed: int = 7) -> pd.DataFrame:
    """Seasonal + trend + noise prices so the project runs without network access."""
    rng = np.random.default_rng(seed)
    dates = pd.date_range(end=pd.Timestamp.today().normalize(), periods=days)
    base = {"Onion": 1800, "Tomato": 2200, "Rice": 3100}
    amp = {"Onion": .35, "Tomato": .45, "Rice": .06}
    rows = []
    for name, dist, state, lat, lon in MANDIS:
        mk = rng.normal(1, .08)
        for crop, b in base.items():
            t = np.arange(days)
            season = 1 + amp[crop] * np.sin(2 * np.pi * (t - rng.integers(0, 60)) / 365)
            walk = np.cumsum(rng.normal(0, .012, days)) * (0.6 if crop == "Rice" else 1)
            p = b * mk * season * np.exp(walk - walk.mean()) * (1 + rng.normal(0, .015, days))
            rows.append(pd.DataFrame({"state": state, "district": dist, "market": name,
                                      "commodity": crop, "variety": "Other", "arrival_date": dates,
                                      "min_price": p * .9, "max_price": p * 1.1, "modal_price": p}))
    return pd.concat(rows)


# ---------- Load ----------
def _f(x):
    return None if pd.isna(x) else float(x)


def load(df: pd.DataFrame) -> int:
    init_db()
    geo = {m[0]: m for m in MANDIS}
    n = 0
    with engine.begin() as con:
        for market, g in df.groupby("market"):
            if market not in geo:
                continue  # no coordinates -> cannot be mapped (add it to etl/mandi_geo.py)
            _, dist, state, lat, lon = geo[market]
            row = con.execute(select(markets.c.id).where(markets.c.name == market, markets.c.state == state)).first()
            mid = row[0] if row else con.execute(
                insert(markets).values(name=market, district=dist, state=state, lat=lat, lon=lon)).inserted_primary_key[0]
            for crop, gc in g.groupby("commodity"):
                con.execute(delete(mandi_prices).where(
                    mandi_prices.c.market_id == mid, mandi_prices.c.commodity == crop,
                    mandi_prices.c.arrival_date.between(gc["arrival_date"].min().date(), gc["arrival_date"].max().date())))
                recs = [dict(market_id=mid, commodity=crop, arrival_date=r.arrival_date.date(),
                             variety=getattr(r, "variety", None), min_price=_f(getattr(r, "min_price", np.nan)),
                             max_price=_f(getattr(r, "max_price", np.nan)), modal_price=float(r.modal_price))
                        for r in gc.itertuples()]
                con.execute(insert(mandi_prices), recs)
                n += len(recs)
    return n


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--api-key"); ap.add_argument("--csv"); ap.add_argument("--synthetic", action="store_true")
    ap.add_argument("--commodities", nargs="*", default=["Onion", "Tomato", "Rice"])
    a = ap.parse_args()
    if a.synthetic:
        raw = synthetic()
    elif a.csv:
        raw = read_csv(a.csv)
    elif a.api_key:
        raw = pd.concat([fetch_api(a.api_key, c) for c in a.commodities])
    else:
        ap.error("choose one of --synthetic, --csv FILE or --api-key KEY")
    print(f"Loaded {load(clean(raw)):,} rows")
