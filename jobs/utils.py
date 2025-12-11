import sys
import os
from sqlalchemy import text
_CA = os.path.abspath(os.curdir)
sys.path.insert(0, _CA)
from database.connection import engine
import pandas as pd
import logging
from datetime import datetime as dt, timedelta

logger = logging.getLogger(__name__)

def today_YYYY_MM_DD():
    return dt.today().strftime('%Y-%m-%d')

def get_data_last_cota(data):
    query = f"""
    SELECT DT_DATA_LAST_COTA
    FROM public.dim_calendario_bz
    WHERE DT_DATA = '{data}'
    """
    try:
        result = pd.read_sql_query(query, engine)
    except Exception as exc:
        print('Falha ao buscar data de última cota: %s', exc)
        return None
    if not result.empty and 'dt_data_last_cota' in result.columns:
        valor = result.iloc[0]['dt_data_last_cota']
        if isinstance(valor, (pd.Timestamp, dt)):
            return valor.strftime('%Y-%m-%d')
        return str(valor)
    return None

def ativos_brl():
    query = f'''
        select codigo, ticker_yf from mercado.ativos
        join mercado.tipoativo using (idtipoativo)
        where moeda = 'BRL'
        and idtipoativo = 1
        and flagopcao = 0
    '''
    result = pd.read_sql_query(query, engine)
    return result

def ativos_usd():
    query = f'''
        select codigo, ticker_yf from mercado.ativos
        join mercado.tipoativo using (idtipoativo)
        where moeda = 'USD'
        and idtipoativo = 26
    '''
    result = pd.read_sql_query(query, engine)
    #print('ativos USD', result)
    return result

def format_ativos_yf_brl(df):
    df = df.copy()
    df['ticker_yf'] = df['codigo'].astype(str) + '.SA'
    #print(df)
    return df

def format_ativos_yf_usd(df):
    df = df.copy()
    df['ticker_yf'] = df['codigo'].str.replace(' US', '', regex=False)
    #print(df)
    return df


def atualizar_tickers_yf(df: pd.DataFrame) -> int:
    """Atualiza os ticker_yf da tabela mercado.ativos com base no DataFrame fornecido."""
    if df is None or df.empty:
        return 0
    df = df[['codigo', 'ticker_yf']].dropna(subset=['ticker_yf'])
    if df.empty:
        return 0

    stmt = text("""
        UPDATE mercado.ativos
        SET ticker_yf = :ticker
        WHERE codigo = :codigo
    """)

    updated = 0
    with engine.begin() as conn:
        for codigo, ticker in zip(df['codigo'], df['ticker_yf']):
            result = conn.execute(stmt, {'ticker': ticker, 'codigo': codigo})
            updated += result.rowcount

    logger.info('Atualizados %d tickers no mercado.ativos', updated)
    return updated


def corrigir_tickers_yahoo() -> int:
    """Reconstroi todos os tickers YAML atualizados para BRL e USD."""
    total = 0
    brl = atualizar_tickers_yf(format_ativos_yf_brl(ativos_brl()))
    usd = atualizar_tickers_yf(format_ativos_yf_usd(ativos_usd()))
    total = brl + usd
    logger.info('Total de tickers atualizados: %d', total)
    return total

def get_ativos_yf():
    query = '''
        select codigo, ticker_yf from mercado.ativos
        where ticker_yf is not null and ticker_yf <> ''
    '''
    result = pd.read_sql_query(query, engine)
    return result


def inserir_precos_adj_close(df: pd.DataFrame) -> int:
    """
    Insere preços ajustados de fechamento (Adj Close) na tabela mercado.precos_adj_close.
    Espera DataFrame com: ['Ticker', 'Date', 'AdjClose', 'Volume']
    Retorna número de linhas inseridas.
    """
    if df is None or df.empty:
        return 0
    
    # Mapear Ticker para idativo
    df_map = pd.read_sql_query("SELECT idativo, ticker_yf FROM mercado.ativos WHERE ticker_yf IS NOT NULL", engine)
    df_map.columns = ['idativo', 'Ticker']
    df = df.merge(df_map, on='Ticker', how='left')
    df = df[df['idativo'].notna()].copy()
    
    if df.empty:
        return 0
    
    # Renomear colunas conforme schema
    df = df.rename(columns={
        'Date': 'data',
        'AdjClose': 'preco_fechamento_ajustado',
        'Volume': 'volume'
    })
    
    stmt = text("""
        INSERT INTO mercado.precos_adj_close (data, idativo, preco_fechamento_ajustado, volume)
        VALUES (:data, :idativo, :preco_fechamento_ajustado, :volume)
        ON CONFLICT (idativo, data) DO UPDATE SET
            preco_fechamento_ajustado = EXCLUDED.preco_fechamento_ajustado,
            volume = EXCLUDED.volume
    """)
    
    inserted = 0
    with engine.begin() as conn:
        for _, row in df.iterrows():
            try:
                conn.execute(stmt, {
                    'data': row['data'],
                    'idativo': int(row['idativo']),
                    'preco_fechamento_ajustado': float(row['preco_fechamento_ajustado']) if pd.notna(row['preco_fechamento_ajustado']) else None,
                    'volume': int(row['volume']) if pd.notna(row['volume']) else None
                })
                inserted += 1
            except Exception as e:
                logger.warning(f"Erro ao inserir preço para {row['Ticker']} em {row['data']}: {e}")
    
    logger.info(f"Inseridos/atualizados {inserted} preços ajustados em mercado.precos_adj_close")
    return inserted


def calcular_variacao_diaria() -> int:
    """
    Calcula variação percentual diária a partir de precos_adj_close.
    Popula tabela variacao_diaria.
    Retorna número de variações calculadas.
    """
    query = """
    SELECT 
        pa.id,
        pa.data,
        pa.idativo,
        pa.preco_fechamento_ajustado,
        LAG(pa.preco_fechamento_ajustado) OVER (PARTITION BY pa.idativo ORDER BY pa.data) as preco_anterior
    FROM mercado.precos_adj_close pa
    WHERE NOT EXISTS (
        SELECT 1 FROM mercado.variacao_diaria vd 
        WHERE vd.idativo = pa.idativo AND vd.data = pa.data
    )
    ORDER BY pa.idativo, pa.data
    """
    
    df = pd.read_sql_query(query, engine)
    
    if df.empty:
        logger.info("Nenhuma variação nova para calcular")
        return 0
    
    # Calcular variação
    df['variacao_absoluta'] = df['preco_fechamento_ajustado'] - df['preco_anterior']
    df['variacao_pct'] = (df['variacao_absoluta'] / df['preco_anterior'] * 100).fillna(0)
    
    stmt = text("""
        INSERT INTO mercado.variacao_diaria (data, idativo, variacao_absoluta, variacao_pct)
        VALUES (:data, :idativo, :variacao_absoluta, :variacao_pct)
        ON CONFLICT (idativo, data) DO NOTHING
    """)
    
    inserted = 0
    with engine.begin() as conn:
        for _, row in df.iterrows():
            if pd.notna(row['variacao_absoluta']):
                try:
                    conn.execute(stmt, {
                        'data': row['data'],
                        'idativo': int(row['idativo']),
                        'variacao_absoluta': float(row['variacao_absoluta']),
                        'variacao_pct': float(row['variacao_pct'])
                    })
                    inserted += 1
                except Exception as e:
                    logger.warning(f"Erro ao inserir variação para idativo {row['idativo']} em {row['data']}: {e}")
    
    logger.info(f"Calculadas e inseridas {inserted} variações diárias")
    return inserted


def inserir_ativo(codigo: str, ticker_yf: str, idtipoativo: int, moeda: str = 'BRL') -> int:
    """
    Insere um novo ativo na tabela mercado.ativos.
    
    Args:
        codigo: Código do ativo (ex: 'PETR4', 'NVDA')
        ticker_yf: Ticker Yahoo Finance (ex: 'PETR4.SA', 'NVDA')
        idtipoativo: ID do tipo de ativo (ex: 1 para Ação)
        moeda: Moeda do ativo (padrão: 'BRL')
    
    Returns:
        ID do ativo inserido, ou None se falhar
    """
    stmt = text("""
        INSERT INTO mercado.ativos (codigo, ticker_yf, idtipoativo, moeda)
        VALUES (:codigo, :ticker_yf, :idtipoativo, :moeda)
        RETURNING idativo
    """)
    
    try:
        with engine.begin() as conn:
            result = conn.execute(stmt, {
                'codigo': codigo,
                'ticker_yf': ticker_yf,
                'idtipoativo': idtipoativo,
                'moeda': moeda
            })
            idativo = result.scalar()
            logger.info(f"Ativo inserido: {codigo} ({ticker_yf}) - ID: {idativo}")
            return idativo
    except Exception as e:
        logger.error(f"Erro ao inserir ativo {codigo}: {e}")
        return None


def inserir_multiplos_ativos(df: pd.DataFrame) -> int:
    """
    Insere múltiplos ativos a partir de um DataFrame.
    
    Args:
        df: DataFrame com colunas ['codigo', 'ticker_yf', 'idtipoativo', 'moeda']
            (moeda é opcional, padrão: 'BRL')
    
    Returns:
        Número de ativos inseridos com sucesso
    """
    if df is None or df.empty:
        return 0
    
    # Validar colunas obrigatórias
    required_cols = ['codigo', 'ticker_yf', 'idtipoativo']
    if not all(col in df.columns for col in required_cols):
        logger.error(f"DataFrame deve conter colunas: {required_cols}")
        return 0
    
    # Preencher moeda padrão se não existir
    if 'moeda' not in df.columns:
        df['moeda'] = 'BRL'
    
    stmt = text("""
        INSERT INTO mercado.ativos (codigo, ticker_yf, idtipoativo, moeda)
        VALUES (:codigo, :ticker_yf, :idtipoativo, :moeda)
        ON CONFLICT (codigo) DO NOTHING
    """)
    
    inserted = 0
    with engine.begin() as conn:
        for _, row in df.iterrows():
            try:
                result = conn.execute(stmt, {
                    'codigo': str(row['codigo']).strip(),
                    'ticker_yf': str(row['ticker_yf']).strip(),
                    'idtipoativo': int(row['idtipoativo']),
                    'moeda': str(row['moeda']).strip() if pd.notna(row.get('moeda')) else 'BRL'
                })
                if result.rowcount > 0:
                    inserted += 1
            except Exception as e:
                logger.warning(f"Erro ao inserir ativo {row.get('codigo')}: {e}")
    
    logger.info(f"Inseridos {inserted} novos ativos em mercado.ativos")
    return inserted
