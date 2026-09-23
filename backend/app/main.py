"""FastAPI entrypoint: start agent runs, stream their trace, and handle human approvals."""
import logging
import threading
import uuid

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from langgraph.types import Command
from pydantic import BaseModel

from . import db
from .agents.deps import Deps
from .graph import build_graph
from .llm import llm_enabled

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("lng.api")


def _trace(run_id: str, agent: str, action: str, detail: dict) -> None:
    log.info("[run %s] %s: %s", run_id[:8], agent, action)
    db.log_step(run_id, agent, action, detail)


deps = Deps(load_training=db.load_training_df, load_external=db.load_external_df, trace=_trace)
graph = build_graph(deps)
_locks: dict[str, threading.Lock] = {}

app = FastAPI(title="LNG Agent Team API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.on_event("startup")
def startup() -> None:
    db.init_db()


class RunRequest(BaseModel):
    request: str = "Phân tích thị trường LNG và dự báo giá JKM tháng kế tiếp"


class Approval(BaseModel):
    approved: bool


def _execute(run_id: str, payload) -> None:
    """Run (or resume) the graph until it finishes or pauses on an interrupt."""
    cfg = {"configurable": {"thread_id": run_id}}
    with _locks.setdefault(run_id, threading.Lock()):
        try:
            out = graph.invoke(payload, cfg)
            if out.get("__interrupt__"):
                db.update_run(run_id, status="waiting_approval", pending_approval=out["__interrupt__"][0].value)
                return
            result = {k: out.get(k) for k in ("plan", "forecast", "backtest", "model_results", "external_approved", "llm_calls")}
            db.update_run(run_id, status="completed", pending_approval=None, result=result, report=out["report"])
        except Exception as exc:  # surface failures to the UI instead of hanging in "running"
            log.exception("run %s failed", run_id)
            db.log_step(run_id, "System", "Run failed", {"error": str(exc)})
            db.update_run(run_id, status="failed", error=str(exc))


@app.get("/api/health")
def health():
    return {"ok": True, "llm": llm_enabled()}


@app.post("/api/runs")
def create_run(body: RunRequest):
    run_id = str(uuid.uuid4())
    db.create_run(run_id, body.request)
    threading.Thread(target=_execute, args=(run_id, {"run_id": run_id, "request": body.request}), daemon=True).start()
    return {"run_id": run_id}


@app.get("/api/runs")
def list_runs():
    return db.list_runs()


@app.get("/api/runs/{run_id}")
def get_run(run_id: str):
    run = db.get_run(run_id)
    if not run:
        raise HTTPException(404, "run not found")
    return run


@app.post("/api/runs/{run_id}/approval")
def approve(run_id: str, body: Approval):
    run = db.get_run(run_id)
    if not run:
        raise HTTPException(404, "run not found")
    if run["status"] != "waiting_approval":
        raise HTTPException(409, f"run is not waiting for approval (status={run['status']})")
    db.update_run(run_id, status="running", pending_approval=None)
    threading.Thread(target=_execute, args=(run_id, Command(resume={"approved": body.approved})), daemon=True).start()
    return {"ok": True}


@app.get("/api/prices")
def prices(include_eval: bool = False):
    """Training series for the chart; eval series only when explicitly requested by the UI after approval."""
    df = db.load_training_df()
    out = {"train": _series(df)}
    if include_eval:
        out["eval"] = _series(db.load_external_df())
    return out


def _series(df: pd.DataFrame) -> list[dict]:
    return [{"Date": str(d.date()), "JKM": float(v)} for d, v in zip(df["Date"], df["JKM_Historical"]) if pd.notna(v)]
