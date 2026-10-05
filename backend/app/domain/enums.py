from enum import StrEnum


class UserRole(StrEnum):
    ADMIN = "admin"
    MANAGER = "manager"
    VIEWER = "viewer"


class CounterpartyKind(StrEnum):
    SUPPLIER = "supplier"
    CLIENT = "client"


class ProductUnit(StrEnum):
    KG = "kg"
    DONA = "dona"
    LITR = "litr"
    METR = "metr"
    QUTI = "quti"


class InvoiceType(StrEnum):
    KIRIM = "kirim"
    CHIQIM = "chiqim"
    UTILIZATSIYA = "utilizatsiya"


class InvoiceStatus(StrEnum):
    ACCEPTED = "accepted"
    CANCELLED = "cancelled"


class PaymentStatus(StrEnum):
    UNPAID = "unpaid"
    PARTIAL = "partial"
    PAID = "paid"


class PaymentMethod(StrEnum):
    CASH = "cash"
    CARD = "card"
    TRANSFER = "transfer"


class PaymentDirection(StrEnum):
    INCOMING = "incoming"
    OUTGOING = "outgoing"


class AiCommandStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class InvoiceSource(StrEnum):
    WEB = "web"
    AI = "ai"
