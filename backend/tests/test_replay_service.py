from datetime import date

from sqlalchemy import text

from backend.app.models import AssetDividend, AssetPriceHistory, CapitalEvent, CapitalEventType, Fund, Investor, Trade, TradeSide
from backend.app.services.replay_service import ReplayService


def test_contribution_and_redemption_keep_unit_value_when_no_market_move(test_db):
    engine, SessionLocal = test_db
    with SessionLocal() as session:
        fund = Fund(name='Fundo Teste', inception_date=date(2026, 1, 1), base_currency='BRL')
        investor = Investor(name='Alice')
        session.add_all([fund, investor])
        session.flush()
        session.add_all([
            CapitalEvent(fund_id=fund.id, investor_id=investor.id, event_type=CapitalEventType.INITIAL, event_date=date(2026, 1, 1), amount=1000),
            CapitalEvent(fund_id=fund.id, investor_id=investor.id, event_type=CapitalEventType.CONTRIBUTION, event_date=date(2026, 1, 2), amount=500),
            CapitalEvent(fund_id=fund.id, investor_id=investor.id, event_type=CapitalEventType.REDEMPTION, event_date=date(2026, 1, 3), amount=300),
        ])
        session.flush()
        result = ReplayService().recalculate_fund(session, fund.id)
        assert result['snapshot_count'] == 3
        rows = session.execute(text('SELECT DT_REF, VL_COTA, VL_PL FROM APP_FUNDO_SNAPSHOT_DIARIO ORDER BY DT_REF')).fetchall()
        assert [round(row[1], 6) for row in rows] == [1.0, 1.0, 1.0]
        assert [round(row[2], 6) for row in rows] == [1000.0, 1500.0, 1200.0]


def test_retroactive_trade_and_dividend_are_replayed(test_db):
    engine, SessionLocal = test_db
    with SessionLocal() as session:
        session.execute(text("INSERT INTO DIM_ATIVO (ID_ATIVO, CD_ATIVO, PRECO_ONLINE) VALUES (1, 'ABEV3', 1)"))
        fund = Fund(name='Fundo Div', inception_date=date(2026, 1, 1), base_currency='BRL')
        investor = Investor(name='Bob')
        session.add_all([fund, investor])
        session.flush()
        session.add(CapitalEvent(fund_id=fund.id, investor_id=investor.id, event_type=CapitalEventType.INITIAL, event_date=date(2026, 1, 1), amount=1000))
        session.add(Trade(fund_id=fund.id, asset_id=1, trade_date=date(2026, 1, 2), side=TradeSide.BUY, quantity=100, unit_price=10, fees=0))
        session.add_all([
            AssetPriceHistory(asset_id=1, price_date=date(2026, 1, 2), close_price=10, adj_close_price=10),
            AssetPriceHistory(asset_id=1, price_date=date(2026, 1, 3), close_price=8, adj_close_price=10),
        ])
        session.add(AssetDividend(asset_id=1, ex_date=date(2026, 1, 3), pay_date=date(2026, 1, 3), amount_per_unit=2))
        session.flush()

        ReplayService().recalculate_fund(session, fund.id)
        rows = session.execute(text('SELECT DT_REF, VL_CAIXA, VL_CARTEIRA, VL_PL FROM APP_FUNDO_SNAPSHOT_DIARIO ORDER BY DT_REF')).fetchall()
        last = rows[-1]
        assert round(last[1], 6) == 200.0
        assert round(last[2], 6) == 800.0
        assert round(last[3], 6) == 1000.0


def test_offshore_trade_uses_daily_fx_on_trade_and_valuation(test_db):
    engine, SessionLocal = test_db
    with SessionLocal() as session:
        session.execute(text("INSERT INTO DIM_ATIVO (ID_ATIVO, CD_ATIVO, MOEDA, PRECO_ONLINE, FATOR_PRECO) VALUES (10, 'NVDA US', 'USD', 1, 1)"))
        session.execute(text("INSERT INTO DIM_ATIVO (ID_ATIVO, CD_ATIVO, MOEDA, PRECO_ONLINE, FATOR_PRECO) VALUES (20, 'USDBRL', 'BRL', 1, 1)"))
        fund = Fund(name='Fundo Offshore', inception_date=date(2026, 1, 1), base_currency='BRL')
        investor = Investor(name='Carol')
        session.add_all([fund, investor])
        session.flush()
        session.add(CapitalEvent(fund_id=fund.id, investor_id=investor.id, event_type=CapitalEventType.INITIAL, event_date=date(2026, 1, 1), amount=1000))
        session.add(Trade(fund_id=fund.id, asset_id=10, trade_date=date(2026, 1, 2), side=TradeSide.BUY, quantity=1, unit_price=100, fees=1))
        session.add_all([
            AssetPriceHistory(asset_id=10, price_date=date(2026, 1, 2), close_price=100, adj_close_price=100),
            AssetPriceHistory(asset_id=10, price_date=date(2026, 1, 3), close_price=110, adj_close_price=110),
            AssetPriceHistory(asset_id=20, price_date=date(2026, 1, 2), close_price=5, adj_close_price=5),
            AssetPriceHistory(asset_id=20, price_date=date(2026, 1, 3), close_price=5.2, adj_close_price=5.2),
        ])
        session.flush()

        ReplayService().recalculate_fund(session, fund.id)
        rows = session.execute(text('SELECT DT_REF, VL_CAIXA, VL_CARTEIRA, VL_PL FROM APP_FUNDO_SNAPSHOT_DIARIO ORDER BY DT_REF')).fetchall()
        last = rows[-1]
        assert round(last[1], 6) == 495.0
        assert round(last[2], 6) == 572.0
        assert round(last[3], 6) == 1067.0
