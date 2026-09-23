import pytest
from langgraph.types import Command

from app import llm
from app.agents.deps import Deps
from app.graph import build_graph


@pytest.fixture
def run_graph(train_df, eval_df, monkeypatch, tmp_path):
    monkeypatch.setattr(llm, "active_providers", lambda: [])  # deterministic, offline
    monkeypatch.setattr("app.config.REPORTS_DIR", tmp_path)
    steps = []
    deps = Deps(load_training=lambda: train_df.copy(), load_external=lambda: eval_df.copy(),
                trace=lambda run_id, agent, action, detail: steps.append((agent, action)))

    def _run(approved: bool):
        graph = build_graph(deps)
        cfg = {"configurable": {"thread_id": "t1"}}
        out = graph.invoke({"run_id": "t1", "request": "Dự báo JKM tháng tới"}, cfg)
        assert "__interrupt__" in out  # paused waiting for human
        assert not any(a == "Data Analyst" for a, _ in steps)
        final = graph.invoke(Command(resume={"approved": approved}), cfg)
        return final, steps
    return _run


def test_graph_approved_runs_backtest(run_graph):
    final, steps = run_graph(True)
    assert final["backtest"]["n_days"] == 20
    assert "Kiểm định ngoài mẫu (backtest" in final["report"]
    agents = [a for a, _ in steps]
    assert agents.index("Orchestrator") < agents.index("Data Engineer") < agents.index("Human") \
        < agents.index("Data Analyst") < agents.index("Data Scientist") < agents.index("Report Writer")


def test_graph_rejected_skips_backtest(run_graph):
    final, steps = run_graph(False)
    assert final["backtest"] is None
    assert "từ chối" in final["report"]
    assert len(final["forecast"]) == 21
