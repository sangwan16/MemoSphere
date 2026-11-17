import asyncio
import importlib
from types import ModuleType, SimpleNamespace
from typing import Self

import pytest
from fastapi import HTTPException
from openai import OpenAIError

from app.schemas.writing_assistant import WritingSuggestionRequest


@pytest.fixture
def writing_assistant_module(monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    monkeypatch.setenv("JWT_SECRET_KEY", "writing-assistant-test-secret")
    monkeypatch.setenv(
        "DATABASE_URL_POOLED",
        "postgresql+asyncpg://user:password@localhost:5432/memosphere_test",
    )
    return importlib.import_module("app.routes.writing_assistant")


class FakeResponses:
    def __init__(self, output_text: str):
        self.output_text = output_text
        self.request: dict[str, object] | None = None

    async def create(self, **kwargs: object) -> SimpleNamespace:
        self.request = kwargs
        return SimpleNamespace(output_text=self.output_text)


class FakeClient:
    def __init__(self, output_text: str):
        self.responses = FakeResponses(output_text)

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *args: object) -> None:
        return None


def test_suggest_writing_uses_non_stored_response_and_returns_suggestion(
    monkeypatch: pytest.MonkeyPatch,
    writing_assistant_module: ModuleType,
) -> None:
    fake_client = FakeClient("  A clearer draft.  ")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(writing_assistant_module, "AsyncOpenAI", lambda **_: fake_client)

    result = asyncio.run(
        writing_assistant_module.suggest_writing(
            WritingSuggestionRequest(task="polish_content", content="A draft."),
            SimpleNamespace(id=1),
        )
    )

    assert result.suggestion == "A clearer draft."
    assert result.task == "polish_content"
    assert fake_client.responses.request is not None
    assert fake_client.responses.request["store"] is False
    assert fake_client.responses.request["model"] == "gpt-5.4-mini"


def test_suggest_writing_reports_missing_api_key(
    monkeypatch: pytest.MonkeyPatch,
    writing_assistant_module: ModuleType,
) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(HTTPException) as error:
        asyncio.run(
            writing_assistant_module.suggest_writing(
                WritingSuggestionRequest(task="suggest_title", content="A draft."),
                SimpleNamespace(id=1),
            )
        )

    assert error.value.status_code == 503


def test_suggest_writing_reports_provider_errors(
    monkeypatch: pytest.MonkeyPatch,
    writing_assistant_module: ModuleType,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    class FailedResponses:
        async def create(self, **kwargs: object) -> None:
            raise OpenAIError("provider unavailable")

    class FailedClient:
        responses = FailedResponses()

        async def __aenter__(self) -> Self:
            return self

        async def __aexit__(self, *args: object) -> None:
            return None

    monkeypatch.setattr(writing_assistant_module, "AsyncOpenAI", lambda **_: FailedClient())

    with pytest.raises(HTTPException) as error:
        asyncio.run(
            writing_assistant_module.suggest_writing(
                WritingSuggestionRequest(task="suggest_excerpt", content="A draft."),
                SimpleNamespace(id=1),
            )
        )

    assert error.value.status_code == 502
