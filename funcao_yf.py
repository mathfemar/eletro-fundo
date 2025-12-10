import yfinance as yf
import pandas as pd
import logging
from typing import Optional
from datetime import datetime as dt, timedelta

today_YYYY_MM_DD = dt.today().strftime('%Y-%m-%d')

def get_yf_data_notebook(lista_ativos_yf, data_target: Optional[str] = None, max_retries: int = 4, chunk_size: Optional[int] = None):
    """
    Download 252 calendar-day history (inclusive of data_target) of Adjusted Close and Volume
    for tickers in `lista_ativos_yf`.

    Returns DataFrame: ['Ticker', 'Date', 'AdjClose', 'Volume'].
    - Forces auto_adjust=False so 'Adj Close' exists.
    - If 'Adj Close' missing, falls back to 'Close'.
    - chunk_size: if provided (e.g. 10), downloads tickers in chunks to avoid failures on large lists.
    """
    data_target = None
    if data_target is None:
        data_target = get_data_last_cota(today_YYYY_MM_DD)

    end_inclusive = pd.to_datetime(data_target)
    start = str((end_inclusive - pd.Timedelta(days=365*5)).strftime('%Y-%m-%d'))
    # yfinance end is exclusive, so add one day
    end = (end_inclusive + pd.Timedelta(days=1)).strftime('%Y-%m-%d')
    print(f"Downloading YF data for {len(lista_ativos_yf)} tickers from {start} to {end} (exclusive)")

    # disable SSL verification globally for requests (insecure)
    

    def _download_with_retries(tickers, start, end, max_retries=max_retries):
        import time
        last_exc = None
        for attempt in range(1, max_retries + 1):
            try:
                # force auto_adjust=False so 'Adj Close' column is present
                df = yf.download(tickers, start=start, end=end, progress=False, threads=False, auto_adjust=False)
                if df is not None and not df.empty:
                    return df
                logger.warning("yf.download returned empty for %s start=%s end=%s (attempt %d)", tickers, start, end, attempt)
            except Exception as exc:
                last_exc = exc
                logger.warning("yf.download failed for %s (attempt %d): %s", tickers, attempt, exc)
            if attempt < max_retries:
                time.sleep(2 ** (attempt - 1))
        if last_exc is not None:
            logger.warning("All yf.download attempts failed; last exception: %s", last_exc)
        return pd.DataFrame()

    # support chunking to be more robust on large lists / corporate networks
    def _maybe_chunk_and_download(tickers):
        if not tickers:
            return pd.DataFrame()
        if chunk_size is None or (isinstance(tickers, str) or len(tickers) <= chunk_size):
            return _download_with_retries(tickers, start, end)
        parts = []
        for i in range(0, len(tickers), chunk_size):
            sub = tickers[i:i+chunk_size]
            df_sub = _download_with_retries(sub, start, end)
            if df_sub is not None and not df_sub.empty:
                parts.append(df_sub)
        if not parts:
            return pd.DataFrame()
        # concatenation of parts: careful with MultiIndex columns; simplest is outer join on index and columns
        return pd.concat(parts, axis=1)

    df_raw = _maybe_chunk_and_download(lista_ativos_yf)

    if df_raw is None or df_raw.empty:
        logger.error("No data returned for %s for date %s (start=%s end=%s)", lista_ativos_yf, data_target, start, end)
        return pd.DataFrame(columns=['Ticker', 'Date', 'AdjClose', 'Volume'])

    tidy_rows = []

    # MultiIndex columns (common when downloading multiple tickers)
    if isinstance(df_raw.columns, pd.MultiIndex):
        # The MultiIndex can be (field, ticker) or (ticker, field).
        lvl0 = list(map(str, df_raw.columns.get_level_values(0)))
        lvl1 = list(map(str, df_raw.columns.get_level_values(1)))
        # detect orientation
        orientation = 'field_ticker' if any('Adj' in s or 'Adj Close' in s or 'Close' in s for s in lvl0) else 'ticker_field'
        if orientation == 'field_ticker':
            tickers = sorted(set(df_raw.columns.get_level_values(1)))
            for ticker in tickers:
                # prefer 'Adj Close' then fallback to 'Close'
                adj = None
                for field_name in ('Adj Close', 'AdjClose', 'Close'):
                    try:
                        adj = df_raw[(field_name, ticker)]
                        break
                    except Exception:
                        continue
                # volume
                vol = None
                for vname in ('Volume',):
                    try:
                        vol = df_raw[(vname, ticker)]
                        break
                    except Exception:
                        continue
                if adj is None or adj.empty:
                    continue
                tmp = pd.DataFrame({
                    'Date': adj.index,
                    'AdjClose': adj.values,
                    'Volume': vol.values if vol is not None and not vol.empty else [None] * len(adj),
                })
                tmp['Ticker'] = ticker
                tidy_rows.append(tmp)
        else:  # ticker_field
            tickers = sorted(set(df_raw.columns.get_level_values(0)))
            for ticker in tickers:
                # try (ticker, 'Adj Close') or (ticker, 'Close')
                adj = None
                for field_name in ('Adj Close', 'AdjClose', 'Close'):
                    try:
                        adj = df_raw[(ticker, field_name)]
                        break
                    except Exception:
                        continue
                vol = None
                try:
                    vol = df_raw[(ticker, 'Volume')]
                except Exception:
                    vol = pd.Series(dtype=float)
                if adj is None or adj.empty:
                    continue
                tmp = pd.DataFrame({
                    'Date': adj.index,
                    'AdjClose': adj.values,
                    'Volume': vol.values if vol is not None and not vol.empty else [None] * len(adj),
                })
                tmp['Ticker'] = ticker
                tidy_rows.append(tmp)
    else:
        # flat columns (single ticker or flattened): find Adj Close or fallback to Close
        cols_lower = {c.lower(): c for c in df_raw.columns}
        adj_col = None
        vol_col = None
        # prefer exact adj close labels
        for key in cols_lower:
            if 'adj' in key and 'close' in key:
                adj_col = cols_lower[key]
            if 'volume' in key:
                vol_col = cols_lower[key]
        # fallbacks
        if adj_col is None and 'close' in cols_lower:
            adj_col = cols_lower['close']
        if vol_col is None and 'volume' in cols_lower:
            vol_col = cols_lower['volume']

        # if still None, create empty series with proper index
        if adj_col is not None:
            adj = df_raw[adj_col]
        else:
            adj = pd.Series(dtype=float, index=df_raw.index)
        vol = df_raw[vol_col] if vol_col is not None else pd.Series([None] * len(adj), index=adj.index)

        # try to infer ticker if single
        inferred_ticker = None
        if isinstance(lista_ativos_yf, (list, tuple)) and len(lista_ativos_yf) == 1:
            inferred_ticker = lista_ativos_yf[0]
        elif isinstance(lista_ativos_yf, str):
            inferred_ticker = lista_ativos_yf

        tmp = pd.DataFrame({
            'Date': adj.index,
            'AdjClose': adj.values,
            'Volume': vol.values if vol is not None else [None] * len(adj),
        })
        tmp['Ticker'] = inferred_ticker if inferred_ticker is not None else 'UNKNOWN'
        tidy_rows.append(tmp)

    if not tidy_rows:
        return pd.DataFrame(columns=['Ticker', 'Date', 'AdjClose', 'Volume'])

    result = pd.concat(tidy_rows, ignore_index=True, sort=False)
    result['Date'] = pd.to_datetime(result['Date']).dt.strftime('%Y-%m-%d')
    result = result[['Ticker', 'Date', 'AdjClose', 'Volume']]
    result = result.sort_values(['Ticker', 'Date']).reset_index(drop=True)
    return result
	
df_yf = get_yf_data_notebook(lista_ativos_yf)