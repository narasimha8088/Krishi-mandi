"""Descriptive analytics: moving averages, volatility, YoY, and sell-score helpers."""
import numpy as np
import pandas as pd


def add_moving_averages(df: pd.DataFrame, col: str = "modal_price") -> pd.DataFrame:
    out = df.sort_values("arrival_date").copy()
    out["ma7"] = out[col].rolling(7, min_periods=3).mean()
    out["ma30"] = out[col].rolling(30, min_periods=10).mean()
    return out


def volatility_score(prices: pd.Series, window: int = 30) -> float:
    """Std-dev of daily % change over the last `window` days, x100.
    ~0-1 = calm market, 1-3 = normal, >3 = jumpy."""
    r = prices.pct_change().dropna().tail(window)
    return float(r.std() * 100) if len(r) > 3 else float("nan")


def yoy_change(df: pd.DataFrame, col: str = "modal_price") -> float | None:
    """% change of the latest 7-day mean vs the same 7-day window a year earlier."""
    s = df.set_index("arrival_date")[col].sort_index()
    s.index = pd.to_datetime(s.index)
    end = s.index.max()
    now = s[end - pd.Timedelta(days=6): end].mean()
    ly_end = end - pd.DateOffset(years=1)
    ly = s[ly_end - pd.Timedelta(days=6): ly_end].mean()
    if np.isnan(now) or np.isnan(ly) or ly == 0:
        return None
    return float((now / ly - 1) * 100)


def haversine_km(lat1, lon1, lat2, lon2) -> float:
    r = 6371.0
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dphi, dl = p2 - p1, np.radians(lon2 - lon1)
    a = np.sin(dphi / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dl / 2) ** 2
    return float(2 * r * np.arcsin(np.sqrt(a)))


def net_sell_score(forecast_price, distance_km, volatility, transport_per_qtl_km=0.55, risk_lambda=18.0):
    """Expected price in Rs/qtl after transport cost and a volatility risk penalty."""
    return forecast_price - transport_per_qtl_km * distance_km - risk_lambda * (volatility or 0)
