import asyncio
import importlib
from types import ModuleType, SimpleNamespace
from typing import Any

import pytest
from fastapi import HTTPException
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import Select


@pytest.fixture
def posts_module(monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    monkeypatch.setenv("JWT_SECRET_KEY", "post-drafts-test-secret")
    monkeypatch.setenv(
        "DATABASE_URL_POOLED",
        "postgresql+asyncpg://user:password@localhost:5432/memosphere_test",
    )
    return importlib.import_module("app.routes.posts")


class FakeResult:
    def __init__(self, rows: list[object] | None = None, row: object | None = None):
        self.rows = rows or []
        self.row = row

    def scalars(self) -> "FakeResult":
        return self

    def all(self) -> list[object]:
        return self.rows

    def scalar_one_or_none(self) -> object | None:
        return self.row


class FakeDatabase:
    def __init__(self, result: FakeResult | None = None):
        self.result = result or FakeResult()
        self.statement: Select[Any] | None = None

    async def execute(self, statement: Select[Any]) -> FakeResult:
        self.statement = statement
        return self.result


def test_list_my_drafts_filters_by_owner_and_draft_status(
    posts_module: ModuleType,
) -> None:
    database = FakeDatabase()

    drafts = asyncio.run(
        posts_module.list_my_drafts(database, SimpleNamespace(id=42))
    )

    assert database.statement is not None
    compiled = database.statement.compile(dialect=postgresql.dialect())
    assert drafts == []
    assert "posts.is_draft IS true" in str(compiled)
    assert 42 in compiled.params.values()


def test_get_my_draft_returns_not_found_when_missing(
    posts_module: ModuleType,
) -> None:
    database = FakeDatabase(FakeResult(row=None))

    with pytest.raises(HTTPException) as error:
        asyncio.run(
            posts_module.get_my_draft(
                post_id=10,
                db=database,
                current_user=SimpleNamespace(id=42),
            )
        )

    assert error.value.status_code == 404
