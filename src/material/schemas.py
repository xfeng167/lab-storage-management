from datetime import datetime

from pydantic import BaseModel, Field

class MaterialCreate(BaseModel):
    material_code: str
    material_name: str
    material_type: str
    description: str
    source: str
    quantity_available: int = Field(ge=0)
    unit: str
    minimum_quantity: int = Field(ge=0)
    qc_status: str
    storage_condition: str
    location_id: int | None = None

class MaterialRead(BaseModel):
    id: int
    material_code: str
    material_name: str
    material_type: str
    description: str | None = None
    source: str | None = None
    quantity_available: int
    quantity_reserved: int
    unit: str
    minimum_quantity: int
    availability_status: str
    qc_status: str
    storage_condition: str | None = None
    location_id: int | None = None
    is_archived: bool
    archived_at: datetime | None = None
    archived_by_user_id: int | None = None
    archive_reason: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None  

class MaterialUpdate(BaseModel):
    material_name: str | None = None
    material_type: str | None = None
    description: str | None = None
    source: str | None = None
    unit: str | None = None
    minimum_quantity: int | None = Field(default=None, ge=0)
    qc_status: str | None = None
    storage_condition: str | None = None
    location_id: int | None = None


class QuantityAdjustment(BaseModel):
    quantity_available: int = Field(ge=0)
    reason: str


class QuantityChange(BaseModel):
    quantity: int = Field(gt=0)
    reason: str


class MaterialMove(BaseModel):
    location_id: int | None = None
    reason: str
