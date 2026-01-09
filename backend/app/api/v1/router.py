from fastapi import APIRouter

from app.api.v1.routers.materials_router import materials_router
from app.api.v1.routers.platform_router import platform_router

# Main API router - includes platform (auth) and vertical (materials) routers
# Engine endpoints have been removed - use /insights/* endpoints instead
api_router = APIRouter()
api_router.include_router(platform_router)
api_router.include_router(materials_router)
