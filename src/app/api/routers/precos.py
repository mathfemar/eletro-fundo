"""
routers/precos.py — Endpoints REST para preços live e histórico.

Live:
    POST  /api/precos/live/atualizar            → dispara captura no Yahoo Finance
    GET   /api/precos/live                      → snapshot atual do banco
    GET   /api/precos/live/{cd_ativo}           → preço live de um ativo específico

Histórico:
    POST  /api/precos/historico/carregar        → carga incremental (body: CarregarParams)
    GET   /api/precos/historico/{cd_ativo}      → série histórica de um ativo
    GET   /api/precos/historico/resumo/geral    → contagem de registros por ativo
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.api.models.common import APIResponse

logger = logging.getLogger("app.api.precos")
router = APIRouter(prefix="/api/precos", tags=["Preços"])


# ─── Input models ────────────────────────────────────────────────────────────

class CarregarParams(BaseModel):
    dt_inicio:  Optional[str]       = None   # 'YYYY-MM-DD'; None = incremental automático
    dt_fim:     Optional[str]       = None   # 'YYYY-MM-DD'; None = hoje
    ids_ativo:  Optional[list[int]] = None   # None = todos os mapeados


class AtualizarLiveParams(BaseModel):
    max_workers: int   = 5     # threads paralelas
    delay_s:     float = 0.3   # pausa por thread (rate limit)


# ─── Live ─────────────────────────────────────────────────────────────────────

@router.post("/live/atualizar", response_model=APIResponse)
async def atualizar_live(params: AtualizarLiveParams = AtualizarLiveParams()):
    """
    Dispara captura de preços ao vivo para todos os ativos mapeados
    e faz UPSERT em FAT_PRICING_LIVE.
    """
    try:
        from app.services.precos.pricing_live_service import PricingLiveService
        resultado = PricingLiveService().atualizar_todos(
            max_workers=params.max_workers,
            delay_s=params.delay_s,
        )
        return APIResponse(data=resultado)
    except Exception as exc:
        logger.exception("Erro em /live/atualizar")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/live", response_model=APIResponse)
async def get_live():
    """Retorna o snapshot atual de todos os ativos em FAT_PRICING_LIVE."""
    try:
        from app.services.precos.pricing_live_service import PricingLiveService
        dados = PricingLiveService().get_live()
        return APIResponse(data={"items": dados, "total": len(dados)})
    except Exception as exc:
        logger.exception("Erro em GET /live")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/live/{cd_ativo}", response_model=APIResponse)
async def get_live_ativo(cd_ativo: str):
    """Retorna o preço live de um único ativo pelo CD_ATIVO."""
    try:
        from app.services.precos.pricing_live_service import PricingLiveService
        dado = PricingLiveService().get_live_ativo(cd_ativo.upper())
        if dado is None:
            raise HTTPException(status_code=404, detail=f"Ativo '{cd_ativo}' não encontrado em FAT_PRICING_LIVE")
        return APIResponse(data=dado)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Erro em GET /live/%s", cd_ativo)
        raise HTTPException(status_code=500, detail=str(exc))


# ─── Histórico ────────────────────────────────────────────────────────────────

@router.post("/historico/carregar", response_model=APIResponse)
async def carregar_historico(params: CarregarParams = CarregarParams()):
    """
    Carrega série histórica OHLCV em FAT_ATIVO_PRECO.

    - Se dt_inicio for omitido, carrega apenas a partir da última data no banco (incremental).
    - Se não houver dados para o ativo, parte de 2020-01-01.
    - ids_ativo filtra para um subconjunto. Se omitido, processa todos.
    """
    try:
        from app.services.precos.historico_service import HistoricoService
        resultado = HistoricoService().carregar_historico(
            dt_inicio=params.dt_inicio,
            dt_fim=params.dt_fim,
            ids_ativo=params.ids_ativo,
        )
        return APIResponse(data=resultado)
    except Exception as exc:
        logger.exception("Erro em /historico/carregar")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/historico/resumo/geral", response_model=APIResponse)
async def resumo_historico():
    """Retorna contagem de registros históricos por ativo."""
    try:
        from app.services.precos.historico_service import HistoricoService
        dados = HistoricoService().resumo()
        return APIResponse(data={"items": dados, "total": len(dados)})
    except Exception as exc:
        logger.exception("Erro em GET /historico/resumo/geral")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/historico/{cd_ativo}", response_model=APIResponse)
async def get_historico_ativo(
    cd_ativo:  str,
    dt_inicio: Optional[str] = Query(default=None, description="YYYY-MM-DD"),
    dt_fim:    Optional[str] = Query(default=None, description="YYYY-MM-DD"),
):
    """Retorna série histórica de preços de um ativo."""
    try:
        from app.services.precos.historico_service import HistoricoService
        dados = HistoricoService().get_historico(
            cd_ativo=cd_ativo.upper(),
            dt_inicio=dt_inicio,
            dt_fim=dt_fim,
        )
        return APIResponse(data={"items": dados, "total": len(dados)})
    except Exception as exc:
        logger.exception("Erro em GET /historico/%s", cd_ativo)
        raise HTTPException(status_code=500, detail=str(exc))
