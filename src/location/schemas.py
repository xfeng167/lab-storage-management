from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints, model_validator


NonBlank80 = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]
NonBlank120 = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
Optional80 = Annotated[str, StringConstraints(strip_whitespace=True, max_length=80)] | None
OptionalText = Annotated[str, StringConstraints(strip_whitespace=True, max_length=5_000)] | None


class LocationCreate(BaseModel):
    name: NonBlank120
    location_type: NonBlank80
    parent_location_id: int | None = Field(default=None, gt=0)
    temperature_zone: Optional80 = None
    description: OptionalText = None


class LocationRead(BaseModel):
    id: int
    name: str
    location_type: str
    parent_location_id: int | None = None
    temperature_zone: str | None = None
    description: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class LocationUpdate(BaseModel):
    name: NonBlank120 | None = None
    location_type: NonBlank80 | None = None
    parent_location_id: int | None = Field(default=None, gt=0)
    temperature_zone: Optional80 = None
    description: OptionalText = None

    @model_validator(mode="after")
    def required_columns_cannot_be_null(self) -> "LocationUpdate":
        null_fields = [
            field for field in {"name", "location_type"} & self.model_fields_set
            if getattr(self, field) is None
        ]
        if null_fields:
            raise ValueError(f"Fields cannot be null: {', '.join(sorted(null_fields))}")
        return self
