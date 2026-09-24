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

        params = state["params"]
        cv = walk_forward_cv(df, n_folds=3, horizon=params["months_ahead"])
        deps.trace(run_id, NAME, f"Walk-forward CV at the requested horizon ({params['months_ahead']} month(s) ahead)",
                   {"summary": cv["summary"], "best_model": cv["best_model"], "test_months": [f["test_month"] for f in cv["folds"]]})
        # Forecast every day up to the target month (multi-step models need the path), then keep the target month.
        dates = horizon_dates(df["Date"].iloc[-1], params["months_ahead"])

        def target(fc_all):
            return fc_all[fc_all["Date"].dt.strftime("%Y-%m") == params["target_month"]].reset_index(drop=True)

        fc = target(fit_and_forecast(df, cv["best_model"], dates))
        forecast = [{"Date": str(r.Date.date()), "forecast": round(r.forecast, 3), "lower": round(r.lower, 3),
                     "upper": round(r.upper, 3)} for r in fc.itertuples()]
        fc_mean = float(fc["forecast"].mean())
        deps.trace(run_id, NAME, f"Forecast {len(fc)} trading days of {params['target_month']} with {cv['best_model']}",
                   {"month": params["target_month"], "months_ahead": params["months_ahead"], "mean": round(fc_mean, 3),
                    "first": forecast[0], "last": forecast[-1]})

        bt = None
        if state.get("external_approved"):
            ext, _ = preprocess(deps.load_external())
            bt = backtest(fc, ext)
            # Benchmark: same backtest for every candidate, to show whether CV selection generalised.
            bt["all_models"] = {m: backtest(target(fit_and_forecast(df, m, dates)), ext)["metrics"] for m in cv["summary"]}
            deps.trace(run_id, NAME, "Backtested forecast on external out-of-sample data",
                       {"metrics": bt["metrics"], "coverage80": bt["interval_coverage"], "all_models": bt["all_models"]})
        else:
            why = "external DB access not approved" if params["backtest"] else "not requested"
            deps.trace(run_id, NAME, f"Skipped backtest ({why})", {})

        model_results = {"cv": cv, "chosen": cv["best_model"], "forecast_mean": fc_mean,
                         "forecast_min": float(fc["forecast"].min()), "forecast_max": float(fc["forecast"].max()),
                         "band_low": float(fc["lower"].mean()), "band_high": float(fc["upper"].mean())}
        notes, src = ask(
            "Bạn là Data Scientist. Giải thích ngắn (4-6 gạch đầu dòng, tiếng Việt) vì sao chọn mô hình, ý nghĩa MAE/RMSE/MAPE, "
            "khoảng tin cậy 80%, và kết quả backtest (nếu có). Nếu months_ahead > 1, nói rõ dự báo xa hơn nên kém chắc chắn hơn "
            "(CV chỉ đánh giá dự báo 1 tháng). Chỉ dùng số liệu được cung cấp.",
            json.dumps({"target_month": params["target_month"], "months_ahead": params["months_ahead"],
                        "cv_summary": cv["summary"], "chosen": cv["best_model"], "forecast_mean": fc_mean,
                        "band80_mean": [model_results["band_low"], model_results["band_high"]],
                        "backtest": bt and {k: bt[k] for k in ("metrics", "actual_mean", "forecast_mean", "interval_coverage", "all_models")},
                        "analyst_notes": state.get("analysis_notes", "")}, ensure_ascii=False, default=str),
            fallback=(f"- Mô hình chọn: **{cv['best_model']}** (MAE CV thấp nhất = {cv['summary'][cv['best_model']]['MAE']:.3f}).\n"
                      f"- Dự báo trung bình tháng: {fc_mean:.3f} USD/MMBtu, khoảng 80% mở rộng theo căn bậc hai số ngày."),
        )
        deps.trace(run_id, NAME, "Explained model choice & results", {"notes": notes, "source": src})
        return {"model_results": model_results, "forecast": forecast, "backtest": bt, "ds_notes": notes,
                "llm_calls": {**state.get("llm_calls", {}), "data_scientist": src}}
    return data_scientist
