"""Thin LLM wrapper. Agents call `ask()`; without an API key (or on error) the caller's fallback text is used."""
import logging

from . import config

log = logging.getLogger("lng.llm")
_client = None


def llm_enabled() -> bool:
    return bool(config.OPENAI_API_KEY)


def _get_client():
    global _client
    if _client is None:
        from langchain_openai import ChatOpenAI
        _client = ChatOpenAI(model=config.OPENAI_MODEL, api_key=config.OPENAI_API_KEY, temperature=0.2, timeout=60)
    return _client


def ask(system: str, user: str, fallback: str) -> tuple[str, str]:
    """Return (text, source) where source is 'llm' or 'fallback'."""
    if not llm_enabled():
        return fallback, "fallback"
    try:
        from langchain_core.messages import HumanMessage, SystemMessage
        resp = _get_client().invoke([SystemMessage(content=system), HumanMessage(content=user)])
        return str(resp.content).strip(), "llm"
    except Exception as exc:  # network / quota errors must not break the pipeline
        log.warning("LLM call failed, using fallback: %s", exc)
        return fallback, "fallback"
