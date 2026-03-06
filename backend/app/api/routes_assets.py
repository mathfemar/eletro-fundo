from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ..db import get_session
from datetime import date

from ..schemas import AssetCreate, AssetHistoryPoint, AssetResponse, AssetUpdate, LivePricePoint, TradePreviewResponse
from ..services.asset_service import AssetService
from ..services.pricing_service import PricingService

router = APIRouter(prefix='/assets', tags=['assets'])
asset_service = AssetService()
pricing_service = PricingService()


@router.get('', response_model=list[AssetResponse])
def list_assets(
    only_online: bool = Query(False),
    only_mapped: bool = Query(False),
    session: Session = Depends(get_session),
) -> list[AssetResponse]:
    return asset_service.list_assets(session, only_online=only_online, only_mapped=only_mapped)


@router.post('', response_model=AssetResponse, status_code=status.HTTP_201_CREATED)
def create_asset(payload: AssetCreate, session: Session = Depends(get_session)) -> AssetResponse:
    try:
        return asset_service.create_asset(session, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.put('/{asset_id}', response_model=AssetResponse)
def update_asset(asset_id: int, payload: AssetUpdate, session: Session = Depends(get_session)) -> AssetResponse:
    try:
        return asset_service.update_asset(session, asset_id, payload)
    except ValueError as exc:
        status_code = 404 if 'não encontrado' in str(exc).lower() else 400
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc


@router.get('/{asset_id}/history', response_model=list[AssetHistoryPoint])
def get_asset_history(asset_id: int, days: int | None = Query(default=None, ge=1, le=3650), session: Session = Depends(get_session)) -> list[AssetHistoryPoint]:
    return pricing_service.get_asset_history(session, asset_id, days)


@router.get('/{asset_id}/live', response_model=list[LivePricePoint])
def get_asset_live(asset_id: int, session: Session = Depends(get_session)) -> list[LivePricePoint]:
    return pricing_service.get_live_points(session, asset_id)


@router.get('/{asset_id}/trade-preview', response_model=TradePreviewResponse)
def get_trade_preview(
    asset_id: int,
    fund_id: int = Query(..., gt=0),
    trade_date: date = Query(...),
    quantity: float = Query(..., gt=0),
    unit_price: float = Query(..., gt=0),
    fees: float = Query(0, ge=0),
    session: Session = Depends(get_session),
) -> TradePreviewResponse:
    try:
        return pricing_service.preview_trade(session, fund_id, asset_id, trade_date, quantity, unit_price, fees)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
