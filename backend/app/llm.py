"""Thin LLM wrapper with provider failover. Agents call `ask()`.

Providers are tried in order (OpenAI → Anthropic backup). A provider whose key is rejected or out of quota is
disabled for the rest of the process, so an expired key costs one failed call, not one per agent. If every
provider fails (or none is configured) the caller's fallback text is used and the pipeline still completes.
"""
import logging
import threading

from . import config
from .guardrails import SYSTEM_GUARD, redact, sanitize_output

log = logging.getLogger("lng.llm")

_clients: dict[str, object] = {}
_dead: dict[str, str] = {}  # provider -> reason it was disabled
_lock = threading.Lock()


def _configured() -> list[str]:
    keys = {"openai": config.OPENAI_API_KEY, "anthropic": config.ANTHROPIC_API_KEY}
    return [p for p in config.LLM_PROVIDERS if keys.get(p)]


def active_providers() -> list[str]:
    return [p for p in _configured() if p not in _dead]


def llm_enabled() -> bool:
    return bool(active_providers())


def _get_client(provider: str):
    with _lock:
        if provider not in _clients:
            if provider == "openai":
                from langchain_openai import ChatOpenAI
                _clients[provider] = ChatOpenAI(model=config.OPENAI_MODEL, api_key=config.OPENAI_API_KEY,
                                                temperature=0.2, timeout=60, max_retries=1)
            elif provider == "anthropic":
                from langchain_anthropic import ChatAnthropic
                _clients[provider] = ChatAnthropic(model=config.ANTHROPIC_MODEL, api_key=config.ANTHROPIC_API_KEY, timeout=60,
                                                   max_retries=1, max_tokens=2048)
            else:
                raise ValueError(f"unknown LLM provider {provider}")
        return _clients[provider]


def _is_fatal(exc: Exception) -> bool:
    """Errors that will not fix themselves on retry: bad/expired/revoked key, no permission, exhausted quota."""
    status = getattr(exc, "status_code", None) or getattr(getattr(exc, "response", None), "status_code", None)
    text = f"{type(exc).__name__} {exc}".lower()
    return (status in (401, 403) or "authentication" in text or "permissiondenied" in text
            or "insufficient_quota" in text or "invalid_api_key" in text or "credit balance" in text)


def _text(content) -> str:
    if isinstance(content, list):  # Anthropic may return content blocks
        return "".join(b.get("text", "") if isinstance(b, dict) else str(b) for b in content)
    return str(content)


def ask(system: str, user: str, fallback: str) -> tuple[str, str]:
    """Return (text, source) where source is the provider name ('openai' / 'anthropic') or 'fallback'.

    LLM text is sanitized before it reaches the report.
    """
    from langchain_core.messages import HumanMessage, SystemMessage
    messages = [SystemMessage(content=system + SYSTEM_GUARD), HumanMessage(content=user)]
    for provider in active_providers():
        try:
            text = sanitize_output(_text(_get_client(provider).invoke(messages).content))
            if text:
                return text, provider
        except Exception as exc:  # network / quota / auth errors must not break the pipeline
            reason = redact(f"{type(exc).__name__}: {exc}")[:300]
            if _is_fatal(exc):
                _dead[provider] = reason
                log.error("LLM provider %s disabled (key expired/invalid or out of quota): %s", provider, reason)
            else:
                log.warning("LLM provider %s failed, trying next: %s", provider, reason)
    return fallback, "fallback"
