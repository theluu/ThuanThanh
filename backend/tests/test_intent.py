import pytest

from app.tools.intent import extract_params, quote, scope


@pytest.mark.parametrize("text,expected", [
    ("Phân tích thị trường LNG 2024–2025 và dự báo giá JKM tháng kế tiếp", "in"),
    ("dự báo khí hóa lỏng tháng tới", "in"),
    ("Brent ảnh hưởng thế nào tới giá?", "in"),
    ("Dự báo giá tháng tới", "maybe"),
    ("Dựa báo tháng 1 cho tôi", "maybe"),  # typo of "dự báo"
    ("Dự bảo tháng 2", "maybe"),
    ("forcast JKM", "in"),
    ("phan tic thi truong khi hoa lỏng", "in"),
    ("Bạn làm được những gì", "help"),
    ("What can you do?", "help"),
    ("Hôm nay ăn gì", "out"),
    ("s", "out"),
    ("Viết cho tôi một bài thơ", "out"),
])
def test_scope(text, expected):
    assert scope(text) == expected


@pytest.mark.parametrize("text,month,ahead", [
    ("Dự báo JKM tháng tới", "2026-01", 1),
    ("Dự báo JKM tháng 2", "2026-02", 2),
    ("Dự báo JKM tháng 02/2026", "2026-02", 2),
    ("Forecast JKM for February 2026", "2026-02", 2),
    ("Phân tích JKM tháng 12/2025 rồi dự báo tháng 1", "2026-01", 1),
])
def test_target_month(text, month, ahead):
    p = extract_params(text)
    assert (p["target_month"], p["months_ahead"]) == (month, ahead) and not p["notes"]


@pytest.mark.parametrize("text,month", [
    ("Phân tích thị trường LNG 2024–2025 và dự báo giá JKM tháng 10", "2026-10"),
    ("Dự báo JKM tháng 5", "2026-05"),
    ("Forecast JKM for October 2026", "2026-10"),
])
def test_later_2026_month_is_forecast_without_backtest(text, month):
    p = extract_params(text)
    assert p["target_month"] == month and p["months_ahead"] == int(month[5:])
    assert p["backtest"] is False and p["backtest_available"] is False and "Chưa có giá thực tế" in p["notes"][0]


def test_month_beyond_2026_falls_back_with_note():
    p = extract_params("Dự báo JKM tháng 3/2027")
    assert p["target_month"] == "2026-01" and "quá xa" in p["notes"][0]


@pytest.mark.parametrize("text,wanted", [
    ("Dự báo JKM tháng tới", True),
    ("Dự báo JKM tháng tới, không cần backtest", False),
    ("Dự báo JKM, bỏ qua kiểm định", False),
    ("Forecast JKM without backtest", False),
])
def test_backtest_flag(text, wanted):
    assert extract_params(text)["backtest"] is wanted


def test_quote_strips_markdown():
    assert quote("**x** [a](b) `c` <d>") == "x a(b) c d"
