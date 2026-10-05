from fastapi import APIRouter

from app.api.v1 import ai_commands, audit, counterparties, invoices, payments, products, statistics, users

api_router = APIRouter()
api_router.include_router(products.products_router)
api_router.include_router(products.stock_router)
api_router.include_router(counterparties.router)
api_router.include_router(invoices.router)
api_router.include_router(payments.payments_router)
api_router.include_router(payments.registers_router)
api_router.include_router(statistics.router)
api_router.include_router(ai_commands.router)
api_router.include_router(users.router)
api_router.include_router(audit.router)
