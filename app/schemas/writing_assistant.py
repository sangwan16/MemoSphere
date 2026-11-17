from typing import Literal

from pydantic import BaseModel, Field, field_validator

WritingTask = Literal["polish_content", "suggest_title", "suggest_excerpt"]


class WritingSuggestionRequest(BaseModel):
    task: WritingTask
    title: str = Field(default="", max_length=200)
    content: str = Field(min_length=1, max_length=5000)

    @field_validator("content")
    @classmethod
    def content_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Content must not be blank")
        return value


class WritingSuggestionResponse(BaseModel):
    task: WritingTask
    suggestion: str
