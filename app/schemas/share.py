from pydantic import BaseModel, Field, field_validator


class ShareCreate(BaseModel):
    recipient_ids: list[int] = Field(min_length=1, max_length=50)

    @field_validator("recipient_ids")
    @classmethod
    def validate_recipients(cls, recipient_ids: list[int]) -> list[int]:
        if any(recipient_id <= 0 for recipient_id in recipient_ids):
            raise ValueError("Recipient IDs must be positive")
        if len(set(recipient_ids)) != len(recipient_ids):
            raise ValueError("Recipient IDs must be unique")
        return recipient_ids


class ShareBatchRead(BaseModel):
    shared_count: int
