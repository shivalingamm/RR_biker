"""Aggregate all API routers."""
from fastapi import APIRouter

from app.api.routes import (
    ai,
    auth,
    cart,
    catalogue,
    documents,
    health,
    maintenance,
    mechanics,
    motorcycles,
    notifications,
    orders,
    products,
    reminders,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(motorcycles.router)
api_router.include_router(documents.router)
api_router.include_router(maintenance.router)
api_router.include_router(reminders.router)
api_router.include_router(products.router)
api_router.include_router(cart.router)
api_router.include_router(orders.router)
api_router.include_router(catalogue.router)
api_router.include_router(ai.router)
api_router.include_router(mechanics.router)
api_router.include_router(notifications.router)
