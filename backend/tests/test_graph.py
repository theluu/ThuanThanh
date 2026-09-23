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


@pytest.fixture
def graph_and_steps(train_df, eval_df, monkeypatch, tmp_path):
    monkeypatch.setattr(llm, "active_providers", lambda: [])
    monkeypatch.setattr("app.config.REPORTS_DIR", tmp_path)
    steps = []
    deps = Deps(load_training=lambda: train_df.copy(), load_external=lambda: eval_df.copy(),
                trace=lambda run_id, agent, action, detail: steps.append((agent, action)))
    return build_graph(deps), steps


def test_off_topic_request_is_declined_before_any_work(graph_and_steps):
    graph, steps = graph_and_steps
    out = graph.invoke({"run_id": "t2", "request": "Hôm nay ăn gì"}, {"configurable": {"thread_id": "t2"}})
    assert out["declined"] and "ngoài phạm vi" in out["report"]
    assert "__interrupt__" not in out and "forecast" not in out
    assert {a for a, _ in steps} == {"Orchestrator"}


def test_no_backtest_request_skips_approval(graph_and_steps):
    graph, steps = graph_and_steps
    out = graph.invoke({"run_id": "t3", "request": "Dự báo JKM tháng tới, không cần backtest"},
                       {"configurable": {"thread_id": "t3"}})
    assert "__interrupt__" not in out  # never paused for the human
    assert out["backtest"] is None and not any(a == "Human" for a, _ in steps)
    assert "không cần" in out["report"]


def test_february_target_forecasts_february(graph_and_steps):
    graph, _ = graph_and_steps
    cfg = {"configurable": {"thread_id": "t4"}}
    graph.invoke({"run_id": "t4", "request": "Dự báo JKM tháng 02/2026"}, cfg)
    out = graph.invoke(Command(resume={"approved": True}), cfg)
    assert {r["Date"][:7] for r in out["forecast"]} == {"2026-02"} and len(out["forecast"]) == 20
    assert out["backtest"]["n_days"] == 11  # eval data covers Feb 2026 up to the 17th
    assert "tháng 2026-02" in out["report"]


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
