from __future__ import annotations

from collections import defaultdict
from datetime import date

from sqlalchemy import delete, select, text
from sqlalchemy.orm import Session

from ..config import settings
from ..models import CapitalEvent, CapitalEventType, Fund, FundDailySnapshot, Investor, InvestorDailySnapshot, Trade, TradeSide
from ..schemas import CapitalEventCreate, FundCreate, InvestorCreate, TradeCreate
from .fx_service import FxService
from .replay_service import ReplayService


class FundService:
    def __init__(self, replay_service: ReplayService | None = None) -> None:
        self.replay_service = replay_service or ReplayService(initial_unit_value=settings.default_initial_unit_value)
        self.fx_service = FxService()

    def create_fund(self, session: Session, payload: FundCreate) -> Fund:
        fund = Fund(name=payload.name, inception_date=payload.inception_date, base_currency=payload.base_currency)
        session.add(fund)
        session.flush()
        return fund

    def list_funds(self, session: Session) -> list[Fund]:
        return session.execute(select(Fund).order_by(Fund.name)).scalars().all()

    def create_investor(self, session: Session, payload: InvestorCreate) -> Investor:
        investor = Investor(name=payload.name)
        session.add(investor)
        session.flush()
        return investor

    def list_investors(self, session: Session) -> list[Investor]:
        return session.execute(select(Investor).order_by(Investor.name)).scalars().all()

    def add_capital_event(self, session: Session, fund_id: int, payload: CapitalEventCreate) -> CapitalEvent:
        event = CapitalEvent(
            fund_id=fund_id,
            investor_id=payload.investor_id,
            event_type=payload.event_type,
            event_date=payload.event_date,
            amount=payload.amount,
            notes=payload.notes,
        )
        session.add(event)
        session.flush()
        self.recalculate(session, fund_id)
        return event

    def add_trade(self, session: Session, fund_id: int, payload: TradeCreate) -> Trade:
        trade = Trade(
            fund_id=fund_id,
            asset_id=payload.asset_id,
            trade_date=payload.trade_date,
            side=payload.side,
            quantity=payload.quantity,
            unit_price=payload.unit_price,
            fees=payload.fees,
            notes=payload.notes,
        )
        session.add(trade)
        session.flush()
        self.recalculate(session, fund_id)
        return trade

    def recalculate(self, session: Session, fund_id: int) -> dict:
        session.execute(delete(InvestorDailySnapshot).where(InvestorDailySnapshot.fund_id == fund_id))
        session.execute(delete(FundDailySnapshot).where(FundDailySnapshot.fund_id == fund_id))
        session.flush()
        return self.replay_service.recalculate_fund(session, fund_id)

    def get_fund_detail(self, session: Session, fund_id: int) -> dict:
        fund = session.get(Fund, fund_id)
        latest_snapshot = session.execute(
            select(FundDailySnapshot)
            .where(FundDailySnapshot.fund_id == fund_id)
            .order_by(FundDailySnapshot.ref_date.desc())
            .limit(1)
        ).scalar_one_or_none()
        investor_snapshots = session.execute(
            select(InvestorDailySnapshot)
            .where(InvestorDailySnapshot.fund_id == fund_id)
            .order_by(InvestorDailySnapshot.investor_id)
        ).scalars().all()
        latest_date = latest_snapshot.ref_date if latest_snapshot else None
        investors = self._build_investor_summary(session, fund_id, latest_snapshot, investor_snapshots)
        positions = self._build_position_summary(session, fund_id, latest_snapshot.ref_date if latest_snapshot else None, float(latest_snapshot.nav) if latest_snapshot else 0.0)
        return {
            'fund': fund,
            'snapshot': None if latest_snapshot is None else {
                'ref_date': latest_snapshot.ref_date,
                'cash_balance': float(latest_snapshot.cash_balance),
                'invested_value': float(latest_snapshot.invested_value),
                'nav': float(latest_snapshot.nav),
                'unit_count': float(latest_snapshot.unit_count),
                'unit_value': float(latest_snapshot.unit_value),
            },
            'investors': investors,
            'positions': positions,
        }

    def _build_investor_summary(self, session: Session, fund_id: int, latest_snapshot: FundDailySnapshot | None, investor_snapshots: list[InvestorDailySnapshot]) -> list[dict]:
        latest_date = latest_snapshot.ref_date if latest_snapshot else None
        nav = float(latest_snapshot.nav) if latest_snapshot else 0.0

        investor_names = {
            row.id: row.name
            for row in session.execute(select(Investor).order_by(Investor.id)).scalars().all()
        }

        net_capital_by_investor: dict[int, float] = defaultdict(float)
        capital_events = session.execute(
            select(CapitalEvent)
            .where(CapitalEvent.fund_id == fund_id)
            .order_by(CapitalEvent.event_date, CapitalEvent.id)
        ).scalars().all()
        for event in capital_events:
            signal = -1.0 if event.event_type == CapitalEventType.REDEMPTION else 1.0
            net_capital_by_investor[event.investor_id] += signal * float(event.amount)

        investors: list[dict] = []
        for snap in investor_snapshots:
            if latest_date and snap.ref_date != latest_date:
                continue
            unit_count = float(snap.unit_count)
            position_value = float(snap.position_value)
            net_capital = net_capital_by_investor.get(snap.investor_id, 0.0)
            average_unit_cost = (net_capital / unit_count) if abs(unit_count) > 1e-9 else 0.0
            pnl = position_value - net_capital
            ownership_percent = (position_value / nav * 100.0) if nav else 0.0
            investors.append(
                {
                    'investor_id': snap.investor_id,
                    'investor_name': investor_names.get(snap.investor_id, f'Cotista {snap.investor_id}'),
                    'unit_count': unit_count,
                    'position_value': position_value,
                    'ownership_percent': ownership_percent,
                    'average_unit_cost': average_unit_cost,
                    'pnl': pnl,
                }
            )
        return investors

    def _build_position_summary(self, session: Session, fund_id: int, ref_date: date | None, nav: float) -> list[dict]:
        if ref_date is None:
            return []

        trades = session.execute(
            select(Trade)
            .where(Trade.fund_id == fund_id, Trade.trade_date <= ref_date)
            .order_by(Trade.trade_date, Trade.id)
        ).scalars().all()

        positions: dict[int, dict] = {}
        for trade in trades:
            identity = self.fx_service.get_asset_identity(session, trade.asset_id)
            fx_rate = self.fx_service.get_fx_quote(session, identity.currency, trade.trade_date).rate
            quantity = float(trade.quantity)
            gross_brl = quantity * float(trade.unit_price) * fx_rate
            fees_brl = float(trade.fees) * fx_rate
            bucket = positions.setdefault(
                trade.asset_id,
                {
                    'asset_id': trade.asset_id,
                    'asset_code': identity.asset_code,
                    'currency': identity.currency,
                    'quantity': 0.0,
                    'cost_brl': 0.0,
                },
            )

            current_qty = bucket['quantity']
            current_cost = bucket['cost_brl']
            if trade.side == TradeSide.BUY:
                bucket['quantity'] = current_qty + quantity
                bucket['cost_brl'] = current_cost + gross_brl + fees_brl
            else:
                if current_qty <= 0:
                    continue
                avg_cost = current_cost / current_qty if abs(current_qty) > 1e-9 else 0.0
                reduction_qty = min(quantity, current_qty)
                bucket['quantity'] = current_qty - reduction_qty
                bucket['cost_brl'] = max(0.0, current_cost - (avg_cost * reduction_qty))

        output: list[dict] = []
        for asset_id, bucket in positions.items():
            quantity = float(bucket['quantity'])
            if abs(quantity) < 1e-9:
                continue
            price_row = session.execute(
                text(
                    """
                    SELECT DT_PRECO, VL_CLOSE
                    FROM APP_ATIVO_PRECO_HIST
                    WHERE ID_ATIVO = :asset_id
                      AND DT_PRECO <= :ref_date
                    ORDER BY DT_PRECO DESC
                    LIMIT 1
                    """
                ),
                {'asset_id': asset_id, 'ref_date': ref_date},
            ).mappings().first()
            if not price_row:
                continue
            fx_rate = self.fx_service.get_fx_quote(session, bucket['currency'], ref_date).rate
            current_price_local = float(price_row['VL_CLOSE'])
            market_value_brl = quantity * current_price_local * fx_rate
            average_cost_brl = bucket['cost_brl'] / quantity if abs(quantity) > 1e-9 else 0.0
            pnl_brl = market_value_brl - bucket['cost_brl']
            allocation_percent = (market_value_brl / nav * 100.0) if nav else 0.0
            output.append(
                {
                    'asset_id': asset_id,
                    'asset_code': bucket['asset_code'],
                    'currency': bucket['currency'],
                    'quantity': quantity,
                    'average_cost_brl': average_cost_brl,
                    'current_price_local': current_price_local,
                    'fx_rate': fx_rate,
                    'market_value_brl': market_value_brl,
                    'allocation_percent': allocation_percent,
                    'pnl_brl': pnl_brl,
                }
            )
        output.sort(key=lambda item: item['market_value_brl'], reverse=True)
        return output

    def get_timeline(self, session: Session, fund_id: int, start_date: date | None = None) -> list[dict]:
        query = select(FundDailySnapshot).where(FundDailySnapshot.fund_id == fund_id)
        if start_date is not None:
            query = query.where(FundDailySnapshot.ref_date >= start_date)
        rows = session.execute(query.order_by(FundDailySnapshot.ref_date)).scalars().all()
        return [
            {
                'ref_date': row.ref_date,
                'nav': float(row.nav),
                'unit_value': float(row.unit_value),
                'cash_balance': float(row.cash_balance),
                'invested_value': float(row.invested_value),
            }
            for row in rows
        ]
