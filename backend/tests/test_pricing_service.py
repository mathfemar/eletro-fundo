from datetime import date, datetime

from sqlalchemy import text

from backend.app.models import AssetLivePrice, AssetPriceHistory, AssetReturnHistory, CapitalEvent, CapitalEventType, Fund, Investor
from backend.app.services.pricing_service import PricingService
from backend.app.services.yfinance_client import DividendRow, HistoricalPriceRow, LivePriceRow


class FakeClient:
    def fetch_history(self, ticker, start, end):
        return [
            HistoricalPriceRow(price_date=date(2026, 1, 1), close_price=10, adj_close_price=10),
            HistoricalPriceRow(price_date=date(2026, 1, 2), close_price=11, adj_close_price=11),
        ]

    def fetch_live_1d(self, ticker):
        return [
            LivePriceRow(collected_at=datetime(2026, 1, 1, 10, 0), price=10),
            LivePriceRow(collected_at=datetime(2026, 1, 1, 10, 30), price=10),
            LivePriceRow(collected_at=datetime(2026, 1, 1, 11, 0), price=11),
        ]

    def fetch_dividends(self, ticker, start, end):
        return [DividendRow(ex_date=date(2026, 1, 3), pay_date=date(2026, 1, 4), amount_per_unit=0.5)]


def seed_assets(session):
    session.execute(text("INSERT INTO DIM_ATIVO (ID_ATIVO, CD_ATIVO, PRECO_ONLINE) VALUES (1, 'ABEV3', 1)"))
    session.execute(text("INSERT INTO DIM_ATIVO_MAPPING (ID_ATIVO, CD_ATIVO, CD_YF) VALUES (1, 'ABEV3', 'ABEV3.SA')"))
    session.commit()


def test_sync_history_creates_returns(test_db):
    engine, SessionLocal = test_db
    with SessionLocal() as session:
        seed_assets(session)
        service = PricingService(client=FakeClient())
        result = service.sync_history(session, date(2026, 1, 1), date(2026, 1, 2))
        session.commit()
        assert result.inserted_rows == 2
        prices = session.query(AssetPriceHistory).all()
        returns = session.query(AssetReturnHistory).all()
        assert len(prices) == 2
        assert len(returns) == 1
        assert round(float(returns[0].daily_return), 6) == 0.1


def test_sync_live_skips_identical_consecutive_prices(test_db):
    engine, SessionLocal = test_db
    with SessionLocal() as session:
        seed_assets(session)
        service = PricingService(client=FakeClient())
        result = service.sync_live_prices(session)
        session.commit()
        live_prices = session.query(AssetLivePrice).order_by(AssetLivePrice.collected_at).all()
        assert result.inserted_rows == 2
        assert result.skipped_rows == 1
        assert [float(item.price) for item in live_prices] == [10.0, 11.0]


def test_trade_preview_uses_fx_rate(test_db):
    engine, SessionLocal = test_db
    with SessionLocal() as session:
        session.execute(text("INSERT INTO DIM_ATIVO (ID_ATIVO, CD_ATIVO, MOEDA, PRECO_ONLINE, FATOR_PRECO) VALUES (1, 'NVDA US', 'USD', 1, 1)"))
        session.execute(text("INSERT INTO DIM_ATIVO (ID_ATIVO, CD_ATIVO, MOEDA, PRECO_ONLINE, FATOR_PRECO) VALUES (2, 'USDBRL', 'BRL', 1, 1)"))
        session.execute(text("INSERT INTO DIM_ATIVO_MAPPING (ID_ATIVO, CD_ATIVO, CD_YF) VALUES (1, 'NVDA US', 'NVDA')"))
        session.execute(text("INSERT INTO DIM_ATIVO_MAPPING (ID_ATIVO, CD_ATIVO, CD_YF) VALUES (2, 'USDBRL', 'USDBRL=X')"))
        fund = Fund(name='Fundo FX', inception_date=date(2026, 1, 1), base_currency='BRL')
        investor = Investor(name='FX Investor')
        session.add_all([fund, investor])
        session.flush()
        session.add(CapitalEvent(fund_id=fund.id, investor_id=investor.id, event_type=CapitalEventType.INITIAL, event_date=date(2026, 1, 1), amount=5000))
        session.add(AssetPriceHistory(asset_id=2, price_date=date(2026, 1, 10), close_price=5.5, adj_close_price=5.5))
        session.commit()

        service = PricingService(client=FakeClient())
        preview = service.preview_trade(session, fund.id, 1, date(2026, 1, 10), quantity=2, unit_price=100, fees=1)
        assert preview.fund_id == fund.id
        assert preview.asset_currency == 'USD'
        assert preview.fx_asset_code == 'USDBRL'
        assert round(preview.fx_rate, 6) == 5.5
        assert round(preview.gross_value_brl, 6) == 1100.0
        assert round(preview.total_value_brl, 6) == 1105.5
        assert round(preview.cash_before_trade_brl, 6) == 5000.0
