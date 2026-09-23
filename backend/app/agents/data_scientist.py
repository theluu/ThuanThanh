"""Data Scientist: model selection with walk-forward CV, next-month forecast, out-of-sample backtest."""
import json

from ..llm import ask
from ..tools.forecast import backtest, fit_and_forecast, horizon_dates, preprocess, walk_forward_cv
from .deps import Deps
from .state import AgentState

NAME = "Data Scientist"


def make_node(deps: Deps):
    def data_scientist(state: AgentState) -> AgentState:
        run_id = state["run_id"]
        df, _ = preprocess(deps.load_training())

        cv = walk_forward_cv(df, n_folds=3)
        deps.trace(run_id, NAME, "Walk-forward CV (train to month-end, forecast whole next month)",
                   {"summary": cv["summary"], "best_model": cv["best_model"]})

        dates = horizon_dates(df["Date"].iloc[-1])
        fc = fit_and_forecast(df, cv["best_model"], dates)
        forecast = [{"Date": str(r.Date.date()), "forecast": round(r.forecast, 3), "lower": round(r.lower, 3),
                     "upper": round(r.upper, 3)} for r in fc.itertuples()]
        fc_mean = float(fc["forecast"].mean())
        deps.trace(run_id, NAME, f"Forecast {len(dates)} trading days with {cv['best_model']}",
                   {"month": str(dates[0].to_period('M')), "mean": round(fc_mean, 3),
                    "first": forecast[0], "last": forecast[-1]})

        bt = None
        if state.get("external_approved"):
            ext, _ = preprocess(deps.load_external())
            bt = backtest(fc, ext)
            # Benchmark: same backtest for every candidate, to show whether CV selection generalised.
            bt["all_models"] = {m: backtest(fit_and_forecast(df, m, dates), ext)["metrics"] for m in cv["summary"]}
            deps.trace(run_id, NAME, "Backtested forecast on external out-of-sample data",
                       {"metrics": bt["metrics"], "coverage80": bt["interval_coverage"], "all_models": bt["all_models"]})
        else:
            deps.trace(run_id, NAME, "Skipped backtest (external DB access not approved)", {})

        model_results = {"cv": cv, "chosen": cv["best_model"], "forecast_mean": fc_mean,
                         "forecast_min": float(fc["forecast"].min()), "forecast_max": float(fc["forecast"].max())}
        notes, src = ask(
            "Bạn là Data Scientist. Giải thích ngắn (4-6 gạch đầu dòng, tiếng Việt) vì sao chọn mô hình, ý nghĩa MAE/RMSE/MAPE, "
            "khoảng tin cậy 80%, và kết quả backtest (nếu có). Chỉ dùng số liệu được cung cấp.",
            json.dumps({"cv_summary": cv["summary"], "chosen": cv["best_model"], "forecast_mean": fc_mean,
                        "backtest": bt and {k: bt[k] for k in ("metrics", "actual_mean", "forecast_mean", "interval_coverage", "all_models")},
                        "analyst_notes": state.get("analysis_notes", "")}, ensure_ascii=False, default=str),
            fallback=(f"- Mô hình chọn: **{cv['best_model']}** (MAE CV thấp nhất = {cv['summary'][cv['best_model']]['MAE']:.3f}).\n"
                      f"- Dự báo trung bình tháng: {fc_mean:.3f} USD/MMBtu, khoảng 80% mở rộng theo căn bậc hai số ngày."),
        )
        deps.trace(run_id, NAME, "Explained model choice & results", {"notes": notes, "source": src})
        return {"model_results": model_results, "forecast": forecast, "backtest": bt, "ds_notes": notes,
                "llm_calls": {**state.get("llm_calls", {}), "data_scientist": src}}
    return data_scientist
