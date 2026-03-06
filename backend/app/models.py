from __future__ import annotations

from datetime import UTC, date, datetime
from enum import Enum
from typing import Optional

from sqlalchemy import Date, DateTime, Enum as SqlEnum, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class CapitalEventType(str, Enum):
    INITIAL = 'INITIAL'
    CONTRIBUTION = 'CONTRIBUTION'
    REDEMPTION = 'REDEMPTION'


class TradeSide(str, Enum):
    BUY = 'BUY'
    SELL = 'SELL'


class Fund(Base):
    __tablename__ = 'APP_FUNDO'

    id: Mapped[int] = mapped_column('ID_FUNDO', primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column('NM_FUNDO', String(120), unique=True)
    inception_date: Mapped[date] = mapped_column('DT_INICIO', Date)
    base_currency: Mapped[str] = mapped_column('MOEDA_BASE', String(8), default='BRL')
    created_at: Mapped[datetime] = mapped_column('DT_CRIACAO', DateTime, default=utc_now)

    capital_events: Mapped[list[CapitalEvent]] = relationship(back_populates='fund', cascade='all, delete-orphan')
    trades: Mapped[list[Trade]] = relationship(back_populates='fund', cascade='all, delete-orphan')
    snapshots: Mapped[list[FundDailySnapshot]] = relationship(back_populates='fund', cascade='all, delete-orphan')


class Investor(Base):
    __tablename__ = 'APP_COTISTA'

    id: Mapped[int] = mapped_column('ID_COTISTA', primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column('NM_COTISTA', String(120), unique=True)
    created_at: Mapped[datetime] = mapped_column('DT_CRIACAO', DateTime, default=utc_now)

    capital_events: Mapped[list[CapitalEvent]] = relationship(back_populates='investor')
    snapshots: Mapped[list[InvestorDailySnapshot]] = relationship(back_populates='investor', cascade='all, delete-orphan')


class CapitalEvent(Base):
    __tablename__ = 'APP_FUNDO_FLUXO_CAPITAL'

    id: Mapped[int] = mapped_column('ID_EVENTO', primary_key=True, autoincrement=True)
    fund_id: Mapped[int] = mapped_column('ID_FUNDO', ForeignKey('APP_FUNDO.ID_FUNDO'), index=True)
    investor_id: Mapped[int] = mapped_column('ID_COTISTA', ForeignKey('APP_COTISTA.ID_COTISTA'), index=True)
    event_type: Mapped[CapitalEventType] = mapped_column('TP_EVENTO', SqlEnum(CapitalEventType))
    event_date: Mapped[date] = mapped_column('DT_EVENTO', Date, index=True)
    amount: Mapped[float] = mapped_column('VL_FINANCEIRO', Numeric(18, 6))
    notes: Mapped[Optional[str]] = mapped_column('DS_OBSERVACAO', Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column('DT_CRIACAO', DateTime, default=utc_now)

    fund: Mapped[Fund] = relationship(back_populates='capital_events')
    investor: Mapped[Investor] = relationship(back_populates='capital_events')


class Trade(Base):
    __tablename__ = 'APP_FUNDO_TRADE'

    id: Mapped[int] = mapped_column('ID_TRADE', primary_key=True, autoincrement=True)
    fund_id: Mapped[int] = mapped_column('ID_FUNDO', ForeignKey('APP_FUNDO.ID_FUNDO'), index=True)
    asset_id: Mapped[int] = mapped_column('ID_ATIVO', index=True)
    trade_date: Mapped[date] = mapped_column('DT_TRADE', Date, index=True)
    side: Mapped[TradeSide] = mapped_column('TP_LADO', SqlEnum(TradeSide))
    quantity: Mapped[float] = mapped_column('QTD', Numeric(18, 6))
    unit_price: Mapped[float] = mapped_column('VL_PRECO_UNITARIO', Numeric(18, 6))
    fees: Mapped[float] = mapped_column('VL_CUSTOS', Numeric(18, 6), default=0)
    notes: Mapped[Optional[str]] = mapped_column('DS_OBSERVACAO', Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column('DT_CRIACAO', DateTime, default=utc_now)

    fund: Mapped[Fund] = relationship(back_populates='trades')


class AssetDividend(Base):
    __tablename__ = 'APP_ATIVO_PROVENTO'
    __table_args__ = (
        UniqueConstraint('ID_ATIVO', 'DT_EX', 'DT_PAGAMENTO', 'VL_POR_UNIDADE', name='UQ_PROVENTO_ATIVO_EVENTO'),
    )

    id: Mapped[int] = mapped_column('ID_PROVENTO', primary_key=True, autoincrement=True)
    asset_id: Mapped[int] = mapped_column('ID_ATIVO', index=True)
    ex_date: Mapped[date] = mapped_column('DT_EX', Date, index=True)
    pay_date: Mapped[date] = mapped_column('DT_PAGAMENTO', Date, index=True)
    amount_per_unit: Mapped[float] = mapped_column('VL_POR_UNIDADE', Numeric(18, 8))
    currency: Mapped[str] = mapped_column('MOEDA', String(8), default='BRL')
    source: Mapped[str] = mapped_column('FONTE', String(32), default='yfinance')
    imported_at: Mapped[datetime] = mapped_column('DT_IMPORTACAO', DateTime, default=utc_now)


class AssetPriceHistory(Base):
    __tablename__ = 'APP_ATIVO_PRECO_HIST'
    __table_args__ = (
        UniqueConstraint('ID_ATIVO', 'DT_PRECO', name='UQ_PRECO_HIST_ATIVO_DIA'),
    )

    id: Mapped[int] = mapped_column('ID_PRECO', primary_key=True, autoincrement=True)
    asset_id: Mapped[int] = mapped_column('ID_ATIVO', index=True)
    price_date: Mapped[date] = mapped_column('DT_PRECO', Date, index=True)
    close_price: Mapped[float] = mapped_column('VL_CLOSE', Numeric(18, 8))
    adj_close_price: Mapped[float] = mapped_column('VL_ADJ_CLOSE', Numeric(18, 8))
    source: Mapped[str] = mapped_column('FONTE', String(32), default='yfinance')
    imported_at: Mapped[datetime] = mapped_column('DT_IMPORTACAO', DateTime, default=utc_now)


class AssetLivePrice(Base):
    __tablename__ = 'APP_ATIVO_PRECO_LIVE'
    __table_args__ = (
        UniqueConstraint('ID_ATIVO', 'DT_COLETA', name='UQ_PRECO_LIVE_ATIVO_TS'),
    )

    id: Mapped[int] = mapped_column('ID_LIVE', primary_key=True, autoincrement=True)
    asset_id: Mapped[int] = mapped_column('ID_ATIVO', index=True)
    collected_at: Mapped[datetime] = mapped_column('DT_COLETA', DateTime, index=True)
    interval_label: Mapped[str] = mapped_column('CD_INTERVALO', String(16), default='30m')
    price: Mapped[float] = mapped_column('VL_PRECO', Numeric(18, 8))
    source: Mapped[str] = mapped_column('FONTE', String(32), default='yfinance')
    imported_at: Mapped[datetime] = mapped_column('DT_IMPORTACAO', DateTime, default=utc_now)


class AssetReturnHistory(Base):
    __tablename__ = 'APP_ATIVO_RETORNO_HIST'
    __table_args__ = (
        UniqueConstraint('ID_ATIVO', 'DT_PRECO', name='UQ_RETORNO_ATIVO_DIA'),
    )

    id: Mapped[int] = mapped_column('ID_RETORNO', primary_key=True, autoincrement=True)
    asset_id: Mapped[int] = mapped_column('ID_ATIVO', index=True)
    price_date: Mapped[date] = mapped_column('DT_PRECO', Date, index=True)
    daily_return: Mapped[float] = mapped_column('VL_RETORNO_DIA', Numeric(18, 10))
    imported_at: Mapped[datetime] = mapped_column('DT_IMPORTACAO', DateTime, default=utc_now)


class FundDailySnapshot(Base):
    __tablename__ = 'APP_FUNDO_SNAPSHOT_DIARIO'
    __table_args__ = (
        UniqueConstraint('ID_FUNDO', 'DT_REF', name='UQ_FUNDO_SNAPSHOT_DIA'),
    )

    id: Mapped[int] = mapped_column('ID_SNAPSHOT', primary_key=True, autoincrement=True)
    fund_id: Mapped[int] = mapped_column('ID_FUNDO', ForeignKey('APP_FUNDO.ID_FUNDO'), index=True)
    ref_date: Mapped[date] = mapped_column('DT_REF', Date, index=True)
    cash_balance: Mapped[float] = mapped_column('VL_CAIXA', Numeric(18, 8))
    invested_value: Mapped[float] = mapped_column('VL_CARTEIRA', Numeric(18, 8))
    nav: Mapped[float] = mapped_column('VL_PL', Numeric(18, 8))
    unit_count: Mapped[float] = mapped_column('QTD_COTA', Numeric(18, 8))
    unit_value: Mapped[float] = mapped_column('VL_COTA', Numeric(18, 8))
    created_at: Mapped[datetime] = mapped_column('DT_CRIACAO', DateTime, default=utc_now)

    fund: Mapped[Fund] = relationship(back_populates='snapshots')


class InvestorDailySnapshot(Base):
    __tablename__ = 'APP_COTISTA_SNAPSHOT_DIARIO'
    __table_args__ = (
        UniqueConstraint('ID_FUNDO', 'ID_COTISTA', 'DT_REF', name='UQ_COTISTA_SNAPSHOT_DIA'),
    )

    id: Mapped[int] = mapped_column('ID_SNAPSHOT', primary_key=True, autoincrement=True)
    fund_id: Mapped[int] = mapped_column('ID_FUNDO', ForeignKey('APP_FUNDO.ID_FUNDO'), index=True)
    investor_id: Mapped[int] = mapped_column('ID_COTISTA', ForeignKey('APP_COTISTA.ID_COTISTA'), index=True)
    ref_date: Mapped[date] = mapped_column('DT_REF', Date, index=True)
    unit_count: Mapped[float] = mapped_column('QTD_COTA', Numeric(18, 8))
    position_value: Mapped[float] = mapped_column('VL_POSICAO', Numeric(18, 8))
    created_at: Mapped[datetime] = mapped_column('DT_CRIACAO', DateTime, default=utc_now)

    investor: Mapped[Investor] = relationship(back_populates='snapshots')
