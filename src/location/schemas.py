from datetime import datetime

from pydantic import BaseModel


class LocationCreate(BaseModel):
    name: str
    location_type: str
    parent_location_id: int | None = None
    temperature_zone: str | None = None
    description: str | None = None


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
    name: str | None = None
    location_type: str | None = None
    parent_location_id: int | None = None
    temperature_zone: str | None = None
    description: str | None = None
