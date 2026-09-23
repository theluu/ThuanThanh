# LNG Agent Team — Bài toán 2 (AI Agent)

Team agent (Orchestrator, Data Engineer, Data Analyst, Data Scientist, Report Writer) phân tích & dự báo giá JKM LNG tháng kế tiếp.
Stack: **FastAPI + LangGraph + PostgreSQL + React (Vite)**. Kiến trúc: xem [ARCHITECTURE.md](ARCHITECTURE.md). Báo cáo mẫu: [reports/SAMPLE_REPORT.md](reports/SAMPLE_REPORT.md).

## Chạy
```bash
cp .env.example .env            # điền OPENAI_API_KEY (tùy chọn — không có key vẫn chạy bằng template)
docker compose up -d            # Postgres 16 tại localhost:5433 (DB lng_main + lng_external)

cd backend && python3.11 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn app.main:app --port 8077      # tự tạo bảng & nạp CSV khi khởi động

cd ../frontend && npm install && npm run dev    # http://localhost:5177 (proxy /api → 8077)
```
Trên UI: bấm **Chạy team agent** → khi Data Engineer xin kết nối DB ngoài, bấm **Approve/Reject** → xem Trace, Báo cáo, Biểu đồ.

## API
| Method | Path | Mô tả |
|---|---|---|
| POST | `/api/runs` `{request}` | Khởi chạy team agent (nền) |
| GET | `/api/runs/{id}` | Trạng thái, trace, yêu cầu phê duyệt, báo cáo |
| POST | `/api/runs/{id}/approval` `{approved}` | Duyệt/từ chối kết nối DB ngoài (409 nếu không chờ duyệt) |
| GET | `/api/prices?include_eval=` | Chuỗi giá cho biểu đồ |

## Test
```bash
cd backend && .venv/bin/python -m pytest -q    # tools (leakage, horizon, metrics, CV) + graph (approve/reject, thứ tự agent)
```
