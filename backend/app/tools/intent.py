"""Deterministic request understanding used by the Orchestrator: is the request in scope, and which parameters it sets.

Scope: LNG / JKM market analysis and price forecasting. Supported parameters: target forecast month
(any month of 2026; only 01 and 02/2026 have out-of-sample actuals to backtest against) and whether a backtest is wanted.
"""
import re
from difflib import SequenceMatcher

from ..guardrails import fold

FORECAST_YEAR = 2026         # training data ends 12/2025, so month N of 2026 is N months ahead
BACKTEST_MONTHS = {1, 2}     # months the external out-of-sample DB covers

# Terms that clearly place a request in the LNG-market domain.
_DOMAIN_RE = re.compile(
    r"\b(lng|jkm|khi hoa long|khi thien nhien|khi tu nhien|khi dot|natural gas|gas|henry hub|brent|"
    r"nang luong|energy|ttf|lpg)\b")
# Generic analytics words: in scope only if the model confirms (the app is an LNG desk, so "dự báo giá tháng tới" is fine).
_GENERIC_RE = re.compile(
    r"\b(du bao|forecast|gia|price|thi truong|market|phan tich|analy[sz]e|analysis|xu huong|trend|bien dong|"
    r"volatility|backtest|mo hinh|model)\b")
# Questions about the desk itself ("bạn làm được gì", "what can you do"): answered with a capabilities note, not a refusal.
_HELP_RE = re.compile(
    r"\b(lam (duoc )?(nhung )?(gi|cai gi)|co the lam|giup (duoc )?(gi|toi)|biet lam|chuc nang|tinh nang|huong dan|"
    r"ban la (ai|gi)|gioi thieu|what can you|what do you do|who are you|how (do i|to) use|help)\b")
# Multi-word / long terms matched fuzzily so typos like "dựa báo", "phan tic", "forcast" still count.
_FUZZY_DOMAIN = ["khi hoa long", "khi thien nhien", "henry hub", "nang luong"]
_FUZZY_GENERIC = ["du bao", "phan tich", "thi truong", "xu huong", "bien dong", "mo hinh", "forecast", "analysis",
                  "predict", "kiem dinh"]
# A month reference ("tháng 1", "tháng tới") on this desk means a forecast horizon.
_HORIZON_RE = re.compile(r"\b(thang\s*0?([1-9]|1[0-2])|thang (toi|sau|ke tiep|ke)|next month)\b")
_NO_BACKTEST_RE = re.compile(
    r"\b(khong|ko|khoi|bo qua|skip|no|without)\s+(can\s+|phai\s+|dung\s+)?(backtest|kiem dinh|doi chieu|du lieu 2026|db ngoai)")
_MONTH_RE = re.compile(r"\bthang\s*0?(1[0-2]|[1-9])\b(?:\s*(?:/|-|nam)\s*(\d{4}))?")
_EN_MONTH = {name: i for i, names in enumerate(
    [("january", "jan"), ("february", "feb"), ("march", "mar"), ("april", "apr"), ("may",), ("june", "jun"),
     ("july", "jul"), ("august", "aug"), ("september", "sep", "sept"), ("october", "oct"), ("november", "nov"),
     ("december", "dec")], start=1) for name in names}
_EN_MONTH_RE = re.compile(r"\b(" + "|".join(_EN_MONTH) + r")\b(?:\s*(\d{4}))?")


def _fuzzy_hit(folded: str, terms: list[str], cutoff: float = 0.8) -> bool:
    """True if some window of words is a near match (typo / dropped letter) for one of the terms."""
    words = re.findall(r"[a-z0-9]+", folded)
    for term in terms:
        n = term.count(" ") + 1
        for i in range(len(words) - n + 1):
            window = " ".join(words[i:i + n])
            if abs(len(window) - len(term)) <= 2 and SequenceMatcher(None, window, term).ratio() >= cutoff:
                return True
    return False


def scope(text: str) -> str:
    """'in' (clearly LNG), 'maybe' (analytics wording — let the LLM decide), 'help' (asks what the desk can do), or 'out'."""
    folded = fold(text)
    if _DOMAIN_RE.search(folded) or _fuzzy_hit(folded, _FUZZY_DOMAIN):
        return "in"
    if _GENERIC_RE.search(folded) or _HORIZON_RE.search(folded) or _fuzzy_hit(folded, _FUZZY_GENERIC):
        return "maybe"
    if _HELP_RE.search(folded):
        return "help"
    return "out"


def extract_params(text: str) -> dict:
    """Target month and backtest wish, with human-readable notes for anything asked but unsupported."""
    folded = fold(text)
    params = {"months_ahead": 1, "target_month": f"{FORECAST_YEAR}-01", "backtest": True,
              "backtest_available": True, "notes": []}

    mentions = [(int(m), y) for m, y in _MONTH_RE.findall(folded)]
    mentions += [(_EN_MONTH[m], y) for m, y in _EN_MONTH_RE.findall(folded)]
    for month, year in mentions:
        if year and int(year) < FORECAST_YEAR:
            continue  # e.g. "tháng 12/2025" refers to the history, not the forecast target
        if year and int(year) > FORECAST_YEAR:
            params["notes"].append(f"Tháng {month:02d}/{year} quá xa dữ liệu (chỉ dự báo đến 12/{FORECAST_YEAR}) "
                                   f"— dùng tháng 01/{FORECAST_YEAR}.")
        else:
            params["months_ahead"], params["target_month"] = month, f"{FORECAST_YEAR}-{month:02d}"
        break

    if params["months_ahead"] not in BACKTEST_MONTHS:
        params["backtest"] = params["backtest_available"] = False
        params["notes"].append(f"Chưa có giá thực tế tháng {params['target_month'][5:]}/{FORECAST_YEAR} "
                               "nên không thể kiểm định ngoài mẫu; dự báo xa càng kém chắc chắn.")
    if _NO_BACKTEST_RE.search(folded):
        params["backtest"] = False
    return params


def quote(text: str, limit: int = 200) -> str:
    """User text made inert for embedding in the markdown report."""
    text = re.sub(r"[`*_\[\]<>#|\\]", "", text).strip()
    return text[:limit] + ("…" if len(text) > limit else "")
