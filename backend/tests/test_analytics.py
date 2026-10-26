import numpy as np
import pandas as pd
from ml.analytics import add_moving_averages, volatility_score, yoy_change, haversine_km
from ml.forecast import forecast_series, backtest_mape


def _series(n=800):
    d = pd.date_range("2023-01-01", periods=n)
    y = 2000 + 300 * np.sin(np.arange(n) / 58) + np.random.default_rng(1).normal(0, 20, n)
    return pd.DataFrame({"arrival_date": d, "modal_price": y})


def test_ma_and_vol():
    df = add_moving_averages(_series())
    assert df["ma7"].notna().sum() > 700
    assert 0 < volatility_score(df["modal_price"]) < 5


def test_yoy_and_distance():
    assert yoy_change(_series()) is not None
    assert 1100 < haversine_km(28.71, 77.17, 19.07, 72.87) < 1200


def test_forecast_shape():
    out, model = forecast_series(_series(), model="arima")
    assert len(out) == 15 and (out["lower"] < out["upper"]).all()
    assert backtest_mape(_series(), model="arima") < 15
