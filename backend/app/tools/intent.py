"""Deterministic request understanding used by the Orchestrator: is the request in scope, and which parameters it sets.

Scope: LNG / JKM market analysis and price forecasting. Supported parameters: target forecast month
(01 or 02/2026 — the months the out-of-sample data covers) and whether an out-of-sample backtest is wanted.
"""
import re

from ..guardrails import fold

SUPPORTED_MONTHS = {1: "2026-01", 2: "2026-02"}  # months ahead of the training data -> target month

# Terms that clearly place a request in the LNG-market domain.
_DOMAIN_RE = re.compile(
    r"\b(lng|jkm|khi hoa long|khi thien nhien|khi tu nhien|khi dot|natural gas|gas|henry hub|brent|"
    r"nang luong|energy|ttf|lpg)\b")
# Generic analytics words: in scope only if the model confirms (the app is an LNG desk, so "dự báo giá tháng tới" is fine).
_GENERIC_RE = re.compile(
    r"\b(du bao|forecast|gia|price|thi truong|market|phan tich|analy[sz]e|analysis|xu huong|trend|bien dong|"
    r"volatility|backtest|mo hinh|model)\b")
_NO_BACKTEST_RE = re.compile(
    r"\b(khong|ko|khoi|bo qua|skip|no|without)\s+(can\s+|phai\s+|dung\s+)?(backtest|kiem dinh|doi chieu|du lieu 2026|db ngoai)")
_MONTH_RE = re.compile(r"\bthang\s*0?(1[0-2]|[1-9])\b(?:\s*(?:/|-|nam)\s*(\d{4}))?")
_EN_MONTH = {"january": 1, "jan": 1, "february": 2, "feb": 2}
_EN_MONTH_RE = re.compile(r"\b(" + "|".join(_EN_MONTH) + r")\b(?:\s*(\d{4}))?")


def scope(text: str) -> str:
    """'in' (clearly LNG), 'maybe' (generic analytics wording — let the LLM decide), or 'out'."""
    folded = fold(text)
    if _DOMAIN_RE.search(folded):
        return "in"
    if _GENERIC_RE.search(folded):
        return "maybe"
    return "out"


def extract_params(text: str) -> dict:
    """Target month and backtest wish, with human-readable notes for anything asked but unsupported."""
    folded = fold(text)
    params = {"months_ahead": 1, "target_month": SUPPORTED_MONTHS[1], "backtest": True, "notes": []}

    mentions = [(int(m), y) for m, y in _MONTH_RE.findall(folded)]
    mentions += [(_EN_MONTH[m], y) for m, y in _EN_MONTH_RE.findall(folded)]
    for month, year in mentions:
        if year and year != "2026":
            continue  # e.g. "tháng 12/2025" refers to the history, not the forecast target
        if month in SUPPORTED_MONTHS:
            params["months_ahead"], params["target_month"] = month, SUPPORTED_MONTHS[month]
        else:
            params["notes"].append(f"Tháng {month:02d} chưa được hỗ trợ (chỉ dự báo 01 hoặc 02/2026) — dùng tháng 01/2026.")
        break

    if _NO_BACKTEST_RE.search(folded):
        params["backtest"] = False
    return params


def quote(text: str, limit: int = 200) -> str:
    """User text made inert for embedding in the markdown report."""
    text = re.sub(r"[`*_\[\]<>#|\\]", "", text).strip()
    return text[:limit] + ("…" if len(text) > limit else "")
