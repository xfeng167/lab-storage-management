from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints, model_validator


NonBlank40 = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=40)]
NonBlank80 = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]
NonBlank120 = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
NonBlank255 = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]
NonBlankText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=5_000)]
OptionalText = Annotated[str, StringConstraints(strip_whitespace=True, max_length=5_000)] | None

class MaterialCreate(BaseModel):
    material_code: NonBlank80
    material_name: NonBlank255
    material_type: NonBlank80
    description: NonBlankText
    source: NonBlank255
    quantity_available: int = Field(ge=0)
    unit: NonBlank40
    minimum_quantity: int = Field(ge=0)
    qc_status: Literal["pending", "passed", "failed"]
    storage_condition: NonBlank120
    location_id: int | None = Field(default=None, gt=0)

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
    material_name: NonBlank255 | None = None
    material_type: NonBlank80 | None = None
    description: OptionalText = None
    source: NonBlank255 | None = None
    unit: NonBlank40 | None = None
    minimum_quantity: int | None = Field(default=None, ge=0)
    qc_status: Literal["pending", "passed", "failed"] | None = None
    storage_condition: NonBlank120 | None = None
    location_id: int | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def required_columns_cannot_be_null(self) -> "MaterialUpdate":
        required_fields = {
            "material_name", "material_type", "unit", "minimum_quantity",
            "qc_status", "storage_condition",
        }
        null_fields = [
            field for field in required_fields & self.model_fields_set
            if getattr(self, field) is None
        ]
        if null_fields:
            raise ValueError(f"Fields cannot be null: {', '.join(sorted(null_fields))}")
        return self


class QuantityAdjustment(BaseModel):
    quantity_available: int = Field(ge=0)
    reason: NonBlankText


class QuantityChange(BaseModel):
    quantity: int = Field(gt=0)
    reason: NonBlankText


class MaterialMove(BaseModel):
    location_id: int | None = Field(default=None, gt=0)
    reason: NonBlankText
