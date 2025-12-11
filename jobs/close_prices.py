import yfinance as yf
import pandas as pd
import logging
from typing import Optional
from datetime import datetime as dt, timedelta
import sys
import os
_CA = os.path.abspath(os.curdir)
sys.path.insert(0, _CA)
from database.connection import engine
from jobs.utils import get_data_last_cota, today_YYYY_MM_DD, get_ativos_yf
from jobs.request_yfinance import get_yf_adj_close

def get_adj_close_prices(data_target: Optional[str] = None) -> pd.DataFrame:
    ativos = get_ativos_yf()
    ativos = ativos[ativos['ticker_yf'].notnull() & (ativos['ticker_yf'] != '')]
    lista_ativos_yf = ativos['ticker_yf'].tolist()
    data_target = today_YYYY_MM_DD() if data_target is None else data_target
    df_yf = get_yf_adj_close(lista_ativos_yf, data_target=data_target)
    return df_yf

print(get_adj_close_prices())

