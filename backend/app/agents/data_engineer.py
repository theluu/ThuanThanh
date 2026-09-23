"""Data Engineer: loads data from the main DB, checks quality, and asks permission before touching another DB."""
from langgraph.types import interrupt

from ..tools.forecast import preprocess
from .deps import Deps
from .state import AgentState

NAME = "Data Engineer"


def make_node(deps: Deps):
    def data_engineer(state: AgentState) -> AgentState:
        run_id = state["run_id"]
        df = deps.load_training()
        _, info = preprocess(df)
        summary = {
            **info,
            "start": str(df["Date"].min().date()),
            "end": str(df["Date"].max().date()),
            "duplicates": int(df["Date"].duplicated().sum()),
            "columns": list(df.columns),
        }
        deps.trace(run_id, NAME, "Loaded training data from main DB & checked quality", summary)
        return {"data_summary": summary}
    return data_engineer


def make_gate(deps: Deps):
    def approval_gate(state: AgentState) -> AgentState:
        """Pauses the graph (LangGraph interrupt) until a human approves the external DB connection."""
        run_id = state["run_id"]
        request = {
            "agent": NAME,
            "action": "connect_external_database",
            "target": deps.external_target,
            "reason": "Đọc dữ liệu 01-02/2026 (out-of-sample) để backtest dự báo. Dữ liệu này KHÔNG dùng để huấn luyện.",
        }
        decision = interrupt(request)
        approved = bool(decision.get("approved")) if isinstance(decision, dict) else bool(decision)
        deps.trace(run_id, "Human", "Approved external DB connection" if approved else "Rejected external DB connection",
                   {"target": deps.external_target})
        if approved:
            ext = deps.load_external()
            deps.trace(run_id, NAME, "Connected to external DB & loaded evaluation data",
                       {"rows": len(ext), "start": str(ext["Date"].min().date()), "end": str(ext["Date"].max().date())})
        return {"external_approved": approved}
    return approval_gate
