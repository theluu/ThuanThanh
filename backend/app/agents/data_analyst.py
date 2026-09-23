"""Data Analyst: exploratory analysis of the JKM market and its drivers."""
import json

from ..llm import ask
from ..tools.analysis import run_eda
from ..tools.forecast import preprocess
from .deps import Deps
from .state import AgentState

NAME = "Data Analyst"


def fallback_notes(eda: dict) -> str:
    lt, cr = eda["latest"], eda["correlation_returns"]
    top = max(cr, key=lambda k: abs(cr[k]))
    return (
        f"- Giá JKM cuối kỳ {lt['date']}: {lt['JKM']} USD/MMBtu, thay đổi 30 ngày {lt['change_30d_pct']}%.\n"
        f"- Độ dốc xu hướng 60 ngày: {lt['trend_60d_slope_per_day']} USD/ngày.\n"
        f"- Biến động năm hóa: toàn kỳ {eda['volatility']['annualized_full']}, 20 ngày gần nhất {eda['volatility']['annualized_last20d']}.\n"
        f"- Biến có tương quan lợi suất mạnh nhất với JKM: {top} ({cr[top]}).\n"
        f"- Spread JKM-HH hiện tại: {lt['jkm_hh_spread']} USD/MMBtu; JKM/Brent = {lt['jkm_brent_ratio_pct']}%."
    )


def make_node(deps: Deps):
    def data_analyst(state: AgentState) -> AgentState:
        run_id = state["run_id"]
        df, _ = preprocess(deps.load_training())
        eda = run_eda(df)
        deps.trace(run_id, NAME, "Ran EDA tool (stats, monthly trend, volatility, correlations)",
                   {"latest": eda["latest"], "correlation_returns": eda["correlation_returns"]})
        facts = {k: eda[k] for k in ("period", "yearly", "correlation_levels", "correlation_returns", "volatility", "extremes", "latest")}
        facts["monthly_last6"] = eda["monthly"][-6:]
        notes, src = ask(
            "Bạn là Data Analyst thị trường LNG. Viết 5-7 gạch đầu dòng tiếng Việt, súc tích, chỉ dùng số liệu được cung cấp: "
            "xu hướng, mùa vụ, biến động, quan hệ với HH/Brent/DXY/Gold, hàm ý cho dự báo tháng tới. Không bịa số.",
            json.dumps(facts, ensure_ascii=False),
            fallback=fallback_notes(eda),
        )
        deps.trace(run_id, NAME, "Wrote market insights for Data Scientist & Report Writer", {"notes": notes, "source": src})
        return {"eda": eda, "analysis_notes": notes, "llm_calls": {**state.get("llm_calls", {}), "data_analyst": src}}
    return data_analyst
