from datetime import datetime

from pydantic import BaseModel, Field


class OrderCreate(BaseModel):
    material_id: int
    requested_quantity: int = Field(gt=0)
    request_notes: str | None = None


class OrderReview(BaseModel):
    outcome_notes: str | None = None


class OrderRead(BaseModel):
    id: int
    requested_by_user_id: int
    material_id: int
    requested_quantity: int
    reserved_quantity: int
    status: str
    request_notes: str | None = None
    reviewed_by_user_id: int | None = None
    reviewed_at: datetime | None = None
    outcome_notes: str | None = None
    is_archived: bool
    archived_at: datetime | None = None
    archived_by_user_id: int | None = None
    archive_reason: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
