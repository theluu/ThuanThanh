# LNG Multi-Agent Analysis & Forecast — Design Spec

## Goal
Mô phỏng một team AI agent (Bài toán 2) phân tích và dự báo giá JKM LNG tháng kế tiếp (01/2026),
với luồng nhiều bước, state dùng chung, trace, và bước xác nhận (HITL) trước khi kết nối DB khác.

## Stack
- Backend: FastAPI, LangGraph (StateGraph + MemorySaver + `interrupt`), SQLAlchemy, pandas, scikit-learn, langchain-openai.
- DB: PostgreSQL 16 qua docker-compose — DB chính `lng_main`, DB "ngoài" `lng_external`.
- FE: React + Vite, recharts, react-markdown. Poll trạng thái run mỗi 1.5s.
- LLM: OpenAI (`OPENAI_API_KEY`, `OPENAI_MODEL` trong `.env`). Không có key → fallback template (số liệu luôn từ tool deterministic).

## Data
- `LNG_market_training_2024_2025.csv` → bảng `lng_prices` (DB chính). Dùng cho EDA, train, walk-forward CV (Q4/2025).
- `LNG_market_evaluation_blintest model_2026_Jan_Feb.csv` → bảng `lng_prices_eval` trong `lng_external`. Chỉ dùng out-of-sample, chỉ đọc sau khi người dùng Approve.
- Target `JKM_Historical`; exogenous HH, Brent, DXY, Gold dùng lag t-1. Missing → ffill (log số lượng).

## Agents
| Agent | Việc |
|---|---|
| Orchestrator | Đọc request, LLM lập plan, khởi tạo state |
| Data Engineer | Seed/đọc `lng_prices`, data-quality report; yêu cầu kết nối `lng_external` → `interrupt()` chờ duyệt; nếu duyệt, nạp eval data |
| Data Analyst | Thống kê mô tả, trung bình tháng, biến động, tương quan (level & return), insight bằng LLM |
| Data Scientist | Feature lag/rolling; so sánh Naive / Drift / Ridge-lag bằng walk-forward CV (MAE, RMSE, MAPE); chọn model tốt nhất; dự báo đệ quy các ngày làm việc tháng 01/2026 + khoảng tin cậy (từ phân phối residual CV); backtest nếu có eval data |
| Report Writer | Tổng hợp báo cáo Markdown (tổng quan, phân tích, dự báo, backtest, rủi ro, khuyến nghị) |

Flow: `orchestrator → data_engineer(HITL) → data_analyst → data_scientist → report_writer → END`.
Reject → bỏ qua backtest, báo cáo ghi rõ.

## State
`AgentState` TypedDict: `run_id, request, plan, data_summary, external_approved, eda, model_results, forecast, backtest, report`.
Trace: mỗi bước agent ghi vào bảng `agent_steps` (run_id, agent, action, detail JSON, created_at). Bảng `runs` lưu status (`running|waiting_approval|completed|failed`), pending approval, report, forecast.

## API
- `POST /api/runs {request}` → `{run_id}` (chạy nền)
- `GET /api/runs/{id}` → run + steps
- `POST /api/runs/{id}/approval {approved}` → resume graph
- `GET /api/prices` → chuỗi training (+eval nếu có) cho chart

## Deliverables
docker-compose.yml, backend/, frontend/, .env.example + .env, ARCHITECTURE.md, reports/ (báo cáo sinh ra), README chạy.

## Testing
pytest: forecasting tools (không leakage, đúng số ngày), graph chạy end-to-end với fake approval & không LLM. E2E thật qua API.
