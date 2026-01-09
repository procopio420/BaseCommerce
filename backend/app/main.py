from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.routers.materials_router import materials_router
from app.api.v1.routers.platform_router import platform_router
from basecore.logging import setup_logging
from basecore.settings import get_settings

# Configurar logging antes de criar app
setup_logging()
settings = get_settings()

app = FastAPI(
    title="Construção SaaS API",
    description="API para gestão de cotações e pedidos (local dev)",
    version="1.0.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers for local development
# Engine-related endpoints have been removed - use /insights/* for engine outputs
app.include_router(platform_router, prefix="/api/v1")
app.include_router(materials_router, prefix="/api/v1")


@app.get("/")
async def root():
    return {"message": "Construção SaaS API", "version": "1.0.0", "docs": "/docs"}


@app.get("/health")
async def health_check():
    return {"status": "ok"}
