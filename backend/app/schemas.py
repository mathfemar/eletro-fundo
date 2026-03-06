from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from .models import CapitalEventType, TradeSide


class AssetBase(BaseModel):
    id_ativo: int
    cd_ativo: str
    cd_yf: Optional[str] = None
    preco_online: bool
    moeda: str = 'BRL'
    fator_preco: float = 1


class AssetHistoryPoint(BaseModel):
    price_date: date
    close_price: float
    adj_close_price: float
    daily_return: Optional[float] = None


class LivePricePoint(BaseModel):
    collected_at: datetime
    price: float


class AssetResponse(AssetBase):
    last_close: Optional[float] = None
    last_adj_close: Optional[float] = None


class AssetCreate(BaseModel):
    cd_ativo: str = Field(min_length=1, max_length=40)
    cd_yf: Optional[str] = Field(default=None, max_length=40)
    preco_online: bool = False
    moeda: str = Field(default='BRL', min_length=3, max_length=8)
    fator_preco: float = Field(default=1, gt=0)


class AssetUpdate(AssetCreate):
    pass


class FundCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    inception_date: date
    base_currency: str = 'BRL'


class FundResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    inception_date: date
    base_currency: str


class InvestorCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)


class InvestorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class CapitalEventCreate(BaseModel):
    investor_id: int
    event_type: CapitalEventType
    event_date: date
    amount: float = Field(gt=0)
    notes: Optional[str] = None


class TradeCreate(BaseModel):
    asset_id: int
    trade_date: date
    side: TradeSide
    quantity: float = Field(gt=0)
    unit_price: float = Field(gt=0)
    fees: float = Field(default=0, ge=0)
    notes: Optional[str] = None


class TradePreviewResponse(BaseModel):
    fund_id: int
    asset_id: int
    asset_code: str
    asset_currency: str
    trade_date: date
    fx_asset_code: Optional[str] = None
    fx_rate: float
    quantity: float
    unit_price: float
    gross_value_local: float
    fees_local: float
    gross_value_brl: float
    fees_brl: float
    total_value_brl: float
    cash_before_trade_brl: float


class SnapshotResponse(BaseModel):
    ref_date: date
    cash_balance: float
    invested_value: float
    nav: float
    unit_count: float
    unit_value: float


class InvestorSnapshotResponse(BaseModel):
    investor_id: int
    investor_name: str
    unit_count: float
    position_value: float
    ownership_percent: float
    average_unit_cost: float
    pnl: float


class FundPositionResponse(BaseModel):
    asset_id: int
    asset_code: str
    currency: str
    quantity: float
    average_cost_brl: float
    current_price_local: float
    fx_rate: float
    market_value_brl: float
    allocation_percent: float
    pnl_brl: float


class FundDetailResponse(BaseModel):
    fund: FundResponse
    snapshot: Optional[SnapshotResponse]
    investors: list[InvestorSnapshotResponse]
    positions: list[FundPositionResponse]


class SyncResponse(BaseModel):
    processed_assets: int
    inserted_rows: int
    skipped_rows: int


class RecalculateResponse(BaseModel):
    fund_id: int
    start_date: date
    end_date: date
    snapshot_count: int


class TimelinePoint(BaseModel):
    ref_date: date
    nav: float
    unit_value: float
    cash_balance: float
    invested_value: float


class ErrorResponse(BaseModel):
    detail: str
