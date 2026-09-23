import pytest

from app import config, llm


class _Resp:
    def __init__(self, content):
        self.content = content


class _Client:
    def __init__(self, result):
        self.result, self.calls = result, 0

    def invoke(self, _messages):
        self.calls += 1
        if isinstance(self.result, Exception):
            raise self.result
        return _Resp(self.result)


class AuthenticationError(Exception):
    status_code = 401


@pytest.fixture
def providers(monkeypatch):
    monkeypatch.setattr(config, "OPENAI_API_KEY", "test-openai")
    monkeypatch.setattr(config, "ANTHROPIC_API_KEY", "test-anthropic")
    monkeypatch.setattr(config, "LLM_PROVIDERS", ["openai", "anthropic"])
    monkeypatch.setattr(llm, "_dead", {})
    clients = {}
    monkeypatch.setattr(llm, "_get_client", lambda p: clients[p])
    return clients


def test_primary_used_when_healthy(providers):
    providers.update(openai=_Client("OpenAI ok"), anthropic=_Client("Claude ok"))
    assert llm.ask("s", "u", "fb") == ("OpenAI ok", "openai")
    assert providers["anthropic"].calls == 0


def test_expired_openai_key_fails_over_and_is_disabled(providers):
    providers.update(openai=_Client(AuthenticationError("Incorrect API key provided")),
                     anthropic=_Client([{"type": "text", "text": "Claude ok"}]))
    assert llm.ask("s", "u", "fb") == ("Claude ok", "anthropic")
    assert llm.ask("s", "u", "fb") == ("Claude ok", "anthropic")
    assert providers["openai"].calls == 1  # disabled after the first auth failure
    assert llm.active_providers() == ["anthropic"]


def test_transient_error_fails_over_without_disabling(providers):
    providers.update(openai=_Client(TimeoutError("read timeout")), anthropic=_Client("Claude ok"))
    assert llm.ask("s", "u", "fb") == ("Claude ok", "anthropic")
    assert llm.active_providers() == ["openai", "anthropic"]


def test_quota_exhausted_is_fatal(providers):
    providers.update(openai=_Client(Exception("Error code: 429 - insufficient_quota")), anthropic=_Client("Claude ok"))
    llm.ask("s", "u", "fb")
    assert "openai" in llm._dead


def test_all_providers_down_uses_template(providers):
    providers.update(openai=_Client(AuthenticationError("bad key")), anthropic=_Client(AuthenticationError("bad key")))
    assert llm.ask("s", "u", "fb") == ("fb", "fallback")
    assert not llm.llm_enabled()


def test_only_backup_configured(providers, monkeypatch):
    monkeypatch.setattr(config, "OPENAI_API_KEY", "")
    providers.update(anthropic=_Client("Claude ok"))
    assert llm.ask("s", "u", "fb") == ("Claude ok", "anthropic")
