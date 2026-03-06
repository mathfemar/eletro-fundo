from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from ..models import AssetDividend, AssetLivePrice, AssetPriceHistory, AssetReturnHistory, CapitalEvent, CapitalEventType, Fund, Trade, TradeSide
from ..schemas import SyncResponse, TradePreviewResponse
from .asset_service import AssetService
from .fx_service import FxService
from .yfinance_client import YFinanceClient, build_default_client


class PricingService:
    def __init__(self, client: YFinanceClient | None = None, asset_service: AssetService | None = None) -> None:
        self.client = client or build_default_client()
        self.asset_service = asset_service or AssetService()
        self.fx_service = FxService()

    def sync_history(self, session: Session, start: date, end: date) -> SyncResponse:
        assets = self.asset_service.get_online_mapped_assets(session)
        inserted = 0
        skipped = 0
        for asset in assets:
            rows = self.client.fetch_history(asset['ticker'], start, end + timedelta(days=1))
            existing = {
                row[0]
                for row in session.execute(
                    select(AssetPriceHistory.price_date).where(
                        AssetPriceHistory.asset_id == asset['asset_id'],
                        AssetPriceHistory.price_date >= start,
                        AssetPriceHistory.price_date <= end,
                    )
                ).all()
            }
            for row in rows:
                if row.price_date in existing:
                    skipped += 1
                    continue
                session.add(
                    AssetPriceHistory(
                        asset_id=asset['asset_id'],
                        price_date=row.price_date,
                        close_price=row.close_price,
                        adj_close_price=row.adj_close_price,
                    )
                )
                inserted += 1
            session.flush()
            self._refresh_returns(session, asset['asset_id'])
        session.flush()
        return SyncResponse(processed_assets=len(assets), inserted_rows=inserted, skipped_rows=skipped)

    def sync_live_prices(self, session: Session) -> SyncResponse:
        assets = self.asset_service.get_online_mapped_assets(session)
        inserted = 0
        skipped = 0
        for asset in assets:
            rows = self.client.fetch_live_1d(asset['ticker'])
            last_price = session.scalar(
                select(AssetLivePrice.price)
                .where(AssetLivePrice.asset_id == asset['asset_id'])
                .order_by(AssetLivePrice.collected_at.desc())
                .limit(1)
            )
            known_timestamps = {
                row[0]
                for row in session.execute(
                    select(AssetLivePrice.collected_at).where(AssetLivePrice.asset_id == asset['asset_id'])
                ).all()
            }
            for row in rows:
                if row.collected_at in known_timestamps:
                    skipped += 1
                    continue
                if last_price is not None and float(last_price) == row.price:
                    skipped += 1
                    continue
                session.add(AssetLivePrice(asset_id=asset['asset_id'], collected_at=row.collected_at, price=row.price))
                last_price = row.price
                inserted += 1
        session.flush()
        return SyncResponse(processed_assets=len(assets), inserted_rows=inserted, skipped_rows=skipped)

    def sync_dividends(self, session: Session, start: date, end: date) -> SyncResponse:
        assets = self.asset_service.get_online_mapped_assets(session)
        inserted = 0
        skipped = 0
        for asset in assets:
            rows = self.client.fetch_dividends(asset['ticker'], start, end)
            for row in rows:
                existing = session.scalar(
                    select(func.count())
                    .select_from(AssetDividend)
                    .where(
                        AssetDividend.asset_id == asset['asset_id'],
                        AssetDividend.ex_date == row.ex_date,
                        AssetDividend.pay_date == row.pay_date,
                        AssetDividend.amount_per_unit == row.amount_per_unit,
                    )
                )
                if existing:
                    skipped += 1
                    continue
                session.add(
                    AssetDividend(
                        asset_id=asset['asset_id'],
                        ex_date=row.ex_date,
                        pay_date=row.pay_date,
                        amount_per_unit=row.amount_per_unit,
                    )
                )
                inserted += 1
        session.flush()
        return SyncResponse(processed_assets=len(assets), inserted_rows=inserted, skipped_rows=skipped)

    def _refresh_returns(self, session: Session, asset_id: int) -> None:
        session.execute(delete(AssetReturnHistory).where(AssetReturnHistory.asset_id == asset_id))
        rows = session.execute(
            select(AssetPriceHistory).where(AssetPriceHistory.asset_id == asset_id).order_by(AssetPriceHistory.price_date)
        ).scalars().all()
        previous: float | None = None
        for row in rows:
            if previous in (None, 0):
                previous = float(row.adj_close_price)
                continue
            daily_return = (float(row.adj_close_price) / previous) - 1
            session.add(AssetReturnHistory(asset_id=asset_id, price_date=row.price_date, daily_return=daily_return))
            previous = float(row.adj_close_price)

    def get_asset_history(self, session: Session, asset_id: int, days: int | None = None) -> list[dict]:
        query = (
            select(AssetPriceHistory, AssetReturnHistory)
            .outerjoin(
                AssetReturnHistory,
                (AssetReturnHistory.asset_id == AssetPriceHistory.asset_id)
                & (AssetReturnHistory.price_date == AssetPriceHistory.price_date),
            )
            .where(AssetPriceHistory.asset_id == asset_id)
        )
        if days is not None:
            cutoff = date.today() - timedelta(days=days)
            query = query.where(AssetPriceHistory.price_date >= cutoff)
        history_rows = session.execute(query.order_by(AssetPriceHistory.price_date)).all()
        return [
            {
                'price_date': price.price_date,
                'close_price': float(price.close_price),
                'adj_close_price': float(price.adj_close_price),
                'daily_return': float(ret.daily_return) if ret else None,
            }
            for price, ret in history_rows
        ]

    def get_live_points(self, session: Session, asset_id: int) -> list[dict]:
        rows = session.execute(
            select(AssetLivePrice)
            .where(AssetLivePrice.asset_id == asset_id)
            .order_by(AssetLivePrice.collected_at)
        ).scalars().all()
        return [{'collected_at': row.collected_at, 'price': float(row.price)} for row in rows]

    def preview_trade(self, session: Session, fund_id: int, asset_id: int, trade_date: date, quantity: float, unit_price: float, fees: float) -> TradePreviewResponse:
        identity = self.fx_service.get_asset_identity(session, asset_id)
        fx_quote = self.fx_service.get_fx_quote(session, identity.currency, trade_date)
        gross_value_local = quantity * unit_price
        fees_local = fees
        gross_value_brl = gross_value_local * fx_quote.rate
        fees_brl = fees_local * fx_quote.rate
        cash_before_trade_brl = self._get_cash_balance_before_trade(session, fund_id, trade_date)
        return TradePreviewResponse(
            fund_id=fund_id,
            asset_id=identity.asset_id,
            asset_code=identity.asset_code,
            asset_currency=identity.currency,
            trade_date=trade_date,
            fx_asset_code=fx_quote.asset_code,
            fx_rate=fx_quote.rate,
            quantity=quantity,
            unit_price=unit_price,
            gross_value_local=gross_value_local,
            fees_local=fees_local,
            gross_value_brl=gross_value_brl,
            fees_brl=fees_brl,
            total_value_brl=gross_value_brl + fees_brl,
            cash_before_trade_brl=cash_before_trade_brl,
        )

    def _get_cash_balance_before_trade(self, session: Session, fund_id: int, trade_date: date) -> float:
        fund = session.get(Fund, fund_id)
        if fund is None:
            raise ValueError('Fundo não encontrado para calcular caixa')

        capital_events = session.execute(
            select(CapitalEvent)
            .where(CapitalEvent.fund_id == fund_id, CapitalEvent.event_date <= trade_date)
            .order_by(CapitalEvent.event_date, CapitalEvent.id)
        ).scalars().all()
        trades = session.execute(
            select(Trade)
            .where(Trade.fund_id == fund_id, Trade.trade_date <= trade_date)
            .order_by(Trade.trade_date, Trade.id)
        ).scalars().all()
        dividends = session.execute(
            select(AssetDividend)
            .where(AssetDividend.ex_date <= trade_date)
            .order_by(AssetDividend.ex_date, AssetDividend.id)
        ).scalars().all()

        capital_by_date = defaultdict(list)
        for event in capital_events:
            capital_by_date[event.event_date].append(event)

        trades_by_date = defaultdict(list)
        for trade in trades:
            trades_by_date[trade.trade_date].append(trade)

        dividends_by_ex_date = defaultdict(list)
        for dividend in dividends:
            dividends_by_ex_date[dividend.ex_date].append(dividend)

        positions: dict[int, float] = defaultdict(float)
        pending_dividends: list[PendingPreviewDividend] = []
        cash = 0.0
        ref_date = fund.inception_date

        while ref_date <= trade_date:
            for pending in [item for item in pending_dividends if item.pay_date == ref_date]:
                fx_quote = self.fx_service.get_fx_quote(session, pending.currency, pending.pay_date)
                cash += pending.amount_local * fx_quote.rate
            pending_dividends = [item for item in pending_dividends if item.pay_date != ref_date]

            positions_before_day = dict(positions)
            for event in capital_by_date.get(ref_date, []):
                amount = float(event.amount)
                if event.event_type == CapitalEventType.REDEMPTION:
                    cash -= amount
                else:
                    cash += amount

            for dividend in dividends_by_ex_date.get(ref_date, []):
                qty = positions_before_day.get(dividend.asset_id, 0.0)
                if qty:
                    identity = self.fx_service.get_asset_identity(session, dividend.asset_id)
                    amount_local = qty * float(dividend.amount_per_unit)
                    if dividend.pay_date <= ref_date:
                        fx_quote = self.fx_service.get_fx_quote(session, identity.currency, dividend.pay_date)
                        cash += amount_local * fx_quote.rate
                    else:
                        pending_dividends.append(
                            PendingPreviewDividend(
                                pay_date=dividend.pay_date,
                                amount_local=amount_local,
                                currency=identity.currency,
                            )
                        )

            for existing_trade in trades_by_date.get(ref_date, []):
                identity = self.fx_service.get_asset_identity(session, existing_trade.asset_id)
                fx_quote = self.fx_service.get_fx_quote(session, identity.currency, existing_trade.trade_date)
                quantity = float(existing_trade.quantity)
                gross_value_brl = quantity * float(existing_trade.unit_price) * fx_quote.rate
                fees_brl = float(existing_trade.fees) * fx_quote.rate
                if existing_trade.side == TradeSide.BUY:
                    positions[existing_trade.asset_id] += quantity
                    cash -= gross_value_brl + fees_brl
                else:
                    positions[existing_trade.asset_id] -= quantity
                    cash += gross_value_brl - fees_brl

            ref_date += timedelta(days=1)

        return cash


@dataclass(slots=True)
class PendingPreviewDividend:
    pay_date: date
    amount_local: float
    currency: str
