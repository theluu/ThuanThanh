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


_GATE_PROMPT = (
    "You gate requests for an LNG market analytics team (JKM price analysis & forecasting). The user may write "
    "Vietnamese with typos or missing diacritics (e.g. 'dựa báo' = 'dự báo'); read the request charitably. "
    "Reply with exactly one word: IN if it can reasonably be served by LNG/JKM market analysis or price forecasting "
    "(a bare 'forecast month X' counts), HELP if it asks what the team is or can do, otherwise OUT.")


def _classify(request: str) -> tuple[str, str, str]:
    """('in' | 'help' | 'out', how it was decided, llm source)."""
    verdict = scope(request)
    if verdict in ("in", "help"):
        return verdict, "keywords", "none"
    if not llm_enabled():
        if verdict == "maybe":
            return "in", "generic analytics wording, no LLM to confirm — accepted", "none"
        return "out", "keywords", "none"
    if verdict == "out" and len(fold(request).split()) < 2:
        return "out", "keywords (too short to be a request)", "none"
    # Keywords are brittle against typos, so the model gets a second look before anything is refused.
    answer, src = ask(_GATE_PROMPT, wrap_untrusted(request), fallback="IN" if verdict == "maybe" else "OUT")
    word = fold(answer).strip()
    decided = "help" if word.startswith("help") else "out" if word.startswith("out") else "in"
    return decided, f"LLM ({src})", src


def help_message() -> str:
    return "\n\n".join([
        "# Nhóm agent có thể làm gì",
        "LNG Desk là một nhóm agent chuyên **phân tích thị trường LNG và dự báo giá JKM**:",
        "- **Orchestrator** hiểu yêu cầu, lập kế hoạch và giao việc.\n"
        "- **Data Engineer** nạp dữ liệu giá 2024–2025 và kiểm tra chất lượng.\n"
        "- **Data Analyst** phân tích xu hướng, mùa vụ, biến động và tương quan với Henry Hub, Brent, DXY, vàng.\n"
        "- **Data Scientist** so sánh nhiều mô hình, chọn mô hình tốt nhất và dự báo tháng 01 hoặc 02/2026.\n"
        "- **Bạn** quyết định có cho phép kết nối cơ sở dữ liệu 2026 để kiểm định ngoài mẫu hay không.\n"
        "- **Report Writer** viết báo cáo trả lời đúng câu hỏi của bạn.",
        "Chọn một yêu cầu mẫu bên dưới để chạy thử, hoặc tự viết yêu cầu của bạn.",
    ])


def decline_message(request: str) -> str:
    return "\n\n".join([
        "# Yêu cầu nằm ngoài phạm vi",
        f"Nhóm agent chỉ phân tích thị trường và dự báo giá **LNG (JKM)**. Yêu cầu *“{quote(request)}”* không thuộc phạm vi này, "
        "nên Orchestrator dừng lại trước khi giao việc: không nạp dữ liệu, không kết nối cơ sở dữ liệu nào và không chạy mô hình.",
        "Nếu bạn muốn dự báo, hãy nhắc tới **JKM** hoặc **LNG**, hoặc chọn một yêu cầu mẫu bên dưới.",
    ])


def make_node(deps: Deps):
    def orchestrator(state: AgentState) -> AgentState:
        run_id, request = state["run_id"], state["request"]
        deps.trace(run_id, NAME, "Received request", {"request": request})

        verdict, how, src = _classify(request)
        if verdict == "help":
            deps.trace(run_id, NAME, "Answered question about the team's capabilities", {"decided_by": how})
            return {"declined": True, "kind": "help", "report": help_message(), "examples": EXAMPLES, "llm_calls": {"orchestrator": src}}
        if verdict == "out":
            deps.trace(run_id, NAME, "Declined request: outside LNG/JKM scope", {"decided_by": how})
            return {"declined": True, "kind": "out_of_scope", "report": decline_message(request),
                    "examples": EXAMPLES, "llm_calls": {"orchestrator": src}}

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
