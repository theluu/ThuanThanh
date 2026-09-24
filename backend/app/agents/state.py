"""Shared state passed between agents in the LangGraph workflow."""
from typing import Any, TypedDict


class AgentState(TypedDict, total=False):
    run_id: str
    request: str
    declined: bool            # Orchestrator: nothing to run (off-topic or a question about the team) -> run stops
    kind: str                 # Orchestrator, when declined: "out_of_scope" | "help"
    examples: list[str]       # Orchestrator, when declined: requests the user can try instead
    params: dict              # Orchestrator: target_month, months_ahead, backtest, notes
    brief: str                # Orchestrator: restated objective
    plan: list[dict]          # Orchestrator: ordered tasks per agent
    data_summary: dict        # Data Engineer: rows, date range, data-quality info
    external_approved: bool   # Human decision on connecting to the external DB
    eda: dict                 # Data Analyst: numbers from the EDA tool
    analysis_notes: str       # Data Analyst: written insights
    model_results: dict       # Data Scientist: CV scores + chosen model
    forecast: list[dict]      # Data Scientist: daily forecast for next month
    backtest: dict | None     # Data Scientist: out-of-sample check (only if approved)
    ds_notes: str             # Data Scientist: written explanation
    report: str               # Report Writer: final markdown
    report_path: str
    llm_calls: dict[str, Any]
