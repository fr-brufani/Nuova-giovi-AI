from fastapi import APIRouter

from .routes.health import router as health_router
from .routes.integrations import router as integrations_router
from .routes.clients import router as clients_router

__all__ = ["get_api_router"]


def get_api_router() -> APIRouter:
    api_router = APIRouter()
    api_router.include_router(health_router, prefix="/health", tags=["health"])
    api_router.include_router(integrations_router, prefix="/integrations", tags=["integrations"])
    api_router.include_router(clients_router, prefix="/clients", tags=["clients"])
    return api_router

