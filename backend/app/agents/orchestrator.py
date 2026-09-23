"""Orchestrator: understands the request, plans the work and assigns tasks to each agent."""
from ..guardrails import wrap_untrusted
from ..llm import ask
from .deps import Deps
from .state import AgentState

NAME = "Orchestrator"

PLAN = [
    {"agent": "Data Engineer", "task": "Load 2024-2025 JKM data from the main DB, run data-quality checks"},
    {"agent": "Human (approval)", "task": "Approve/reject connecting to the external DB holding 2026 out-of-sample data"},
    {"agent": "Data Analyst", "task": "EDA: trend, seasonality, volatility, correlation with HH/Brent/DXY/Gold"},
    {"agent": "Data Scientist", "task": "Walk-forward CV of candidate models, pick best, forecast next month, backtest if data approved"},
    {"agent": "Report Writer", "task": "Compile the analysis & next-month forecast report"},
]


def make_node(deps: Deps):
    def orchestrator(state: AgentState) -> AgentState:
        run_id = state["run_id"]
        deps.trace(run_id, NAME, "Received request", {"request": state["request"]})
        brief, src = ask(
            "You are the lead of an LNG market analytics team. Restate the business objective in 2-3 sentences (Vietnamese) "
            "and mention which team member handles which part.",
            f"Request:\n{wrap_untrusted(state['request'])}\nTeam plan: {PLAN}",
            fallback=f"Mục tiêu: {state['request']}. Team thực hiện theo kế hoạch {len(PLAN)} bước.",
        )
        deps.trace(run_id, NAME, "Created plan & assigned tasks", {"plan": PLAN, "brief": brief, "source": src})
        return {"plan": PLAN, "llm_calls": {"orchestrator": src}}
    return orchestrator
