"""LangGraph workflow wiring the agent team together."""
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from .agents import data_analyst, data_engineer, data_scientist, orchestrator, report_writer
from .agents.deps import Deps
from .agents.state import AgentState


def build_graph(deps: Deps, checkpointer=None):
    g = StateGraph(AgentState)
    g.add_node("orchestrator", orchestrator.make_node(deps))
    g.add_node("data_engineer", data_engineer.make_node(deps))
    g.add_node("approval_gate", data_engineer.make_gate(deps))  # human-in-the-loop interrupt
    g.add_node("data_analyst", data_analyst.make_node(deps))
    g.add_node("data_scientist", data_scientist.make_node(deps))
    g.add_node("report_writer", report_writer.make_node(deps))

    g.add_edge(START, "orchestrator")
    g.add_edge("orchestrator", "data_engineer")
    g.add_edge("data_engineer", "approval_gate")
    g.add_edge("approval_gate", "data_analyst")
    g.add_edge("data_analyst", "data_scientist")
    g.add_edge("data_scientist", "report_writer")
    g.add_edge("report_writer", END)
    return g.compile(checkpointer=checkpointer or MemorySaver())
