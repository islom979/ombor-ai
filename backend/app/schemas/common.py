import math
from decimal import Decimal
from typing import Annotated, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field, PlainSerializer

# JSON'da son (float) sifatida, Python ichida esa aniq Decimal sifatida ishlaydi.
Money = Annotated[Decimal, PlainSerializer(float, return_type=float, when_used="json")]
Quantity = Annotated[Decimal, PlainSerializer(float, return_type=float, when_used="json")]

PositiveQuantity = Annotated[Decimal, Field(gt=0, max_digits=14, decimal_places=3)]
NonNegativeMoney = Annotated[Decimal, Field(ge=0, max_digits=14, decimal_places=2)]
PositiveMoney = Annotated[Decimal, Field(gt=0, max_digits=16, decimal_places=2)]

T = TypeVar("T")


class Schema(BaseModel):
    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)


class Page(Schema, Generic[T]):
    items: list[T]
    total: int
    page: int
    size: int
    pages: int

    @classmethod
    def build(cls, items: list[T], total: int, page: int, size: int) -> "Page[T]":
        return cls(items=items, total=total, page=page, size=size, pages=max(1, math.ceil(total / size)))


class PageParams(Schema):
    page: int = Field(1, ge=1)
    size: int = Field(20, ge=1, le=200)

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.size
