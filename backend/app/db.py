"""Database layer: main DB (training data + run/trace tables) and the external DB (out-of-sample data)."""
import json
from datetime import datetime, timezone
from functools import lru_cache

import pandas as pd
from sqlalchemy import JSON, Column, DateTime, Integer, MetaData, String, Table, Text, create_engine, inspect, select

from . import config

metadata = MetaData()

runs = Table(
    "runs", metadata,
    Column("id", String(36), primary_key=True),
    Column("request", Text, nullable=False),
    Column("status", String(32), nullable=False),  # running | waiting_approval | completed | failed
    Column("pending_approval", JSON),
    Column("result", JSON),  # forecast / backtest / model results for the UI
    Column("report", Text),
    Column("error", Text),
    Column("created_at", DateTime(timezone=True)),
    Column("updated_at", DateTime(timezone=True)),
)

agent_steps = Table(
    "agent_steps", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("run_id", String(36), index=True, nullable=False),
    Column("agent", String(64), nullable=False),
    Column("action", String(255), nullable=False),
    Column("detail", JSON),
    Column("created_at", DateTime(timezone=True)),
)


def _now():
    return datetime.now(timezone.utc)


@lru_cache
def main_engine():
    return create_engine(config.MAIN_DB_URL, pool_pre_ping=True)


@lru_cache
def external_engine():
    return create_engine(config.EXTERNAL_DB_URL, pool_pre_ping=True)


def read_csv(path) -> pd.DataFrame:
    df = pd.read_csv(path, parse_dates=["Date"])
    return df.sort_values("Date").reset_index(drop=True)


def init_db() -> None:
    """Create run/trace tables and seed both databases from the provided CSVs (idempotent)."""
    metadata.create_all(main_engine())
    if not inspect(main_engine()).has_table("lng_prices"):
        read_csv(config.TRAIN_CSV).to_sql("lng_prices", main_engine(), index=False)
    if not inspect(external_engine()).has_table("lng_prices_eval"):
        read_csv(config.EVAL_CSV).to_sql("lng_prices_eval", external_engine(), index=False)


def load_training_df() -> pd.DataFrame:
    df = pd.read_sql('SELECT * FROM lng_prices ORDER BY "Date"', main_engine(), parse_dates=["Date"])
    return df


def load_external_df() -> pd.DataFrame:
    """Only called after the human approved connecting to the external DB."""
    return pd.read_sql('SELECT * FROM lng_prices_eval ORDER BY "Date"', external_engine(), parse_dates=["Date"])


def _jsonable(obj):
    return json.loads(json.dumps(obj, default=str))


def log_step(run_id: str, agent: str, action: str, detail: dict | None = None) -> None:
    with main_engine().begin() as conn:
        conn.execute(agent_steps.insert().values(
            run_id=run_id, agent=agent, action=action[:255], detail=_jsonable(detail or {}), created_at=_now()))


def create_run(run_id: str, request: str) -> None:
    with main_engine().begin() as conn:
        conn.execute(runs.insert().values(id=run_id, request=request, status="running", created_at=_now(), updated_at=_now()))


def update_run(run_id: str, **fields) -> None:
    fields = {k: (_jsonable(v) if k in ("pending_approval", "result") and v is not None else v) for k, v in fields.items()}
    with main_engine().begin() as conn:
        conn.execute(runs.update().where(runs.c.id == run_id).values(updated_at=_now(), **fields))


def get_run(run_id: str) -> dict | None:
    with main_engine().connect() as conn:
        row = conn.execute(select(runs).where(runs.c.id == run_id)).mappings().first()
        if not row:
            return None
        steps = conn.execute(select(agent_steps).where(agent_steps.c.run_id == run_id).order_by(agent_steps.c.id)).mappings().all()
    return {**dict(row), "steps": [dict(s) for s in steps]}


def list_runs(limit: int = 20) -> list[dict]:
    with main_engine().connect() as conn:
        rows = conn.execute(select(runs.c.id, runs.c.request, runs.c.status, runs.c.created_at)
                            .order_by(runs.c.created_at.desc()).limit(limit)).mappings().all()
    return [dict(r) for r in rows]
