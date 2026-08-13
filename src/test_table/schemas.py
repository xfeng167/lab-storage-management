from pydantic import BaseModel


class TestTableCreate(BaseModel):
    name: str


class TestTableUpdate(BaseModel):
    name: str


class TestTableRead(BaseModel):
    id: int
    name: str
