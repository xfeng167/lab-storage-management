from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.db.connection import get_db
from src.test_table import service
from src.test_table.schemas import TestTableCreate, TestTableRead, TestTableUpdate

router = APIRouter()


@router.get("", response_model=list[TestTableRead])
def list_test_table_items(db: Session = Depends(get_db)) -> list[TestTableRead]:
    return service.list_items(db)


@router.post("", response_model=TestTableRead, status_code=status.HTTP_201_CREATED)
def create_test_table_item(
    payload: TestTableCreate,
    db: Session = Depends(get_db),
) -> TestTableRead:
    return service.create_item(db, payload)


@router.patch("/{item_id}", response_model=TestTableRead)
def update_test_table_item(
    item_id: int,
    payload: TestTableUpdate,
    db: Session = Depends(get_db),
) -> TestTableRead:
    item = service.update_item(db, item_id, payload)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    return item


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_test_table_item(item_id: int, db: Session = Depends(get_db)) -> None:
    deleted = service.delete_item(db, item_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
