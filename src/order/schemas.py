from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints


OptionalNotes = Annotated[str, StringConstraints(strip_whitespace=True, max_length=5_000)] | None
ArchiveReason = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=5_000)]
OrderStatus = Literal["submitted", "approved", "rejected", "fulfilled", "canceled"]


class OrderCreate(BaseModel):
    material_id: int = Field(gt=0)
    requested_quantity: int = Field(gt=0)
    request_notes: OptionalNotes = None


class OrderReview(BaseModel):
    outcome_notes: OptionalNotes = None


class OrderArchive(BaseModel):
    reason: ArchiveReason


class OrderRead(BaseModel):
    id: int
    requested_by_user_id: int
    requested_by_username: str
    material_id: int
    requested_quantity: int
    reserved_quantity: int
    status: OrderStatus
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
