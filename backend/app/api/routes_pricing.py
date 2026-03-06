from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..db import get_session
from ..schemas import SyncResponse
from ..services.pricing_service import PricingService

router = APIRouter(prefix='/pricing', tags=['pricing'])
pricing_service = PricingService()


@router.post('/sync/history', response_model=SyncResponse)
def sync_history(
    start: date = Query(default_factory=lambda: date.today() - timedelta(days=365)),
    end: date = Query(default_factory=date.today),
    session: Session = Depends(get_session),
) -> SyncResponse:
    return pricing_service.sync_history(session, start, end)


@router.post('/sync/live', response_model=SyncResponse)
def sync_live(session: Session = Depends(get_session)) -> SyncResponse:
    return pricing_service.sync_live_prices(session)


@router.post('/sync/dividends', response_model=SyncResponse)
def sync_dividends(
    start: date = Query(default_factory=lambda: date.today() - timedelta(days=365)),
    end: date = Query(default_factory=date.today),
    session: Session = Depends(get_session),
) -> SyncResponse:
    return pricing_service.sync_dividends(session, start, end)
