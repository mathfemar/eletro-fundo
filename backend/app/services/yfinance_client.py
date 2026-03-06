from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Iterable

import pandas as pd

from YFinanceConfig import configure_yfinance_for_corporate_proxy

configure_yfinance_for_corporate_proxy()
import yfinance as yf  # noqa: E402


@dataclass(slots=True)
class HistoricalPriceRow:
    price_date: date
    close_price: float
    adj_close_price: float


@dataclass(slots=True)
class LivePriceRow:
    collected_at: datetime
    price: float


@dataclass(slots=True)
class DividendRow:
    ex_date: date
    pay_date: date
    amount_per_unit: float


class YFinanceClient:
    def fetch_history(self, ticker: str, start: date, end: date) -> list[HistoricalPriceRow]:
        frame = yf.Ticker(ticker).history(start=start, end=end, auto_adjust=False, actions=False)
        if frame.empty:
            return []
        frame = frame.reset_index()
        frame['Date'] = pd.to_datetime(frame['Date']).dt.date
        output: list[HistoricalPriceRow] = []
        for _, row in frame.iterrows():
            close_value = float(row['Close'])
            adj_close = float(row['Adj Close']) if 'Adj Close' in row else close_value
            output.append(HistoricalPriceRow(price_date=row['Date'], close_price=close_value, adj_close_price=adj_close))
        return output

    def fetch_live_1d(self, ticker: str) -> list[LivePriceRow]:
        frame = yf.Ticker(ticker).history(period='1d', interval='30m', auto_adjust=False, actions=False)
        if frame.empty:
            return []
        frame = frame.reset_index()
        ts_col = 'Datetime' if 'Datetime' in frame.columns else frame.columns[0]
        output: list[LivePriceRow] = []
        for _, row in frame.iterrows():
            output.append(
                LivePriceRow(
                    collected_at=pd.to_datetime(row[ts_col]).to_pydatetime(),
                    price=float(row['Close']),
                )
            )
        return output

    def fetch_dividends(self, ticker: str, start: date, end: date) -> list[DividendRow]:
        ticker_obj = yf.Ticker(ticker)
        dividends = ticker_obj.dividends
        if dividends is None or len(dividends) == 0:
            return []
        series = dividends[(dividends.index.date >= start) & (dividends.index.date <= end)]
        if len(series) == 0:
            return []
        calendar = getattr(ticker_obj, 'calendar', None)
        pay_date = None
        if isinstance(calendar, pd.DataFrame) and 'Ex-Dividend Date' in calendar.index and 'Dividend Date' in calendar.index:
            try:
                pay_date = pd.to_datetime(calendar.loc['Dividend Date'].iloc[0]).date()
            except Exception:
                pay_date = None
        rows: list[DividendRow] = []
        for ts, value in series.items():
            ex_date = pd.to_datetime(ts).date()
            rows.append(DividendRow(ex_date=ex_date, pay_date=pay_date or ex_date, amount_per_unit=float(value)))
        return rows


def build_default_client() -> YFinanceClient:
    return YFinanceClient()
