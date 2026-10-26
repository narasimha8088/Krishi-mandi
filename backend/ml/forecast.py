"""15-day price forecasting. Prophet if installed, otherwise ARIMA. Both are backtested on a 15-day holdout."""
import itertools
import warnings
import numpy as np
import pandas as pd

warnings.simplefilter("ignore")
HORIZON = 15
TRAIN_DAYS = 540   # use the most recent ~18 months


def _prophet(df: pd.DataFrame, horizon: int):
    from prophet import Prophet
    m = Prophet(weekly_seasonality=True, yearly_seasonality=len(df) > 400,
                daily_seasonality=False, interval_width=0.8)
    m.fit(df.rename(columns={"arrival_date": "ds", "modal_price": "y"})[["ds", "y"]])
    f = m.predict(m.make_future_dataframe(periods=horizon)).tail(horizon)
    return f["ds"].dt.date.values, f["yhat"].values, f["yhat_lower"].values, f["yhat_upper"].values


def _arima(df: pd.DataFrame, horizon: int):
    from statsmodels.tsa.arima.model import ARIMA
    warnings.simplefilter("ignore")
    y = df.set_index("arrival_date")["modal_price"].asfreq("D").interpolate()
    best, best_aic = None, np.inf
    for p, q in itertools.product(range(3), range(2)):   # small AIC grid, d=1
        try:
            res = ARIMA(y, order=(p, 1, q)).fit()
            if res.aic < best_aic:
                best, best_aic = res, res.aic
        except Exception:
            continue
    fc = best.get_forecast(horizon)
    ci = fc.conf_int(alpha=0.2)
    # ARIMA(d=1) is flat without drift. Add damped recent momentum (mean of last 30 daily changes,
    # decaying 7% a day) so the forecast can rise or fall and a best sell day exists.
    shift = y.diff().tail(30).mean() * np.cumsum(0.93 ** np.arange(1, horizon + 1))
    return (pd.date_range(y.index[-1] + pd.Timedelta(days=1), periods=horizon).date,
            fc.predicted_mean.values + shift, ci.iloc[:, 0].values + shift, ci.iloc[:, 1].values + shift)


def forecast_series(df: pd.DataFrame, horizon: int = HORIZON, model: str = "auto"):
    """df: columns arrival_date, modal_price. Returns (DataFrame, model name)."""
    df = df[["arrival_date", "modal_price"]].dropna().sort_values("arrival_date").tail(TRAIN_DAYS).copy()
    df["arrival_date"] = pd.to_datetime(df["arrival_date"])
    runners = {"prophet": _prophet, "arima": _arima}
    order = ["prophet", "arima"] if model == "auto" else [model]
    errors = []
    for name in order:
        try:
            dates, yhat, lo, hi = runners[name](df, horizon)
            return pd.DataFrame({"target_date": dates, "yhat": yhat, "lower": lo, "upper": hi}), name
        except Exception as e:           # Prophet missing or failing -> try next model
            errors.append(f"{name}: {e}")
    raise RuntimeError("; ".join(errors))


def backtest_mape(df: pd.DataFrame, horizon: int = HORIZON, model: str = "auto") -> float:
    """Train on everything except the last `horizon` days, score against them."""
    df = df.sort_values("arrival_date")
    train, test = df.iloc[:-horizon], df.iloc[-horizon:]
    pred, _ = forecast_series(train, horizon, model)
    y, yh = test["modal_price"].values, pred["yhat"].values[: len(test)]
    return float(np.mean(np.abs((y - yh) / y)) * 100)
