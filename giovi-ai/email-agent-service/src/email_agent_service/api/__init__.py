from fastapi import APIRouter

from .routes.health import router as health_router
from .routes.integrations import router as integrations_router
from .routes.clients import router as clients_router
from .routes.property_mappings import router as property_mappings_router
from .routes.test.attachments import router as test_attachments_router
from .routes.test.conversations import router as test_conversations_router
from .routes.test.users import router as test_users_router

__all__ = ["get_api_router"]


def get_api_router() -> APIRouter:
    api_router = APIRouter()
    api_router.include_router(health_router, prefix="/health", tags=["health"])
    api_router.include_router(integrations_router, prefix="/integrations", tags=["integrations"])
    api_router.include_router(clients_router, prefix="/clients", tags=["clients"])
    api_router.include_router(property_mappings_router, prefix="/property-mappings", tags=["property_mappings"])
    
    # Test endpoints
    test_router = APIRouter()
    test_router.include_router(test_users_router, tags=["test"])
    test_router.include_router(test_conversations_router, tags=["test"])
    test_router.include_router(test_attachments_router, tags=["test"])
    api_router.include_router(test_router, prefix="/test", tags=["test"])
    
    return api_router

