from sqlalchemy import text


def test_fund_detail_returns_investor_name_and_positions(client):
    test_client, SessionLocal = client
    with SessionLocal() as session:
        session.execute(text("INSERT INTO DIM_ATIVO (ID_ATIVO, CD_ATIVO, MOEDA, PRECO_ONLINE, FATOR_PRECO) VALUES (1, 'PETR4', 'BRL', 1, 1)"))
        session.execute(text("INSERT INTO DIM_ATIVO_MAPPING (ID_ATIVO, CD_ATIVO, CD_YF) VALUES (1, 'PETR4', 'PETR4.SA')"))
        session.execute(text("INSERT INTO APP_COTISTA (ID_COTISTA, NM_COTISTA, DT_CRIACAO) VALUES (1, 'Alice', '2026-01-01 00:00:00')"))
        session.execute(text("INSERT INTO APP_FUNDO (ID_FUNDO, NM_FUNDO, DT_INICIO, MOEDA_BASE, DT_CRIACAO) VALUES (1, 'Fundo XPTO', '2026-01-01', 'BRL', '2026-01-01 00:00:00')"))
        session.execute(text("INSERT INTO APP_FUNDO_FLUXO_CAPITAL (ID_EVENTO, ID_FUNDO, ID_COTISTA, TP_EVENTO, DT_EVENTO, VL_FINANCEIRO, DT_CRIACAO) VALUES (1, 1, 1, 'INITIAL', '2026-01-01', 1000, '2026-01-01 00:00:00')"))
        session.execute(text("INSERT INTO APP_FUNDO_TRADE (ID_TRADE, ID_FUNDO, ID_ATIVO, DT_TRADE, TP_LADO, QTD, VL_PRECO_UNITARIO, VL_CUSTOS, DT_CRIACAO) VALUES (1, 1, 1, '2026-01-02', 'BUY', 10, 10, 0, '2026-01-02 00:00:00')"))
        session.execute(text("INSERT INTO APP_ATIVO_PRECO_HIST (ID_PRECO, ID_ATIVO, DT_PRECO, VL_CLOSE, VL_ADJ_CLOSE, FONTE, DT_IMPORTACAO) VALUES (1, 1, '2026-01-02', 10, 10, 'test', '2026-01-02 00:00:00')"))
        session.execute(text("INSERT INTO APP_ATIVO_PRECO_HIST (ID_PRECO, ID_ATIVO, DT_PRECO, VL_CLOSE, VL_ADJ_CLOSE, FONTE, DT_IMPORTACAO) VALUES (2, 1, '2026-01-03', 12, 12, 'test', '2026-01-03 00:00:00')"))
        session.execute(text("INSERT INTO APP_FUNDO_SNAPSHOT_DIARIO (ID_SNAPSHOT, ID_FUNDO, DT_REF, VL_CAIXA, VL_CARTEIRA, VL_PL, QTD_COTA, VL_COTA, DT_CRIACAO) VALUES (1, 1, '2026-01-03', 900, 120, 1020, 1000, 1.02, '2026-01-03 00:00:00')"))
        session.execute(text("INSERT INTO APP_COTISTA_SNAPSHOT_DIARIO (ID_SNAPSHOT, ID_FUNDO, ID_COTISTA, DT_REF, QTD_COTA, VL_POSICAO, DT_CRIACAO) VALUES (1, 1, 1, '2026-01-03', 1000, 1020, '2026-01-03 00:00:00')"))
        session.commit()

    response = test_client.get('/funds/1')
    assert response.status_code == 200
    payload = response.json()
    assert payload['investors'][0]['investor_name'] == 'Alice'
    assert round(payload['investors'][0]['ownership_percent'], 2) == 100.00
    assert payload['positions'][0]['asset_code'] == 'PETR4'
    assert round(payload['positions'][0]['market_value_brl'], 2) == 120.00


def test_list_assets_filters_online_and_mapped(client):
    test_client, SessionLocal = client
    with SessionLocal() as session:
        session.execute(text("INSERT INTO DIM_ATIVO (ID_ATIVO, CD_ATIVO, PRECO_ONLINE) VALUES (1, 'ABEV3', 1), (2, 'OFF1', 0)"))
        session.execute(text("INSERT INTO DIM_ATIVO_MAPPING (ID_ATIVO, CD_ATIVO, CD_YF) VALUES (1, 'ABEV3', 'ABEV3.SA'), (2, 'OFF1', NULL)"))
        session.commit()

    response = test_client.get('/assets?only_online=true&only_mapped=true')
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]['cd_ativo'] == 'ABEV3'
