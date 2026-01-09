from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.api.v1.routers.materials_router import materials_router
from app.api.v1.routers.platform_router import platform_router
from app.web.middleware import TenantResolutionMiddleware
from app.web.router import web_router
from basecore.logging import setup_logging
from basecore.settings import get_settings

# Configurar logging antes de criar app
setup_logging()
settings = get_settings()

app = FastAPI(
    title="BaseCommerce API",
    description="Multi-vertical commerce platform API",
    version="1.0.0",
)

# Tenant Resolution Middleware (for web routes)
app.add_middleware(TenantResolutionMiddleware)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for web UI
static_dir = Path(__file__).parent / "web" / "static"
app.mount("/web/static", StaticFiles(directory=str(static_dir)), name="web_static")

# Include API routers
# Engine-related endpoints have been removed - use /insights/* for engine outputs
app.include_router(platform_router, prefix="/api/v1")
app.include_router(materials_router, prefix="/api/v1")

# Include web router (HTMX server-rendered pages)
app.include_router(web_router, prefix="/web", tags=["web"])


@app.get("/")
async def root():
    """Redirect root to web dashboard or show API info."""
    return RedirectResponse(url="/web/dashboard")


@app.get("/health")
async def health_check():
    return {"status": "ok"}
