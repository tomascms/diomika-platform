"""Métricas de negócio para monitorização remota (chave ops)."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from core.auth import require_ops
from core.business_analytics import build_business_summary

router = APIRouter(prefix="/ops", tags=["Ops"])


@router.get("/analytics/summary")
def analytics_summary(_role=Depends(require_ops)):
    """Resumo pedidos, contactos e encomendas — requer X-API-Key ops."""
    return build_business_summary()
