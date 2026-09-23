"""FastAPI entrypoint: start agent runs, stream their trace, and handle human approvals."""
import hmac
import logging
import threading
import time
import uuid
from collections import defaultdict, deque

import pandas as pd
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from langgraph.types import Command
from pydantic import BaseModel, Field

from . import config, db
from .agents.deps import Deps
from .graph import build_graph
from .guardrails import GuardrailError, check_request, redact
from .llm import active_providers

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("lng.api")


def _trace(run_id: str, agent: str, action: str, detail: dict) -> None:
    log.info("[run %s] %s: %s", run_id[:8], agent, action)
    db.log_step(run_id, agent, action, detail)


deps = Deps(load_training=db.load_training_df, load_external=db.load_external_df, trace=_trace)
graph = build_graph(deps)
_locks: dict[str, threading.Lock] = {}

app = FastAPI(title="LNG Agent Team API")
app.add_middleware(CORSMiddleware, allow_origins=config.CORS_ORIGINS, allow_methods=["GET", "POST"],
                   allow_headers=["Content-Type", "X-API-Key"])


@app.middleware("http")
async def security_headers(request: Request, call_next):
    resp = await call_next(request)
    resp.headers.update({"X-Content-Type-Options": "nosniff", "X-Frame-Options": "DENY",
                         "Referrer-Policy": "no-referrer", "Cache-Control": "no-store"})
    return resp


def require_token(x_api_key: str = Header(default="")) -> None:
    """Shared-token auth, enabled when API_TOKEN is set (the approval endpoint must not be open to anyone)."""
    if config.API_TOKEN and not hmac.compare_digest(x_api_key, config.API_TOKEN):
        raise HTTPException(401, "invalid or missing API key")


_hits: dict[str, deque] = defaultdict(deque)
_hits_lock = threading.Lock()


def rate_limit(request: Request) -> None:
    """Sliding-window limit on state-changing requests per client IP (in-memory, single process)."""
    key, now = request.client.host if request.client else "?", time.monotonic()
    with _hits_lock:
        q = _hits[key]
        while q and now - q[0] > 60:
            q.popleft()
        if len(q) >= config.RATE_LIMIT_PER_MIN:
            raise HTTPException(429, "too many requests, try again later")
        q.append(now)


@app.on_event("startup")
def startup() -> None:
    db.init_db()


class RunRequest(BaseModel):
    request: str = Field("Phân tích thị trường LNG và dự báo giá JKM tháng kế tiếp", max_length=2000)


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
            if out.get("declined"):  # Orchestrator refused an off-topic request; nothing else ran
                db.update_run(run_id, status="declined", result={"llm_calls": out.get("llm_calls")}, report=out["report"])
                return
            keys = ("params", "plan", "forecast", "backtest", "model_results", "external_approved", "llm_calls")
            result = {k: out.get(k) for k in keys}
            db.update_run(run_id, status="completed", pending_approval=None, result=result, report=out["report"])
        except Exception as exc:  # surface failures to the UI instead of hanging in "running"
            log.exception("run %s failed", run_id)
            msg = redact(f"{type(exc).__name__}: {exc}")[:500]  # never leak credentials to the UI
            db.log_step(run_id, "System", "Run failed", {"error": msg})
            db.update_run(run_id, status="failed", error=msg)


@app.get("/api/health")
def health():
    providers = active_providers()
    return {"ok": True, "llm": bool(providers), "providers": providers}


@app.post("/api/runs", dependencies=[Depends(require_token), Depends(rate_limit)])
def create_run(body: RunRequest):
    try:
        request = check_request(body.request)
    except GuardrailError as exc:
        log.warning("blocked run request: %s", exc)
        raise HTTPException(400, str(exc)) from exc
    if db.count_active_runs() >= config.MAX_ACTIVE_RUNS:
        raise HTTPException(429, "too many runs in progress, try again later")
    run_id = str(uuid.uuid4())
    db.create_run(run_id, request)
    threading.Thread(target=_execute, args=(run_id, {"run_id": run_id, "request": request}), daemon=True).start()
    return {"run_id": run_id}


@app.get("/api/runs", dependencies=[Depends(require_token)])
def list_runs():
    return db.list_runs()


@app.get("/api/runs/{run_id}", dependencies=[Depends(require_token)])
def get_run(run_id: uuid.UUID):
    run = db.get_run(str(run_id))
    if not run:
        raise HTTPException(404, "run not found")
    return run


@app.post("/api/runs/{run_id}/approval", dependencies=[Depends(require_token), Depends(rate_limit)])
def approve(run_id: uuid.UUID, body: Approval):
    run_id = str(run_id)
    run = db.get_run(run_id)
    if not run:
        raise HTTPException(404, "run not found")
    if not db.claim_approval(run_id):  # atomic: concurrent/replayed decisions get 409
        raise HTTPException(409, f"run is not waiting for approval (status={run['status']})")
    threading.Thread(target=_execute, args=(run_id, Command(resume={"approved": body.approved})), daemon=True).start()
    return {"ok": True}


@app.get("/api/prices", dependencies=[Depends(require_token)])
def prices(run_id: uuid.UUID | None = None):
    """Training series for the chart; the external (eval) series only for a completed run whose DB access a human approved."""
    out = {"train": _series(db.load_training_df())}
    if run_id is not None:
        run = db.get_run(str(run_id))
        if not run:
            raise HTTPException(404, "run not found")
        if run["status"] == "completed" and (run.get("result") or {}).get("external_approved"):
            out["eval"] = _series(db.load_external_df())
    return out


def _series(df: pd.DataFrame) -> list[dict]:
    return [{"Date": str(d.date()), "JKM": float(v)} for d, v in zip(df["Date"], df["JKM_Historical"]) if pd.notna(v)]
