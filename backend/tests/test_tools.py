import numpy as np
import pandas as pd

from app.tools.analysis import run_eda
from app.tools.forecast import (
    MODELS, backtest, fit_and_forecast, horizon_dates, make_features, metrics, preprocess, walk_forward_cv,
)


def test_preprocess_fills_missing_values(eval_df):
    clean, info = preprocess(eval_df)
    assert clean.isna().sum().sum() == 0
    assert info["missing_before"]["HH_Historical"] >= 1


def test_features_use_only_past_information(train_df):
    clean, _ = preprocess(train_df)
    feats = make_features(clean)
    # changing today's values must not change today's features (no leakage)
    tampered = clean.copy()
    tampered.loc[tampered.index[-1], ["JKM_Historical", "HH_Historical", "Brent_price"]] *= 10
    feats2 = make_features(tampered)
    pd.testing.assert_series_equal(feats.iloc[-1], feats2.iloc[-1])


def test_horizon_dates_next_month():
    dates = horizon_dates(pd.Timestamp("2025-12-31"))
    assert dates[0] == pd.Timestamp("2026-01-02")  # New Year excluded
    assert dates[-1] == pd.Timestamp("2026-01-30")
    assert all(d.month == 1 for d in dates)


def test_metrics_simple():
    m = metrics(np.array([10.0, 12.0]), np.array([11.0, 12.0]))
    assert m["MAE"] == 0.5
    assert round(m["MAPE"], 2) == round((1 / 10) / 2 * 100, 2)


def test_every_model_forecasts_full_horizon(train_df):
    clean, _ = preprocess(train_df)
    dates = horizon_dates(clean["Date"].iloc[-1])
    for name in MODELS:
        fc = fit_and_forecast(clean, name, dates)
        assert len(fc) == len(dates)
        assert fc["forecast"].notna().all()
        assert (fc["lower"] <= fc["forecast"]).all() and (fc["forecast"] <= fc["upper"]).all()


def test_walk_forward_cv_ranks_models(train_df):
    clean, _ = preprocess(train_df)
    cv = walk_forward_cv(clean, n_folds=3)
    assert set(cv["summary"]) == set(MODELS)
    assert cv["best_model"] in MODELS
    assert len(cv["folds"]) == 3


def test_walk_forward_cv_scores_at_requested_horizon(train_df):
    clean, _ = preprocess(train_df)
    cv = walk_forward_cv(clean, n_folds=3, horizon=10)
    assert [f["test_month"] for f in cv["folds"]] == ["2025-10", "2025-11", "2025-12"]
    assert [f["train_end"][:7] for f in cv["folds"]] == ["2024-12", "2025-01", "2025-02"]
    # further ahead is harder than one month ahead
    assert cv["summary"]["naive"]["MAE"] > walk_forward_cv(clean, n_folds=3)["summary"]["naive"]["MAE"]


def test_backtest_aligns_on_common_dates(train_df, eval_df):
    clean, _ = preprocess(train_df)
    fc = fit_and_forecast(clean, "naive", horizon_dates(clean["Date"].iloc[-1]))
    bt = backtest(fc, preprocess(eval_df)[0])
    assert bt["n_days"] == 20  # eval Jan has 20 trading days (19/1 holiday)
    assert bt["metrics"]["MAE"] > 0


def test_eda_has_key_sections(train_df):
    eda = run_eda(preprocess(train_df)[0])
    for key in ["summary", "monthly", "correlation_levels", "correlation_returns", "volatility", "latest"]:
        assert key in eda
