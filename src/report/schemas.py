from datetime import datetime

from pydantic import BaseModel


class LowStockMaterialRead(BaseModel):
    id: int
    material_code: str
    material_name: str
    quantity_available: int
    quantity_reserved: int
    minimum_quantity: int
    unit: str
    location_id: int | None = None


class PendingOrderRead(BaseModel):
    id: int
    requested_by_user_id: int
    requested_by_username: str
    material_id: int
    material_code: str
    material_name: str
    unit: str
    requested_quantity: int
    status: str
    request_notes: str | None = None
    created_at: datetime | None = None


class RecentInventoryActivityRead(BaseModel):
    id: int
    user_id: int
    username: str
    material_id: int
    material_code: str
    material_name: str
    operation_type: str
    before_value: str
    after_value: str
    reason: str
    created_at: datetime | None = None


class MaterialsByLocationRead(BaseModel):
    location_id: int | None = None
    location_name: str
    material_count: int
    total_quantity_available: int
    total_quantity_reserved: int
