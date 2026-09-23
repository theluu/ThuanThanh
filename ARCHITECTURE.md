# Kiến trúc — LNG Agent Team (Bài toán 2)

## 1. Tổng quan
Hệ thống mô phỏng một nhóm dữ liệu đa tác tử phân tích thị trường LNG và **dự báo giá JKM tháng kế tiếp (01/2026)**.
Mọi con số (thống kê, CV, dự báo, backtest) được tính bởi **tool Python deterministic**; LLM (OpenAI) chỉ lập kế hoạch
và diễn giải → không "bịa số". OpenAI lỗi/hết hạn key → tự chuyển sang Anthropic Claude; không provider nào dùng được → fallback template, pipeline vẫn chạy trọn vẹn.

```
React UI ──HTTP──► FastAPI ──► LangGraph StateGraph (MemorySaver checkpointer, thread_id = run_id)
   ▲  poll 1.5s        │               │
   │                   │               ├─ tools/analysis.py  (EDA)
   │                   │               └─ tools/forecast.py  (features, CV, models, backtest)
   └── trace/report ◄── PostgreSQL lng_main: lng_prices, runs, agent_steps
                       PostgreSQL lng_external: lng_prices_eval   (chỉ truy cập sau khi người dùng Approve)
```

## 2. Các agent & vai trò
| Agent | Vai trò | Input (state) | Output (state) |
|---|---|---|---|
| **Orchestrator** | Hiểu yêu cầu, lập kế hoạch, phân công | `request` | `plan` |
| **Data Engineer** | Đọc dữ liệu 2024–2025 từ DB chính, kiểm tra chất lượng (thiếu, trùng, khoảng ngày); **xin phép** kết nối DB ngoài | — | `data_summary`, `external_approved` |
| **Human (approval gate)** | Duyệt/từ chối kết nối `lng_external` qua LangGraph `interrupt()` | yêu cầu kết nối | quyết định |
| **Data Analyst** | EDA: thống kê, xu hướng tháng/năm, biến động, tương quan mức giá & lợi suất với HH/Brent/DXY/Gold → insight | dữ liệu | `eda`, `analysis_notes` |
| **Data Scientist** | Feature (lag, rolling, exog lag t-1), walk-forward CV 3 fold (train đến cuối tháng → dự báo cả tháng sau), so sánh `naive` / `drift` / `ridge_lag`, chọn MAE thấp nhất, dự báo tháng 01/2026 + khoảng 80%; backtest ngoài mẫu nếu được duyệt | `eda`, `analysis_notes`, `external_approved` | `model_results`, `forecast`, `backtest`, `ds_notes` |
| **Report Writer** | Tổng hợp báo cáo nghiệp vụ Markdown (bảng số deterministic + tóm tắt điều hành bằng LLM) | toàn bộ state | `report`, file `reports/report_<run_id>.md` |

## 3. Workflow
```
START → orchestrator → data_engineer → approval_gate ⏸(interrupt: chờ người dùng)
      → data_analyst → data_scientist → report_writer → END
```
- **Approve** → Data Engineer kết nối `lng_external`, Data Scientist backtest trên 20 phiên 01/2026 (MAE/RMSE/MAPE, coverage khoảng 80%, so sánh mọi model).
- **Reject** → pipeline vẫn hoàn tất, bỏ qua backtest, báo cáo ghi rõ.
- Dữ liệu 2026 **không bao giờ** dùng để huấn luyện.

## 4. Quản lý state & ngữ cảnh
- `AgentState` (TypedDict, `backend/app/agents/state.py`) là "bảng trắng chung": mỗi agent đọc output của agent trước và ghi thêm key của mình
  (vd. Data Scientist đọc `analysis_notes` của Analyst để giải thích; Report Writer đọc toàn bộ).
- **Checkpointer** `MemorySaver` lưu state theo `thread_id = run_id` → graph dừng ở `interrupt()` và **resume** đúng chỗ bằng `Command(resume={"approved": ...})`.
- DataFrame không nằm trong state (chỉ số liệu JSON-serializable); agent đọc dữ liệu qua `Deps` (inject → test được không cần Postgres).

## 5. Logging / trace
- Mỗi hành động agent → `deps.trace()` → bảng `agent_steps` (run_id, agent, action, detail JSON, thời gian) + log console.
- Bảng `runs` lưu trạng thái `running | waiting_approval | completed | failed`, yêu cầu phê duyệt đang chờ, kết quả, báo cáo.
- UI hiển thị timeline trace (click để xem chi tiết JSON), pipeline agent, thẻ phê duyệt, báo cáo và biểu đồ.

## 6. Mô hình & đánh giá
- Tiền xử lý: sort theo ngày, forward-fill (ngày nghỉ/thiếu quote), log số lượng thiếu.
- Validation: expanding walk-forward theo tháng — đúng với bài toán "dự báo tháng kế tiếp", tránh leakage (test kiểm tra feature ngày t không phụ thuộc giá trị ngày t).
- Metrics: MAE (USD/MMBtu, dễ diễn giải), RMSE (phạt sai số lớn), MAPE (% so sánh tương đối).
- Khoảng tin cậy 80%: σ log-return 120 phiên × √h.
- Kết quả thực tế: `naive` thắng CV (MAE ≈ 0.39); backtest 01/2026 MAE ≈ 0.85, MAPE ≈ 7.5% — sai số chủ yếu do cú nhảy +16% ngày 16/01/2026 (sốc thị trường không có tín hiệu trong dữ liệu quá khứ). `ridge_lag` cho kết quả tương đương → random-walk là baseline rất khó vượt với giá hàng hóa ngắn hạn.
