from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.domain.enums import CounterpartyKind
from app.schemas.common import Money, Schema


class CounterpartyCreate(Schema):
    kind: CounterpartyKind
    name: str = Field(min_length=1, max_length=200)
    phone: str | None = Field(None, max_length=32)
    address: str | None = Field(None, max_length=300)
    note: str | None = Field(None, max_length=1000)


class CounterpartyUpdate(Schema):
    name: str | None = Field(None, min_length=1, max_length=200)
    phone: str | None = Field(None, max_length=32)
    address: str | None = Field(None, max_length=300)
    note: str | None = Field(None, max_length=1000)


class CounterpartyRead(Schema):
    id: UUID
    kind: CounterpartyKind
    name: str
    phone: str | None
    address: str | None
    note: str | None
    balance: Money
    created_at: datetime


class CounterpartyBrief(Schema):
    id: UUID
    kind: CounterpartyKind
    name: str
