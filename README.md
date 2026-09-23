# LNG Agent Team — Bài toán 2 (AI Agent)

Team agent (Orchestrator, Data Engineer, Data Analyst, Data Scientist, Report Writer) phân tích & dự báo giá JKM LNG tháng kế tiếp.
Stack: **FastAPI + LangGraph + PostgreSQL + React (Vite)**. Kiến trúc: xem [ARCHITECTURE.md](ARCHITECTURE.md). Báo cáo mẫu: [reports/SAMPLE_REPORT.md](reports/SAMPLE_REPORT.md).

## Chạy
```bash
cp .env.example .env            # điền OPENAI_API_KEY + ANTHROPIC_API_KEY (dự phòng) — tùy chọn, không có key vẫn chạy bằng template
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
| GET | `/api/prices?run_id=` | Chuỗi giá cho biểu đồ (chuỗi 2026 chỉ trả về khi run đã hoàn tất **và** được duyệt) |

## LLM failover
Thứ tự: **OpenAI → Anthropic Claude (dự phòng) → template**. Khi một provider trả lỗi xác thực (key hết hạn/sai, 401/403) hoặc hết quota, nó bị tắt đến khi restart backend và mọi lời gọi chuyển sang provider kế tiếp; lỗi tạm thời (timeout, 5xx) chỉ chuyển provider cho lần gọi đó. `GET /api/health` trả `providers` đang hoạt động; trace của mỗi agent ghi `source` = provider đã dùng.

## Bảo mật & guardrails
| Lớp | Guardrail | Code |
|---|---|---|
| Input | Chuẩn hóa, bỏ ký tự điều khiển/zero-width, tối đa 500 ký tự, chặn mẫu prompt injection (EN/VI, không phân biệt dấu) → HTTP 400 | `app/guardrails.py::check_request` |
| Prompt | Yêu cầu người dùng được bọc trong `<user_request>` và mọi system prompt có thêm quy tắc an toàn (coi là dữ liệu, không lộ key/cấu hình) | `wrap_untrusted`, `SYSTEM_GUARD` |
| Output LLM | Loại bỏ HTML, ảnh/link markdown & URL (chống exfiltration khi render báo cáo), che key/credentials, giới hạn độ dài | `sanitize_output` |
| HITL | Phê duyệt atomic (chỉ áp dụng 1 lần, 409 nếu gửi lại); dữ liệu DB ngoài không thể lấy qua `/api/prices` nếu run chưa được duyệt | `db.claim_approval`, `main.prices` |
| API | CORS theo `CORS_ORIGINS`, token `API_TOKEN` (so sánh constant-time), rate limit theo IP, giới hạn số run đồng thời, `run_id` phải là UUID, security headers, lỗi trả về đã được che credentials | `app/main.py` |

Không có `API_TOKEN` thì API mở — chỉ dùng cho local. Rate limit lưu trong bộ nhớ (một process); khi scale nhiều worker cần chuyển sang Redis/gateway.

## Test
```bash
cd backend && .venv/bin/python -m pytest -q    # tools (leakage, horizon, metrics, CV) + graph (approve/reject, thứ tự agent)
```
