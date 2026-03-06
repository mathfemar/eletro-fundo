from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ..db import get_session
from ..schemas import CapitalEventCreate, FundCreate, FundDetailResponse, FundResponse, InvestorCreate, InvestorResponse, RecalculateResponse, TimelinePoint, TradeCreate
from ..services.fund_service import FundService

router = APIRouter(tags=['funds'])
fund_service = FundService()


@router.post('/funds', response_model=FundResponse, status_code=status.HTTP_201_CREATED)
def create_fund(payload: FundCreate, session: Session = Depends(get_session)) -> FundResponse:
    return fund_service.create_fund(session, payload)


@router.get('/funds', response_model=list[FundResponse])
def list_funds(session: Session = Depends(get_session)) -> list[FundResponse]:
    return fund_service.list_funds(session)


@router.get('/funds/{fund_id}', response_model=FundDetailResponse)
def get_fund(fund_id: int, session: Session = Depends(get_session)) -> FundDetailResponse:
    detail = fund_service.get_fund_detail(session, fund_id)
    if detail['fund'] is None:
        raise HTTPException(status_code=404, detail='Fundo não encontrado')
    return detail


@router.post('/investors', response_model=InvestorResponse, status_code=status.HTTP_201_CREATED)
def create_investor(payload: InvestorCreate, session: Session = Depends(get_session)) -> InvestorResponse:
    return fund_service.create_investor(session, payload)


@router.get('/investors', response_model=list[InvestorResponse])
def list_investors(session: Session = Depends(get_session)) -> list[InvestorResponse]:
    return fund_service.list_investors(session)


@router.post('/funds/{fund_id}/capital-events', status_code=status.HTTP_201_CREATED)
def add_capital_event(fund_id: int, payload: CapitalEventCreate, session: Session = Depends(get_session)) -> dict:
    event = fund_service.add_capital_event(session, fund_id, payload)
    return {'id': event.id}


@router.post('/funds/{fund_id}/trades', status_code=status.HTTP_201_CREATED)
def add_trade(fund_id: int, payload: TradeCreate, session: Session = Depends(get_session)) -> dict:
    trade = fund_service.add_trade(session, fund_id, payload)
    return {'id': trade.id}


@router.post('/funds/{fund_id}/recalculate', response_model=RecalculateResponse)
def recalculate_fund(fund_id: int, session: Session = Depends(get_session)) -> RecalculateResponse:
    return fund_service.recalculate(session, fund_id)


@router.get('/funds/{fund_id}/timeline', response_model=list[TimelinePoint])
def get_timeline(
    fund_id: int,
    start_date: date | None = Query(default=None),
    session: Session = Depends(get_session),
) -> list[TimelinePoint]:
    return fund_service.get_timeline(session, fund_id, start_date)
