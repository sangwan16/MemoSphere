import asyncio
import importlib
from types import ModuleType, SimpleNamespace

import pytest
from fastapi import HTTPException
from google.genai.errors import APIError

from app.schemas.writing_assistant import WritingSuggestionRequest


@pytest.fixture
def writing_assistant_module(monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    monkeypatch.setenv("JWT_SECRET_KEY", "writing-assistant-test-secret")
    monkeypatch.setenv(
        "DATABASE_URL_POOLED",
        "postgresql+asyncpg://user:password@localhost:5432/memosphere_test",
    )
    return importlib.import_module("app.routes.writing_assistant")


class FakeModels:
    def __init__(self, output_text: str):
        self.output_text = output_text
        self.request: dict[str, object] | None = None

    async def generate_content(self, **kwargs: object) -> SimpleNamespace:
        self.request = kwargs
        return SimpleNamespace(text=self.output_text)


class FakeAsyncClient:
    def __init__(self, output_text: str):
        self.models = FakeModels(output_text)
        self.closed = False

    async def aclose(self) -> None:
        self.closed = True


class FakeClient:
    def __init__(self, output_text: str):
        self.aio = FakeAsyncClient(output_text)
        self.closed = False

    def close(self) -> None:
        self.closed = True


def test_suggest_writing_calls_gemini_and_returns_suggestion(
    monkeypatch: pytest.MonkeyPatch,
    writing_assistant_module: ModuleType,
) -> None:
    fake_client = FakeClient("  A clearer draft.  ")
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    monkeypatch.delenv("GEMINI_MODEL", raising=False)
    monkeypatch.setattr(writing_assistant_module.genai, "Client", lambda **_: fake_client)

    result = asyncio.run(
        writing_assistant_module.suggest_writing(
            WritingSuggestionRequest(task="polish_content", content="A draft."),
            SimpleNamespace(id=1),
        )
    )

    assert result.suggestion == "A clearer draft."
    assert result.task == "polish_content"
    assert fake_client.aio.models.request is not None
    assert fake_client.aio.models.request["model"] == "gemini-3.8-flash"
    assert fake_client.aio.models.request["config"].max_output_tokens == 1500
    assert fake_client.aio.closed
    assert fake_client.closed


def test_suggest_writing_reports_missing_google_api_key(
    monkeypatch: pytest.MonkeyPatch,
    writing_assistant_module: ModuleType,
) -> None:
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

    with pytest.raises(HTTPException) as error:
        asyncio.run(
            writing_assistant_module.suggest_writing(
                WritingSuggestionRequest(task="suggest_title", content="A draft."),
                SimpleNamespace(id=1),
            )
        )

    assert error.value.status_code == 503


def test_suggest_writing_reports_gemini_errors(
    monkeypatch: pytest.MonkeyPatch,
    writing_assistant_module: ModuleType,
) -> None:
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")

    class FailedModels:
        async def generate_content(self, **kwargs: object) -> None:
            raise APIError(503, {"error": {"message": "provider unavailable"}})

    class FailedAsyncClient:
        models = FailedModels()

        async def aclose(self) -> None:
            return None

    class FailedClient:
        aio = FailedAsyncClient()

        def close(self) -> None:
            return None

    monkeypatch.setattr(writing_assistant_module.genai, "Client", lambda **_: FailedClient())

    with pytest.raises(HTTPException) as error:
        asyncio.run(
            writing_assistant_module.suggest_writing(
                WritingSuggestionRequest(task="suggest_excerpt", content="A draft."),
                SimpleNamespace(id=1),
            )
        )

    assert error.value.status_code == 502
