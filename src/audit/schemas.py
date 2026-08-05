from datetime import datetime

from pydantic import BaseModel


class InventoryAuditLogRead(BaseModel):
    id: int
    user_id: int
    material_id: int
    operation_type: str
    before_value: str
    after_value: str
    reason: str
    created_at: datetime | None = None
