from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import AssetDividend, AssetPriceHistory, CapitalEvent, CapitalEventType, Fund, FundDailySnapshot, InvestorDailySnapshot, Trade, TradeSide
from .fx_service import FxService


@dataclass(slots=True)
class PendingDividend:
    asset_id: int
    pay_date: date
    amount_local: float
    currency: str


class ReplayService:
    def __init__(self, initial_unit_value: float = 1.0) -> None:
        self.initial_unit_value = initial_unit_value
        self.fx_service = FxService()

    def recalculate_fund(self, session: Session, fund_id: int) -> dict:
        fund = session.get(Fund, fund_id)
        if fund is None:
            raise ValueError('Fundo não encontrado')

        capital_events = session.execute(
            select(CapitalEvent).where(CapitalEvent.fund_id == fund_id).order_by(CapitalEvent.event_date, CapitalEvent.id)
        ).scalars().all()
        trades = session.execute(select(Trade).where(Trade.fund_id == fund_id).order_by(Trade.trade_date, Trade.id)).scalars().all()
        dividends = session.execute(select(AssetDividend).order_by(AssetDividend.ex_date, AssetDividend.id)).scalars().all()
        if not capital_events and not trades:
            return {'fund_id': fund_id, 'start_date': fund.inception_date, 'end_date': fund.inception_date, 'snapshot_count': 0}

        max_event_date = fund.inception_date
        if capital_events:
            max_event_date = max(max_event_date, max(event.event_date for event in capital_events))
        if trades:
            max_event_date = max(max_event_date, max(trade.trade_date for trade in trades))
        if dividends:
            max_event_date = max(max_event_date, max(div.pay_date for div in dividends))
        price_dates = session.execute(select(AssetPriceHistory.price_date).order_by(AssetPriceHistory.price_date.desc()).limit(1)).scalars().first()
        if price_dates is not None:
            max_event_date = max(max_event_date, price_dates)

        capital_by_date = defaultdict(list)
        for event in capital_events:
            capital_by_date[event.event_date].append(event)

        trades_by_date = defaultdict(list)
        for trade in trades:
            trades_by_date[trade.trade_date].append(trade)

        dividends_by_ex_date = defaultdict(list)
        for div in dividends:
            dividends_by_ex_date[div.ex_date].append(div)

        positions: dict[int, float] = defaultdict(float)
        investor_units: dict[int, float] = defaultdict(float)
        pending_dividends: list[PendingDividend] = []
        cash = 0.0
        total_units = 0.0
        last_unit_value = self.initial_unit_value
        snapshot_count = 0

        ref_date = fund.inception_date
        while ref_date <= max_event_date:
            for pending in [item for item in pending_dividends if item.pay_date == ref_date]:
                fx_quote = self.fx_service.get_fx_quote(session, pending.currency, pending.pay_date)
                cash += pending.amount_local * fx_quote.rate
            pending_dividends = [item for item in pending_dividends if item.pay_date != ref_date]

            positions_before_day = dict(positions)
            for event in capital_by_date.get(ref_date, []):
                amount = float(event.amount)
                if total_units <= 0:
                    unit_value = self.initial_unit_value
                else:
                    unit_value = last_unit_value
                delta_units = amount / unit_value
                if event.event_type == CapitalEventType.REDEMPTION:
                    delta_units *= -1
                    cash -= amount
                else:
                    cash += amount
                total_units += delta_units
                investor_units[event.investor_id] += delta_units
                last_unit_value = unit_value if total_units > 0 else self.initial_unit_value

            for div in dividends_by_ex_date.get(ref_date, []):
                qty = positions_before_day.get(div.asset_id, 0.0)
                if qty:
                    asset_identity = self.fx_service.get_asset_identity(session, div.asset_id)
                    amount = qty * float(div.amount_per_unit)
                    if div.pay_date <= ref_date:
                        fx_quote = self.fx_service.get_fx_quote(session, asset_identity.currency, div.pay_date)
                        cash += amount * fx_quote.rate
                    else:
                        pending_dividends.append(
                            PendingDividend(
                                asset_id=div.asset_id,
                                pay_date=div.pay_date,
                                amount_local=amount,
                                currency=asset_identity.currency,
                            )
                        )

            for trade in trades_by_date.get(ref_date, []):
                quantity = float(trade.quantity)
                asset_identity = self.fx_service.get_asset_identity(session, trade.asset_id)
                fx_quote = self.fx_service.get_fx_quote(session, asset_identity.currency, trade.trade_date)
                gross_value = quantity * float(trade.unit_price) * fx_quote.rate
                fees = float(trade.fees) * fx_quote.rate
                if trade.side == TradeSide.BUY:
                    positions[trade.asset_id] += quantity
                    cash -= gross_value + fees
                else:
                    positions[trade.asset_id] -= quantity
                    cash += gross_value - fees

            invested_value = 0.0
            for asset_id, quantity in positions.items():
                if abs(quantity) < 1e-9:
                    continue
                price = session.execute(
                    select(AssetPriceHistory)
                    .where(AssetPriceHistory.asset_id == asset_id, AssetPriceHistory.price_date <= ref_date)
                    .order_by(AssetPriceHistory.price_date.desc())
                    .limit(1)
                ).scalar_one_or_none()
                if price is None:
                    continue
                asset_identity = self.fx_service.get_asset_identity(session, asset_id)
                fx_quote = self.fx_service.get_fx_quote(session, asset_identity.currency, ref_date)
                invested_value += quantity * float(price.close_price) * fx_quote.rate

            nav = cash + invested_value
            if total_units > 0:
                last_unit_value = nav / total_units
            else:
                last_unit_value = self.initial_unit_value

            session.add(
                FundDailySnapshot(
                    fund_id=fund_id,
                    ref_date=ref_date,
                    cash_balance=cash,
                    invested_value=invested_value,
                    nav=nav,
                    unit_count=total_units,
                    unit_value=last_unit_value,
                )
            )
            for investor_id, units in investor_units.items():
                position_value = units * last_unit_value
                session.add(
                    InvestorDailySnapshot(
                        fund_id=fund_id,
                        investor_id=investor_id,
                        ref_date=ref_date,
                        unit_count=units,
                        position_value=position_value,
                    )
                )
            snapshot_count += 1
            ref_date += timedelta(days=1)

        session.flush()
        return {'fund_id': fund_id, 'start_date': fund.inception_date, 'end_date': max_event_date, 'snapshot_count': snapshot_count}
