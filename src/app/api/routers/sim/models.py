"""
sim/models.py — Pydantic models do simulador de fundos.
"""

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field


class PortfolioInput(BaseModel):
    NM_PORTFOLIO: str = Field(min_length=1, max_length=120)
    DT_INICIO: str = Field(default_factory=lambda: date.today().isoformat())
    BENCHMARK: Optional[str] = None
    MOEDA_BASE: str = "BRL"
    ST_ATIVO: int = 1
    ID_FUNDO: Optional[int] = None
    ID_TITULAR: Optional[int] = None
    ID_CORRETORA: Optional[int] = None
    CONTA_REF: Optional[str] = None


class FundoInput(BaseModel):
    NM_FUNDO: str = Field(min_length=1, max_length=120)
    DS_ESTRATEGIA: Optional[str] = None
    BENCHMARK: Optional[str] = None
    MOEDA_BASE: str = "BRL"
    ST_ATIVO: int = 1
    DT_INICIO: str = Field(default_factory=lambda: date.today().isoformat())
    VL_PL_INICIAL: float = Field(default=0.0, ge=0)
    VL_COTA_INICIAL: float = Field(default=1.0, gt=0)


class FundoSetupCotistaInput(BaseModel):
    ID_TITULAR: int
    VL_APORTE: float = Field(gt=0)


class FundoSetupInput(BaseModel):
    NM_FUNDO: str = Field(min_length=1, max_length=120)
    DS_ESTRATEGIA: Optional[str] = None
    BENCHMARK: Optional[str] = None
    MOEDA_BASE: str = "BRL"
    ST_ATIVO: int = 1
    DT_INICIO: str = Field(default_factory=lambda: date.today().isoformat())
    VL_COTA_INICIAL: float = Field(default=1.0, gt=0)
    COTISTAS_INICIAIS: list[FundoSetupCotistaInput]


class FundoCarteiraInput(BaseModel):
    ID_TITULAR: int
    NM_CARTEIRA: str = Field(min_length=1, max_length=120)
    ID_CORRETORA: Optional[int] = None
    CONTA_REF: Optional[str] = None
    MOEDA_BASE: str = "BRL"
    DT_INICIO: str = Field(default_factory=lambda: date.today().isoformat())


class FundoAlocacaoInput(BaseModel):
    ID_CARTEIRA_ORIGEM: int
    ID_CARTEIRA_DESTINO: int
    VL_ALOCACAO: float = Field(gt=0)
    DT_MOVIMENTO: str = Field(default_factory=lambda: date.today().isoformat())
    DS_OBSERVACAO: Optional[str] = None


class TitularInput(BaseModel):
    NM_TITULAR: str = Field(min_length=1, max_length=120)
    NR_DOCUMENTO: Optional[str] = None
    ST_ATIVO: int = 1


class CorretoraInput(BaseModel):
    NM_CORRETORA: str = Field(min_length=1, max_length=120)
    CD_CORRETORA: Optional[str] = None
    ST_ATIVO: int = 1


class TradeInput(BaseModel):
    ID_PORTFOLIO: int
    ID_ATIVO: int
    DT_HORA_EXEC: Optional[str] = None
    DT_TRADE: str = Field(default_factory=lambda: date.today().isoformat())
    SIDE: str = Field(description="BUY | SELL")
    QTD: float
    PU: float
    CUSTO: float = 0.0
    OBSERVACAO: Optional[str] = None


class FundoFluxoInput(BaseModel):
    ID_FUNDO: int
    ID_TITULAR: Optional[int] = None
    DT_REFERENCIA: str = Field(default_factory=lambda: date.today().isoformat())
    TP_FLUXO: str = Field(description="APORTE | RESGATE")
    VL_FLUXO: float = Field(gt=0)
    OBSERVACAO: Optional[str] = None


class AtivoLiquidezInput(BaseModel):
    ID_ATIVO: int
    NR_DIAS_LIQUIDEZ: int = Field(default=0, ge=0)
    DS_REGRA: Optional[str] = None
    ST_ATIVO: int = 1


class RFTituloInput(BaseModel):
    CD_TITULO: str = Field(min_length=1, max_length=80)
    NM_TITULO: Optional[str] = None
    ID_ATIVO: Optional[int] = None
    DT_VENCIMENTO: str
    DT_RESGATE: Optional[str] = None
    VL_TAXA_CONTRATADA: Optional[float] = None
    ST_ATIVO: int = 1


class ResgateSolicitacaoInput(BaseModel):
    ID_FUNDO: int
    ID_TITULAR: Optional[int] = None
    DT_SOLICITACAO: str = Field(default_factory=lambda: date.today().isoformat())
    VL_RESGATE: float = Field(gt=0)
    DS_OBSERVACAO: Optional[str] = None


class ResgatePlanoItemInput(BaseModel):
    ID_ATIVO: int
    VL_LIQUIDAR: float = Field(gt=0)
    NR_DIAS_LIQUIDEZ: Optional[int] = Field(default=None, ge=0)
    DS_OBSERVACAO: Optional[str] = None


class ResgatePlanoInput(BaseModel):
    ID_SOLICITACAO: int
    CD_METODO: str = "MANUAL_GESTOR"
    DS_JUSTIFICATIVA: Optional[str] = None
    ST_STATUS: str = "RASCUNHO"
    items: list[ResgatePlanoItemInput]


class ResgateExecucaoInput(BaseModel):
    DT_REFERENCIA: str = Field(default_factory=lambda: date.today().isoformat())
    VL_EXECUTADO: Optional[float] = Field(default=None, gt=0)
    DS_OBSERVACAO: Optional[str] = None


class ResgateOverrideInput(BaseModel):
    DT_REFERENCIA: str = Field(default_factory=lambda: date.today().isoformat())
    DS_JUSTIFICATIVA: str = Field(min_length=5)
    VL_EVENTO: float = 0.0
