"""Deterministic EDA toolkit used by the Data Analyst agent."""
import numpy as np
import pandas as pd

from ..config import EXOG, TARGET

COLS = [TARGET, *EXOG]


def _r(x, nd=3):
    return float(round(x, nd))


def run_eda(df: pd.DataFrame) -> dict:
    s = df.set_index("Date")[COLS]
    rets = np.log(s).diff().dropna()
    monthly = s[TARGET].resample("ME").agg(["mean", "min", "max"]).round(3)
    yearly = s[TARGET].groupby(s.index.year).agg(["mean", "min", "max", "std"]).round(3)
    vol = rets[TARGET].rolling(20).std() * np.sqrt(252)
    peak_day, trough_day = s[TARGET].idxmax(), s[TARGET].idxmin()
    last60 = s[TARGET].tail(60)
    return {
        "period": {"start": str(s.index.min().date()), "end": str(s.index.max().date()), "trading_days": len(s)},
        "summary": s.describe().round(3).to_dict(),
        "yearly": {str(k): v for k, v in yearly.to_dict("index").items()},
        "monthly": [{"month": str(i.to_period("M")), **{k: float(v) for k, v in row.items()}} for i, row in monthly.iterrows()],
        "correlation_levels": s.corr()[TARGET].drop(TARGET).round(3).to_dict(),
        "correlation_returns": rets.corr()[TARGET].drop(TARGET).round(3).to_dict(),
        "volatility": {
            "annualized_full": _r(rets[TARGET].std() * np.sqrt(252)),
            "annualized_last20d": _r(vol.iloc[-1]),
            "max_daily_move_pct": _r(rets[TARGET].abs().max() * 100, 2),
        },
        "extremes": {"max": {"date": str(peak_day.date()), "value": _r(s[TARGET].max())},
                     "min": {"date": str(trough_day.date()), "value": _r(s[TARGET].min())}},
        "latest": {
            "date": str(s.index[-1].date()),
            "JKM": _r(s[TARGET].iloc[-1]),
            "change_30d_pct": _r((s[TARGET].iloc[-1] / s[TARGET].iloc[-22] - 1) * 100, 2),
            "trend_60d_slope_per_day": _r(np.polyfit(np.arange(len(last60)), last60.to_numpy(), 1)[0], 4),
            "jkm_hh_spread": _r(s[TARGET].iloc[-1] - s["HH_Historical"].iloc[-1]),
            "jkm_brent_ratio_pct": _r(s[TARGET].iloc[-1] / s["Brent_price"].iloc[-1] * 100, 2),
        },
    }
