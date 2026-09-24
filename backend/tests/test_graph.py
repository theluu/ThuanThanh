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


def test_capability_question_gets_help_not_refusal(graph_and_steps):
    graph, steps = graph_and_steps
    out = graph.invoke({"run_id": "t5", "request": "Bạn làm được những gì"}, {"configurable": {"thread_id": "t5"}})
    assert out["declined"] and out["kind"] == "help" and "ngoài phạm vi" not in out["report"]
    assert out["examples"] and {a for a, _ in steps} == {"Orchestrator"}


def test_misspelled_forecast_request_runs(graph_and_steps):
    graph, _ = graph_and_steps
    out = graph.invoke({"run_id": "t6", "request": "Dựa báo tháng 1 cho tôi"}, {"configurable": {"thread_id": "t6"}})
    assert not out.get("declined") and "__interrupt__" in out  # reached the approval valve


def test_off_topic_gets_llm_second_look(monkeypatch):
    from app.agents import orchestrator
    monkeypatch.setattr(orchestrator, "llm_enabled", lambda: True)
    monkeypatch.setattr(orchestrator, "ask", lambda *a, **k: ("IN", "openai"))
    assert orchestrator._classify("cho tôi con số tháng sau đi")[0] == "in"
    monkeypatch.setattr(orchestrator, "ask", lambda *a, **k: ("OUT", "openai"))
    assert orchestrator._classify("Hôm nay ăn gì")[0] == "out"
    assert orchestrator._classify("s") == ("out", "keywords (too short to be a request)", "none")


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


def test_october_target_forecasts_october_without_approval(graph_and_steps):
    graph, steps = graph_and_steps
    out = graph.invoke({"run_id": "t7", "request": "Phân tích thị trường LNG 2024–2025 và dự báo giá JKM tháng 10"},
                       {"configurable": {"thread_id": "t7"}})
    assert "__interrupt__" not in out and not any(a == "Human" for a, _ in steps)  # no actuals -> nothing to approve
    assert {r["Date"][:7] for r in out["forecast"]} == {"2026-10"}
    assert "tháng 2026-10" in out["report"] and "chưa có tháng này" in out["report"]
