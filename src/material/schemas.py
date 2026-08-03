from pydantic import BaseModel

class MaterialCreate(BaseModel):
    material_code: str
    material_name: str
    material_type: str
    description: str
    source: str
    quantity_available: int
    unit: str
    minimum_quantity: int
    qc_status: str
    storage_condition: str
    location_id: int

class MaterialRead(BaseModel):
    id: int
    material_code: str
    material_name: str
    material_type: str
    description: str
    source: str
    quantity_available: int
    unit: str
    minimum_quantity: int
    qc_status: str
    storage_condition: str
    location_id: int    

class MaterialUpdate(BaseModel):
    material_name: str | None = None
    material_type: str | None = None
    description: str | None = None
    source: str | None = None
    unit: str | None = None
    minimum_quantity: int | None = None
    qc_status: str | None = None
    storage_condition: str | None = None
    location_id: int | None = None
    

