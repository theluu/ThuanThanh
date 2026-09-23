"""Report Writer: turns the team's shared state into the business deliverable (markdown report).

Tables/numbers are rendered deterministically from state; the LLM writes the narrative sections only.
"""
import json
from datetime import datetime

from .. import config
from ..llm import ask
from .deps import Deps
from .state import AgentState

NAME = "Report Writer"


def _metrics_table(rows: dict) -> str:
    out = ["| Mô hình | MAE | RMSE | MAPE (%) |", "|---|---|---|---|"]
    out += [f"| {m} | {v['MAE']:.3f} | {v['RMSE']:.3f} | {v['MAPE']:.2f} |" for m, v in rows.items()]
    return "\n".join(out)


def build_report(state: AgentState, summary_text: str) -> str:
    eda, mr, fc, bt, ds = state["eda"], state["model_results"], state["forecast"], state.get("backtest"), state["data_summary"]
    month = fc[0]["Date"][:7]
    lt = eda["latest"]
    parts = [
        f"# Báo cáo phân tích & dự báo giá JKM LNG — tháng {month}",
        f"_Tạo bởi nhóm agent (Orchestrator → Data Engineer → Data Analyst → Data Scientist → Report Writer) · run `{state['run_id']}` · {datetime.now():%Y-%m-%d %H:%M}_",
        "## 1. Tóm tắt điều hành", summary_text,
        "## 2. Dữ liệu (Data Engineer)",
        f"- Nguồn: DB chính `lng_prices`, {ds['rows']} phiên, {ds['start']} → {ds['end']}. Trùng ngày: {ds['duplicates']}.",
        f"- Giá trị thiếu trước xử lý: {ds['missing_before']} → xử lý: {ds['method']}.",
        f"- Kết nối DB ngoài (dữ liệu 2026): **{'đã được phê duyệt' if state.get('external_approved') else 'bị từ chối — không backtest'}**.",
        "## 3. Phân tích thị trường (Data Analyst)",
        f"- JKM cuối kỳ ({lt['date']}): **{lt['JKM']} USD/MMBtu**; thay đổi ~30 phiên: {lt['change_30d_pct']}%; spread JKM–HH: {lt['jkm_hh_spread']}.",
        f"- Đỉnh: {eda['extremes']['max']['value']} ({eda['extremes']['max']['date']}); đáy: {eda['extremes']['min']['value']} ({eda['extremes']['min']['date']}).",
        f"- Biến động năm hóa: {eda['volatility']['annualized_full']} (toàn kỳ), {eda['volatility']['annualized_last20d']} (20 phiên gần nhất).",
        "\n| Biến | Tương quan mức giá | Tương quan lợi suất ngày |\n|---|---|---|\n" + "\n".join(
            f"| {k} | {eda['correlation_levels'][k]} | {eda['correlation_returns'][k]} |" for k in eda["correlation_levels"]),
        "\n**Nhận định:**\n\n" + state.get("analysis_notes", ""),
        "## 4. Mô hình & dự báo (Data Scientist)",
        "Walk-forward CV: huấn luyện đến cuối tháng, dự báo toàn bộ tháng kế tiếp (3 fold: 10, 11, 12/2025) — mô phỏng đúng bài toán thực tế.",
        _metrics_table(mr["cv"]["summary"]),
        f"\nMô hình được chọn: **{mr['chosen']}**. Dự báo trung bình tháng {month}: **{mr['forecast_mean']:.3f} USD/MMBtu** "
        f"(dải {mr['forecast_min']:.3f} – {mr['forecast_max']:.3f}).",
        "\n| Ngày | Dự báo | Cận dưới 80% | Cận trên 80% |\n|---|---|---|---|\n" + "\n".join(
            f"| {r['Date']} | {r['forecast']:.3f} | {r['lower']:.3f} | {r['upper']:.3f} |" for r in fc),
        "\n**Giải thích:**\n\n" + state.get("ds_notes", ""),
    ]
    if bt:
        m = bt["metrics"]
        parts += [
            "## 5. Kiểm định ngoài mẫu (backtest với dữ liệu thực tế 2026)",
            f"- {bt['n_days']} phiên: MAE **{m['MAE']:.3f}**, RMSE {m['RMSE']:.3f}, MAPE **{m['MAPE']:.2f}%**.",
            f"- Trung bình thực tế {bt['actual_mean']:.3f} vs dự báo {bt['forecast_mean']:.3f}; tỷ lệ ngày nằm trong khoảng 80%: {bt['interval_coverage']*100:.0f}%.",
            "\nSo sánh tất cả mô hình trên dữ liệu ngoài mẫu:\n\n" + _metrics_table(bt["all_models"]),
        ]
    else:
        parts += ["## 5. Kiểm định ngoài mẫu", "Không thực hiện do người dùng từ chối kết nối DB ngoài."]
    parts += [
        "## 6. Rủi ro & hạn chế",
        "- Biến ngoại sinh tương lai chưa biết → giữ nguyên giá trị cuối (giả định). Cú sốc thời tiết/địa chính trị không nằm trong dữ liệu.",
        "- Dữ liệu chỉ 2 năm, tần suất ngày → mùa vụ năm chỉ quan sát 2 chu kỳ.",
        "- Khoảng tin cậy dựa trên biến động 120 phiên gần nhất, giả định log-return chuẩn.",
    ]
    return "\n\n".join(parts)


def make_node(deps: Deps):
    def report_writer(state: AgentState) -> AgentState:
        run_id = state["run_id"]
        mr, bt = state["model_results"], state.get("backtest")
        facts = {"latest": state["eda"]["latest"], "forecast_mean": mr["forecast_mean"], "chosen_model": mr["chosen"],
                 "cv": mr["cv"]["summary"][mr["chosen"]], "backtest": bt and bt["metrics"],
                 "analyst": state.get("analysis_notes"), "scientist": state.get("ds_notes")}
        summary, src = ask(
            "Bạn là trưởng nhóm phân tích. Viết tóm tắt điều hành 4-5 câu tiếng Việt cho lãnh đạo: hiện trạng thị trường JKM, "
            "dự báo tháng tới (số trung bình), độ tin cậy, kết quả backtest (nếu có), khuyến nghị. Chỉ dùng số liệu được cung cấp. "
            "Lưu ý: naive = giữ nguyên giá cuối (không hàm ý tăng/giảm); drift = ngoại suy xu hướng 60 phiên; ridge_lag = hồi quy trên lag.",
            json.dumps(facts, ensure_ascii=False, default=str),
            fallback=(f"JKM kết thúc kỳ ở {state['eda']['latest']['JKM']} USD/MMBtu. Nhóm dự báo giá trung bình tháng tới "
                      f"≈ {mr['forecast_mean']:.3f} USD/MMBtu bằng mô hình {mr['chosen']}."),
        )
        report = build_report(state, summary)
        config.REPORTS_DIR.mkdir(exist_ok=True)
        path = config.REPORTS_DIR / f"report_{run_id}.md"
        path.write_text(report, encoding="utf-8")
        deps.trace(run_id, NAME, "Compiled final report", {"path": str(path.name), "chars": len(report), "source": src})
        return {"report": report, "report_path": str(path), "llm_calls": {**state.get("llm_calls", {}), "report_writer": src}}
    return report_writer
