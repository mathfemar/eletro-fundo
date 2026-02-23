"""
routers/ativos.py — Endpoints REST para cadastro / metadados de ativos.

GET  /api/ativos             → lista todos os ativos com informações completas
GET  /api/ativos/meta        → tabelas de dimensão (tipos, setores, ...)
GET  /api/ativos/{cd_ativo}  → detalhe de um único ativo
POST /api/ativos             → criar novo ativo + mapping
PUT  /api/ativos/{cd_ativo}  → atualizar ativo + mapping existentes
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.api.models.common import APIResponse
from app.services.db_connection import query, managed_connection

logger = logging.getLogger("app.api.ativos")
router = APIRouter(prefix="/api/ativos", tags=["Ativos"])

# ─── SQL auxiliar ──────────────────────────────────────────────────────────────────

_SQL_ATIVOS = """
    SELECT
        da.ID_ATIVO,
        da.CD_ATIVO,
        da.ID_TIPO_ATIVO,
        da.ID_SETOR_FILHO,
        da.ID_SETOR_PAI,
        da.DT_EMISSAO,
        da.DT_VENCIMENTO,
        da.CD_SELIC,
        da.MOEDA,
        da.PRECO_ONLINE,
        da.FATOR_PRECO,
        da.CALL_PUT,
        da.LOTE,
        dam.CD_BBG,
        dam.CD_CUSIP,
        dam.CD_FIGI,
        dam.CD_ISIN,
        dam.CD_YF,
        dta.TIPO_ATIVO,
        dta.ClasseRisco,
        dsf.SetorFilho,
        dsp.SetorPai
    FROM DIM_ATIVO da
    LEFT JOIN DIM_ATIVO_MAPPING dam ON da.ID_ATIVO = dam.ID_ATIVO
    LEFT JOIN DIM_TIPO_ATIVO    dta ON dta.ID_TIPO_ATIVO = da.ID_TIPO_ATIVO
    LEFT JOIN DIM_SETOR_FILHO   dsf ON dsf.ID_SETOR_FILHO = da.ID_SETOR_FILHO
    LEFT JOIN DIM_SETOR_PAI     dsp ON dsp.ID_SETOR_PAI   = da.ID_SETOR_PAI
"""

# ─── Modelos de entrada ──────────────────────────────────────────────────────────────

class AtivoInput(BaseModel):
    # DIM_ATIVO
    CD_ATIVO: str
    ID_TIPO_ATIVO: Optional[int] = None
    DT_EMISSAO: Optional[str] = None
    DT_VENCIMENTO: Optional[str] = None
    CD_SELIC: Optional[str] = None
    ID_SETOR_PAI: Optional[int] = None
    ID_SETOR_FILHO: Optional[int] = None
    MOEDA: Optional[str] = None
    PRECO_ONLINE: Optional[int] = None
    FATOR_PRECO: Optional[float] = None
    CALL_PUT: Optional[str] = None
    LOTE: Optional[float] = None
    # DIM_ATIVO_MAPPING
    CD_BBG: Optional[str] = None
    CD_YF: Optional[str] = None
    CD_FIGI: Optional[str] = None
    CD_ISIN: Optional[str] = None
    CD_CUSIP: Optional[str] = None


# ─── Endpoints ────────────────────────────────────────────────────────────────────

@router.get("", response_model=APIResponse)
async def listar_ativos():
    """Retorna todos os ativos com metadados completos."""
    try:
        df = query(f"{_SQL_ATIVOS} ORDER BY da.CD_ATIVO")
        dados = df.to_dict("records")
        return APIResponse(data={"items": dados, "total": len(dados)})
    except Exception as exc:
        logger.exception("Erro em GET /ativos")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/meta", response_model=APIResponse)
async def get_meta():
    """Retorna tabelas de dimensão para popular os selects do formulário."""
    try:
        tipos = query(
            "SELECT ID_TIPO_ATIVO, TIPO_ATIVO, ClasseRisco FROM DIM_TIPO_ATIVO ORDER BY TIPO_ATIVO"
        ).to_dict("records")
        setores_pai = query(
            "SELECT ID_SETOR_PAI, SetorPai FROM DIM_SETOR_PAI ORDER BY SetorPai"
        ).to_dict("records")
        setores_filho = query(
            "SELECT ID_SETOR_FILHO, SetorFilho FROM DIM_SETOR_FILHO ORDER BY SetorFilho"
        ).to_dict("records")
        return APIResponse(data={
            "tipos": tipos,
            "setores_pai": setores_pai,
            "setores_filho": setores_filho,
        })
    except Exception as exc:
        logger.exception("Erro em GET /ativos/meta")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/{cd_ativo}", response_model=APIResponse)
async def get_ativo(cd_ativo: str):
    """Retorna detalhe de um único ativo."""
    try:
        df = query(f"{_SQL_ATIVOS} WHERE da.CD_ATIVO = ?", params=(cd_ativo.upper(),))
        records = df.to_dict("records")
        if not records:
            raise HTTPException(status_code=404, detail=f"Ativo '{cd_ativo}' não encontrado")
        return APIResponse(data=records[0])
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Erro em GET /ativos/%s", cd_ativo)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("", response_model=APIResponse, status_code=201)
async def criar_ativo(payload: AtivoInput):
    """Cria um novo ativo em DIM_ATIVO + DIM_ATIVO_MAPPING."""
    cd = payload.CD_ATIVO.strip().upper()
    if not cd:
        raise HTTPException(status_code=422, detail="CD_ATIVO não pode ser vazio")

    # Verifica duplicata
    existe = query("SELECT ID_ATIVO FROM DIM_ATIVO WHERE CD_ATIVO = ?", params=(cd,))
    if not existe.empty:
        raise HTTPException(status_code=409, detail=f"Ativo '{cd}' já existe")

    try:
        with managed_connection() as conn:
            cur = conn.execute(
                """
                INSERT INTO DIM_ATIVO
                    (CD_ATIVO, ID_TIPO_ATIVO, DT_EMISSAO, DT_VENCIMENTO, CD_SELIC,
                     ID_SETOR_PAI, ID_SETOR_FILHO, MOEDA, PRECO_ONLINE, FATOR_PRECO, CALL_PUT, LOTE)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (cd, payload.ID_TIPO_ATIVO, payload.DT_EMISSAO, payload.DT_VENCIMENTO,
                 payload.CD_SELIC, payload.ID_SETOR_PAI, payload.ID_SETOR_FILHO,
                 payload.MOEDA, payload.PRECO_ONLINE, payload.FATOR_PRECO,
                 payload.CALL_PUT, payload.LOTE),
            )
            novo_id = cur.lastrowid
            conn.execute(
                """
                INSERT INTO DIM_ATIVO_MAPPING
                    (ID_ATIVO, CD_ATIVO, CD_BBG, CD_YF, CD_FIGI, CD_ISIN, CD_CUSIP)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (novo_id, cd, payload.CD_BBG, payload.CD_YF,
                 payload.CD_FIGI, payload.CD_ISIN, payload.CD_CUSIP),
            )
        logger.info("Ativo criado: %s (ID %s)", cd, novo_id)
        return APIResponse(data={"CD_ATIVO": cd, "ID_ATIVO": novo_id})
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Erro em POST /ativos")
        raise HTTPException(status_code=500, detail=str(exc))


@router.put("/{cd_ativo}", response_model=APIResponse)
async def atualizar_ativo(cd_ativo: str, payload: AtivoInput):
    """Atualiza DIM_ATIVO e DIM_ATIVO_MAPPING para um ativo existente."""
    cd = cd_ativo.strip().upper()

    row = query("SELECT ID_ATIVO FROM DIM_ATIVO WHERE CD_ATIVO = ?", params=(cd,))
    if row.empty:
        raise HTTPException(status_code=404, detail=f"Ativo '{cd}' não encontrado")
    id_ativo = int(row.iloc[0]["ID_ATIVO"])

    try:
        with managed_connection() as conn:
            conn.execute(
                """
                UPDATE DIM_ATIVO SET
                    ID_TIPO_ATIVO = ?, DT_EMISSAO = ?, DT_VENCIMENTO = ?, CD_SELIC = ?,
                    ID_SETOR_PAI = ?, ID_SETOR_FILHO = ?, MOEDA = ?, PRECO_ONLINE = ?,
                    FATOR_PRECO = ?, CALL_PUT = ?, LOTE = ?
                WHERE CD_ATIVO = ?
                """,
                (payload.ID_TIPO_ATIVO, payload.DT_EMISSAO, payload.DT_VENCIMENTO,
                 payload.CD_SELIC, payload.ID_SETOR_PAI, payload.ID_SETOR_FILHO,
                 payload.MOEDA, payload.PRECO_ONLINE, payload.FATOR_PRECO,
                 payload.CALL_PUT, payload.LOTE, cd),
            )
            # Upsert do mapping
            conn.execute(
                """
                INSERT INTO DIM_ATIVO_MAPPING
                    (ID_ATIVO, CD_ATIVO, CD_BBG, CD_YF, CD_FIGI, CD_ISIN, CD_CUSIP)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(ID_ATIVO) DO UPDATE SET
                    CD_ATIVO = excluded.CD_ATIVO,
                    CD_BBG   = excluded.CD_BBG,
                    CD_YF    = excluded.CD_YF,
                    CD_FIGI  = excluded.CD_FIGI,
                    CD_ISIN  = excluded.CD_ISIN,
                    CD_CUSIP = excluded.CD_CUSIP
                """,
                (id_ativo, cd, payload.CD_BBG, payload.CD_YF,
                 payload.CD_FIGI, payload.CD_ISIN, payload.CD_CUSIP),
            )
        logger.info("Ativo atualizado: %s", cd)
        return APIResponse(data={"CD_ATIVO": cd, "ID_ATIVO": id_ativo})
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Erro em PUT /ativos/%s", cd)
        raise HTTPException(status_code=500, detail=str(exc))
