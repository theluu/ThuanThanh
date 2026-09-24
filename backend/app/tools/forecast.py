"""Deterministic forecasting toolkit used by the Data Scientist agent.

All numbers in the final report come from here — the LLM only explains them.
"""
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from ..config import EXOG, TARGET

COLS = [TARGET, *EXOG]
MODELS = ["naive", "drift", "ridge_lag"]
Z80 = 1.2816  # 80% prediction interval
JKM_LAGS = 5


def preprocess(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Sort by date, forward-fill gaps (market holidays / missing quotes), back-fill leading NaNs."""
    df = df.sort_values("Date").reset_index(drop=True)
    missing = {c: int(df[c].isna().sum()) for c in COLS}
    clean = df.copy()
    clean[COLS] = clean[COLS].ffill().bfill()
    return clean, {"rows": len(df), "missing_before": missing, "method": "forward-fill then back-fill"}


def make_features(df: pd.DataFrame) -> pd.DataFrame:
    """Features for predicting day t's JKM log-return, built only from data up to t-1."""
    logp = np.log(df[COLS])
    ret = logp.diff()
    feats = pd.DataFrame(index=df.index)
    for lag in range(1, JKM_LAGS + 1):
        feats[f"jkm_ret_l{lag}"] = ret[TARGET].shift(lag)
    feats["jkm_dev_ma10"] = (df[TARGET] / df[TARGET].rolling(10).mean() - 1).shift(1)
    feats["jkm_vol10"] = ret[TARGET].rolling(10).std().shift(1)
    for c in EXOG:
        feats[f"{c}_ret_l1"] = ret[c].shift(1)
    return feats


def horizon_dates(last_date: pd.Timestamp, months: int = 1) -> list[pd.Timestamp]:
    """Business days from the month after `last_date` through the end of the `months`-th month ahead (1 Jan excluded)."""
    start = (last_date + pd.offsets.MonthBegin(1)).normalize()
    end = start + pd.offsets.MonthEnd(months)
    days = pd.bdate_range(start, end)
    return [d for d in days if not (d.month == 1 and d.day == 1)]


def metrics(actual: np.ndarray, pred: np.ndarray) -> dict:
    actual, pred = np.asarray(actual, float), np.asarray(pred, float)
    err = pred - actual
    return {
        "MAE": float(np.mean(np.abs(err))),
        "RMSE": float(np.sqrt(np.mean(err ** 2))),
        "MAPE": float(np.mean(np.abs(err) / np.abs(actual)) * 100),
    }


def _daily_sigma(df: pd.DataFrame, window: int = 120) -> float:
    return float(np.log(df[TARGET]).diff().tail(window).std())


def _ridge_forecast(df: pd.DataFrame, n: int) -> np.ndarray:
    feats = make_features(df)
    y = np.log(df[TARGET]).diff()
    mask = feats.notna().all(axis=1) & y.notna()
    model = make_pipeline(StandardScaler(), Ridge(alpha=10.0))
    model.fit(feats[mask], y[mask])

    # Recursive multi-step: append predicted JKM, hold exogenous vars flat (unknown future).
    hist = df[COLS].copy().reset_index(drop=True)
    preds = []
    for _ in range(n):
        hist = pd.concat([hist, hist.iloc[[-1]]], ignore_index=True)
        x = make_features(hist).iloc[[-1]]
        r = float(model.predict(x)[0])
        nxt = hist.loc[len(hist) - 2, TARGET] * np.exp(r)
        hist.loc[len(hist) - 1, TARGET] = nxt
        preds.append(nxt)
    return np.array(preds)


def fit_and_forecast(df: pd.DataFrame, model_name: str, dates: list[pd.Timestamp]) -> pd.DataFrame:
    """Train on all of `df` and forecast JKM for each date in `dates`, with an 80% interval."""
    n = len(dates)
    last = float(df[TARGET].iloc[-1])
    steps = np.arange(1, n + 1)
    if model_name == "naive":
        pred = np.full(n, last)
    elif model_name == "drift":
        window = df[TARGET].tail(60).to_numpy()
        slope = (window[-1] - window[0]) / (len(window) - 1)
        pred = last + slope * steps
    elif model_name == "ridge_lag":
        pred = _ridge_forecast(df, n)
    else:
        raise ValueError(f"unknown model {model_name}")
    band = Z80 * _daily_sigma(df) * np.sqrt(steps)
    return pd.DataFrame({
        "Date": pd.to_datetime(dates),
        "forecast": pred,
        "lower": pred * np.exp(-band),
        "upper": pred * np.exp(band),
    })


def walk_forward_cv(df: pd.DataFrame, n_folds: int = 3, horizon: int = 1) -> dict:
    """Expanding-window CV that mimics the real task: train up to month-end, forecast the whole month `horizon` months later.

    Scoring at the requested horizon matters: the best 1-month model is not necessarily the best 10-month model.
    """
    month_ends = df.groupby(df["Date"].dt.to_period("M"))["Date"].max().tolist()
    origins = month_ends[-(n_folds + horizon):-horizon]
    folds, per_model = [], {m: [] for m in MODELS}
    for origin in origins:
        train = df[df["Date"] <= origin]
        test_month = origin.to_period("M") + horizon
        test = df[df["Date"].dt.to_period("M") == test_month]
        # Multi-step models need the business-day path through the months in between.
        path = horizon_dates(origin, horizon - 1) if horizon > 1 else []
        fold = {"train_end": str(origin.date()), "test_month": str(test_month), "n_test": len(test)}
        for m in MODELS:
            fc = fit_and_forecast(train, m, path + list(test["Date"])).tail(len(test))
            score = metrics(test[TARGET].to_numpy(), fc["forecast"].to_numpy())
            fold[m] = score
            per_model[m].append(score)
        folds.append(fold)
    summary = {m: {k: float(np.mean([s[k] for s in scores])) for k in ("MAE", "RMSE", "MAPE")} for m, scores in per_model.items()}
    best = min(summary, key=lambda m: summary[m]["MAE"])
    return {"folds": folds, "summary": summary, "best_model": best, "horizon": horizon}


def backtest(forecast: pd.DataFrame, actual_df: pd.DataFrame) -> dict:
    merged = forecast.merge(actual_df[["Date", TARGET]], on="Date", how="inner")
    in_band = ((merged[TARGET] >= merged["lower"]) & (merged[TARGET] <= merged["upper"])).mean()
    return {
        "n_days": int(len(merged)),
        "metrics": metrics(merged[TARGET].to_numpy(), merged["forecast"].to_numpy()),
        "actual_mean": float(merged[TARGET].mean()),
        "forecast_mean": float(merged["forecast"].mean()),
        "interval_coverage": float(in_band),
        "rows": [
            {"Date": str(d.date()), "actual": float(a), "forecast": float(f)}
            for d, a, f in zip(merged["Date"], merged[TARGET], merged["forecast"])
        ],
    }
