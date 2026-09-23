# LNG Agent Team Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans (native — user yêu cầu triển khai ngay, giới hạn 40').

**Goal:** Team agent LangGraph phân tích + dự báo JKM tháng 01/2026, có HITL trước khi kết nối DB ngoài, API FastAPI, UI React.
**Architecture:** Tools deterministic (pandas/sklearn) tính số; LLM (OpenAI, optional) viết diễn giải; LangGraph StateGraph + MemorySaver + interrupt; trace lưu Postgres.
**Tech Stack:** Python 3.11, FastAPI, LangGraph, SQLAlchemy+psycopg, scikit-learn, langchain-openai; Postgres 16 (compose); React+Vite+recharts+react-markdown.
**Spec:** docs/superpowers/specs/2026-09-23-lng-agent-team-design.md

## Global Constraints
- Eval CSV không bao giờ dùng để train; chỉ đọc sau Approve.
- Exogenous features lag t-1.
- Không có OPENAI_API_KEY → hệ thống vẫn chạy hết (fallback template).

## Review Focus
- NaN trong exogenous (HH/Brent eval rỗng) → ffill, không crash.
- Reject approval → pipeline hoàn tất, không backtest.
- Approve gọi 2 lần / run không tồn tại → 404/409, không crash.
- Không có API key → báo cáo template.
- Postgres chưa chạy → lỗi rõ ràng ở status `failed`.

## File map
- `docker-compose.yml`, `docker/init.sql` (tạo DB lng_external)
- `backend/app/config.py` (env), `db.py` (engines, tables, seed), `tools/forecast.py`, `tools/analysis.py`, `llm.py`, `agents/*.py`, `graph.py`, `main.py`
- `backend/tests/test_forecast.py`, `test_graph.py`
- `frontend/` (Vite React)
- `ARCHITECTURE.md`, `README.md`, `.env.example`, `.env`

## Tasks
### Task 1: Infra + config + DB layer
compose (postgres:16, port 5433, init.sql tạo `lng_external`), config đọc `.env`, `db.py`: `get_main_engine()`, `get_external_engine()`, `init_db()` tạo `runs`, `agent_steps`, `seed_training()`, `seed_external()`, `load_training_df()`, `load_external_df()`, `log_step(run_id, agent, action, detail)`.
Verify: `docker compose up -d`, python seed chạy OK.

### Task 2: Forecast + analysis tools (TDD)
`tools/forecast.py`: `make_features(df)`, `walk_forward_cv(df, models, start)`, `fit_and_forecast(df, model_name, horizon_dates)`, `backtest(forecast_df, actual_df)`; models `naive`, `drift`, `ridge_lag`.
`tools/analysis.py`: `run_eda(df) -> dict`.
Tests: không leakage (feature ngày t chỉ dùng dữ liệu ≤ t-1), forecast đúng số ngày làm việc 01/2026, metrics đúng trên ví dụ nhỏ.

### Task 3: Agents + graph (TDD)
`graph.py`: `build_graph()`, `AgentState`; nodes orchestrator, data_engineer (interrupt), data_analyst, data_scientist, report_writer. Test: chạy graph với data CSV, resume approved=True/False, report không rỗng, backtest có/không.

### Task 4: FastAPI
Endpoints theo spec; background thread chạy graph; approval resume `Command(resume=...)`. Verify bằng curl e2e.

### Task 5: React FE
Form request, timeline steps, approval card, chart, report markdown. Verify build + browser.

### Task 6: Docs + packaging
ARCHITECTURE.md, README, reports/ sample, zip.
