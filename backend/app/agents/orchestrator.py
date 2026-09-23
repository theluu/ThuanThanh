"""Orchestrator: understands the request, declines off-topic ones, extracts parameters, plans the work."""
from ..guardrails import fold, wrap_untrusted
from ..llm import ask, llm_enabled
from ..tools.intent import extract_params, quote, scope
from .deps import Deps
from .state import AgentState

NAME = "Orchestrator"

EXAMPLES = [
    "Phân tích thị trường LNG 2024–2025 và dự báo giá JKM tháng kế tiếp",
    "Dự báo giá JKM tháng 02/2026, tập trung vào tương quan với Brent",
    "Dự báo JKM tháng tới, không cần backtest",
]


def build_plan(params: dict) -> list[dict]:
    month = params["target_month"]
    plan = [{"agent": "Data Engineer", "task": "Load 2024-2025 JKM data from the main DB, run data-quality checks"}]
    if params["backtest"]:
        plan.append({"agent": "Human (approval)", "task": "Approve/reject connecting to the external DB holding 2026 out-of-sample data"})
    plan += [
        {"agent": "Data Analyst", "task": "EDA: trend, seasonality, volatility, correlation with HH/Brent/DXY/Gold — focused on the request"},
        {"agent": "Data Scientist", "task": f"Walk-forward CV of candidate models, pick best, forecast {month}"
                                            + (", backtest if data approved" if params["backtest"] else "")},
        {"agent": "Report Writer", "task": f"Compile the analysis & {month} forecast report answering the request"},
    ]
    return plan


def _in_scope(request: str) -> tuple[bool, str, str]:
    """(in_scope, how it was decided, llm source)."""
    verdict = scope(request)
    if verdict != "maybe":
        return verdict == "in", "keywords", "none"
    if not llm_enabled():
        return True, "generic analytics wording, no LLM to confirm — accepted", "none"
    answer, src = ask(
        "You gate requests for an LNG market analytics team (JKM price analysis & forecasting). Reply with exactly one word: "
        "IN if the request can reasonably be served by LNG/JKM market analysis or price forecasting, otherwise OUT.",
        wrap_untrusted(request), fallback="IN")
    return not fold(answer).strip().startswith("out"), f"LLM ({src})", src


def decline_message(request: str) -> str:
    return "\n\n".join([
        "# Yêu cầu nằm ngoài phạm vi",
        f"Nhóm agent chỉ phân tích thị trường và dự báo giá **LNG (JKM)**. Yêu cầu *“{quote(request)}”* không thuộc phạm vi này, "
        "nên Orchestrator dừng lại trước khi giao việc: không nạp dữ liệu, không kết nối cơ sở dữ liệu nào và không chạy mô hình.",
        "Bạn có thể thử một trong các yêu cầu sau:",
        "\n".join(f"- {e}" for e in EXAMPLES),
    ])


def make_node(deps: Deps):
    def orchestrator(state: AgentState) -> AgentState:
        run_id, request = state["run_id"], state["request"]
        deps.trace(run_id, NAME, "Received request", {"request": request})

        ok, how, src = _in_scope(request)
        if not ok:
            deps.trace(run_id, NAME, "Declined request: outside LNG/JKM scope", {"decided_by": how})
            return {"declined": True, "report": decline_message(request), "llm_calls": {"orchestrator": src}}

        params = extract_params(request)
        plan = build_plan(params)
        deps.trace(run_id, NAME, "Understood request & extracted parameters", {"params": params, "scope_decided_by": how})
        brief, src = ask(
            "You are the lead of an LNG market analytics team. In 2-3 Vietnamese sentences, restate what the user asked "
            "(keep their specific focus) and say which team member handles which part.",
            f"Request:\n{wrap_untrusted(request)}\nParameters: {params}\nTeam plan: {plan}",
            fallback=f"Yêu cầu: “{quote(request)}”. Nhóm dự báo JKM tháng {params['target_month']} theo kế hoạch {len(plan)} bước"
                     + ("" if params["backtest"] else ", không kiểm định ngoài mẫu") + ".",
        )
        deps.trace(run_id, NAME, "Created plan & assigned tasks", {"plan": plan, "brief": brief, "source": src})
        return {"declined": False, "params": params, "plan": plan, "brief": brief, "llm_calls": {"orchestrator": src}}
    return orchestrator
