from fastapi import APIRouter
from app.api.v1.endpoints import (
    clientes,
    cotacoes,
    dashboard,
    insights,
    obras,
    pedidos,
    produtos,
)

materials_router = APIRouter()

# Vertical endpoints
materials_router.include_router(clientes.router, prefix="/clientes", tags=["clientes"])
materials_router.include_router(obras.router, prefix="/obras", tags=["obras"])
materials_router.include_router(produtos.router, prefix="/produtos", tags=["produtos"])
materials_router.include_router(cotacoes.router, prefix="/cotacoes", tags=["cotacoes"])
materials_router.include_router(pedidos.router, prefix="/pedidos", tags=["pedidos"])
materials_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])

# Insights endpoints (read from engine-owned tables)
materials_router.include_router(insights.router, prefix="/insights", tags=["insights"])

