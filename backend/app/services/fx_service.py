from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from ..models import AssetPriceHistory
from .yfinance_client import YFinanceClient, build_default_client


@dataclass(slots=True)
class AssetIdentity:
    asset_id: int
    asset_code: str
    currency: str


@dataclass(slots=True)
class FxQuote:
    asset_code: str | None
    rate: float


class FxService:
    def __init__(self, client: YFinanceClient | None = None) -> None:
        self.client = client or build_default_client()

    def get_asset_identity(self, session: Session, asset_id: int) -> AssetIdentity:
        row = session.execute(
            text(
                """
                SELECT ID_ATIVO AS asset_id,
                       TRIM(CD_ATIVO) AS asset_code,
                       COALESCE(TRIM(MOEDA), 'BRL') AS currency
                FROM DIM_ATIVO
                WHERE ID_ATIVO = :asset_id
                LIMIT 1
                """
            ),
            {'asset_id': asset_id},
        ).mappings().first()
        if not row:
            raise ValueError('Ativo não encontrado para cálculo de FX')
        return AssetIdentity(asset_id=row['asset_id'], asset_code=row['asset_code'], currency=(row['currency'] or 'BRL').upper())

    def get_fx_quote(self, session: Session, currency: str, ref_date: date) -> FxQuote:
        normalized = (currency or 'BRL').strip().upper()
        if normalized == 'BRL':
            return FxQuote(asset_code='BRLBRL', rate=1.0)

        fx_asset_code = f'{normalized}BRL'
        fx_asset_row = session.execute(
            text(
                """
                SELECT ID_ATIVO AS asset_id
                FROM DIM_ATIVO
                WHERE UPPER(TRIM(CD_ATIVO)) = :fx_asset_code
                LIMIT 1
                """
            ),
            {'fx_asset_code': fx_asset_code},
        ).mappings().first()
        if not fx_asset_row:
            raise ValueError(f'Ativo de FX não encontrado para {fx_asset_code}')

        fx_asset_id = fx_asset_row['asset_id']
        fx_price = self._find_local_price(session, fx_asset_id, ref_date)
        if fx_price is None:
            self._import_price_window(session, fx_asset_id, ref_date)
            fx_price = self._find_local_price(session, fx_asset_id, ref_date)
        if fx_price is None:
            raise ValueError(f'Preço de FX não encontrado para {fx_asset_code} na data informada')
        return FxQuote(asset_code=fx_asset_code, rate=float(fx_price.close_price))

    def convert_to_brl(self, session: Session, currency: str, amount: float, ref_date: date) -> FxQuote:
        quote = self.get_fx_quote(session, currency, ref_date)
        return FxQuote(asset_code=quote.asset_code, rate=amount * quote.rate)

    def _find_local_price(self, session: Session, asset_id: int, ref_date: date) -> AssetPriceHistory | None:
        return session.execute(
            select(AssetPriceHistory)
            .where(AssetPriceHistory.asset_id == asset_id, AssetPriceHistory.price_date <= ref_date)
            .order_by(AssetPriceHistory.price_date.desc())
            .limit(1)
        ).scalar_one_or_none()

    def _resolve_ticker(self, session: Session, asset_id: int) -> str:
        row = session.execute(
            text(
                """
                SELECT COALESCE(TRIM(CD_YF), '') AS ticker
                FROM DIM_ATIVO_MAPPING
                WHERE ID_ATIVO = :asset_id
                LIMIT 1
                """
            ),
            {'asset_id': asset_id},
        ).mappings().first()
        ticker = (row['ticker'] if row else '').strip()
        if not ticker:
            raise ValueError('Ticker yfinance não encontrado para ativo de FX')
        return ticker

    def _import_price_window(self, session: Session, asset_id: int, ref_date: date) -> None:
        ticker = self._resolve_ticker(session, asset_id)
        start = ref_date - timedelta(days=7)
        end = ref_date + timedelta(days=1)
        rows = self.client.fetch_history(ticker, start, end)
        if not rows:
            return
        existing_dates = {
            item[0]
            for item in session.execute(
                select(AssetPriceHistory.price_date)
                .where(AssetPriceHistory.asset_id == asset_id, AssetPriceHistory.price_date >= start, AssetPriceHistory.price_date <= end)
            ).all()
        }
        for row in rows:
            if row.price_date in existing_dates:
                continue
            session.add(
                AssetPriceHistory(
                    asset_id=asset_id,
                    price_date=row.price_date,
                    close_price=row.close_price,
                    adj_close_price=row.adj_close_price,
                )
            )
        session.flush()