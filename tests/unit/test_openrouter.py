"""Tests for the OpenRouter-backed AI client (src/telemetry-api/ai.py). No network: httpx.post is faked."""

import sys
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src" / "telemetry-api"))
import ai  # noqa: E402


class FakeResponse:
    def __init__(self, status=200, body=None, text=""):
        self.status_code = status
        self._body = body
        self.text = text

    def json(self):
        if self._body is None:
            raise ValueError("no json")
        return self._body


def ok(content="1. Do the thing"):
    return FakeResponse(200, {"choices": [{"message": {"content": content}}]})


def err(status, message="nope"):
    return FakeResponse(status, {"error": {"message": message}})


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")
    monkeypatch.setattr(ai, "PRIMARY_MODEL", "primary/model")
    monkeypatch.setattr(ai, "FALLBACK_MODELS", ["backup/model"])


def scripted(monkeypatch, *responses):
    """Make httpx.post return the given responses in order; records the requested models and headers."""
    calls = []
    queue = list(responses)

    def fake_post(url, json=None, headers=None, timeout=None):
        calls.append({"url": url, "model": json["model"], "headers": headers, "payload": json})
        item = queue.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    monkeypatch.setattr(ai.httpx, "post", fake_post)
    return calls


def test_live_answer(monkeypatch):
    calls = scripted(monkeypatch, ok("hello"))
    r = ai.converse("sys", [{"role": "user", "content": "hi"}])
    assert r.live and r.text == "hello" and r.engine == "OpenRouter" and r.model_id == "primary/model"
    assert calls[0]["url"].endswith("/chat/completions")
    assert calls[0]["headers"]["Authorization"] == "Bearer sk-or-test"
    assert calls[0]["payload"]["messages"][0] == {"role": "system", "content": "sys"}
    assert calls[0]["payload"]["messages"][1] == {"role": "user", "content": "hi"}


def test_missing_key_is_reported_not_called(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY")
    calls = scripted(monkeypatch)
    r = ai.converse("s", [{"role": "user", "content": "x"}])
    assert not r.live and r.fallback_code == "MissingApiKey" and "OPENROUTER_API_KEY" in r.fallback_reason and calls == []


@pytest.mark.parametrize("status,code", [(401, "InvalidApiKey"), (402, "InsufficientCredits"), (403, "Forbidden")])
def test_auth_and_credit_errors_stop_immediately(monkeypatch, status, code):
    calls = scripted(monkeypatch, err(status))
    r = ai.converse("s", [{"role": "user", "content": "x"}])
    assert not r.live and r.fallback_code == code and len(calls) == 1  # no pointless retry on the backup model


@pytest.mark.parametrize("status", [404, 429, 503])
def test_model_specific_errors_try_the_fallback_model(monkeypatch, status):
    calls = scripted(monkeypatch, err(status), ok("from backup"))
    r = ai.converse("s", [{"role": "user", "content": "x"}])
    assert r.live and r.text == "from backup" and r.model_id == "backup/model"
    assert [c["model"] for c in calls] == ["primary/model", "backup/model"]


def test_timeout_then_network_error_reports_last_failure(monkeypatch):
    scripted(monkeypatch, httpx.ReadTimeout("slow"), httpx.ConnectError("down"))
    r = ai.converse("s", [{"role": "user", "content": "x"}])
    assert not r.live and r.fallback_code == "NetworkError" and "Could not reach OpenRouter" in r.fallback_reason


def test_empty_answer_is_a_failure(monkeypatch):
    scripted(monkeypatch, ok("   "), ok(""))
    r = ai.converse("s", [{"role": "user", "content": "x"}])
    assert not r.live and r.fallback_code == "EmptyResponse"


def test_malformed_body_does_not_crash(monkeypatch):
    scripted(monkeypatch, FakeResponse(200, {"unexpected": True}), FakeResponse(200, {"choices": []}))
    r = ai.converse("s", [{"role": "user", "content": "x"}])
    assert not r.live and r.fallback_code == "EmptyResponse"


def test_error_reason_never_contains_the_api_key(monkeypatch, capsys):
    scripted(monkeypatch, err(500, "internal sk-or-test leak?"), err(500, "again"))
    r = ai.converse("s", [{"role": "user", "content": "x"}])
    assert "sk-or-test" not in (r.fallback_reason or "")
    assert "sk-or-test" not in capsys.readouterr().out


def test_no_aws_sdk_dependency_in_ai_module():
    source = Path(ai.__file__).read_text(encoding="utf-8").lower()
    assert "boto3" not in source and "bedrock" not in source
