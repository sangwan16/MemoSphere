from pydantic import BaseModel, Field


class CategoryRead(BaseModel):
    id: int
    name: str
    slug: str
    description: str | None = None

    model_config = {"from_attributes": True}


class CategoryCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=80)
    slug: str = Field(..., min_length=1, max_length=80)
    description: str | None = Field(default=None, max_length=255)
