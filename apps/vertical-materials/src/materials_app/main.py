from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.routers.materials_router import materials_router
from basecore.logging import setup_logging
from basecore.settings import get_settings

setup_logging()
settings = get_settings()

app = FastAPI(
    title="Materials Service",
    description="Vertical materials management API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(materials_router, prefix="/api/v1")


@app.get("/")
async def root():
    return {"message": "Materials Service", "version": "1.0.0"}


@app.get("/health")
async def health_check():
    return {"status": "ok"}

