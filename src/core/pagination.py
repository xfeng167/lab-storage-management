from math import ceil
from typing import Generic, TypeVar

from pydantic import BaseModel


DEFAULT_PAGE_SIZE = 25
MAX_PAGE_SIZE = 100

ItemT = TypeVar("ItemT")


class Page(BaseModel, Generic[ItemT]):
    items: list[ItemT]
    page: int
    size: int
    total: int
    pages: int


def build_page(
    items: list[ItemT],
    *,
    page: int,
    size: int,
    total: int,
) -> Page[ItemT]:
    return Page(
        items=items,
        page=page,
        size=size,
        total=total,
        pages=ceil(total / size) if total else 0,
    )


def page_offset(page: int, size: int) -> int:
    return (page - 1) * size
