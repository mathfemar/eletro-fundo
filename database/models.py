"""
Modelos SQLAlchemy para a aplicação Eletro Fundo
Estrutura construída em torno das tabelas reais: tipoativo e ativos
"""
from datetime import datetime, date
from sqlalchemy import (
    Column,
    Integer,
    String,
    Numeric,
    Date,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    Index,
    CheckConstraint,
)
from sqlalchemy.orm import relationship
from database.connection import Base


# ============================================================
# SCHEMA: MERCADO
# ============================================================

class TipoAtivo(Base):
    """Tipos de ativos - Schema: mercado"""
    __tablename__ = "tipoativo"
    __table_args__ = {"schema": "mercado"}

    idtipoativo = Column(Integer, primary_key=True)
    tipoativo = Column(String(300))

    # Relacionamentos
    ativos = relationship("Ativo", back_populates="tipo_ativo")

    def __repr__(self):
        return f"<TipoAtivo {self.tipoativo}>"


class Ativo(Base):
    """Ativos (ações, criptos, etc) - Schema: mercado"""
    __tablename__ = "ativos"
    __table_args__ = (
        UniqueConstraint("codigo", name="uq_ativo_codigo"),
        UniqueConstraint("ticker_yf", name="uq_ativo_ticker_yf"),
        Index("idx_ativos_codigo", "codigo"),
        Index("idx_ativos_ticker_yf", "ticker_yf"),
        Index("idx_ativos_tipoativo", "idtipoativo"),
        {"schema": "mercado"},
    )

    idativo = Column(Integer, primary_key=True)
    codigo = Column(String(55), nullable=False)  # NVDA, PETR4
    ticker_yf = Column(String(55))  # NVDA, PETR4.SA (can be empty)
    idtipoativo = Column(Integer, ForeignKey("mercado.tipoativo.idtipoativo"))
    moeda = Column(String(100))  # BRL, USD

    # Relacionamentos
    tipo_ativo = relationship("TipoAtivo", back_populates="ativos")
    precos = relationship("PrecoHistorico", back_populates="ativo")
    posicoes = relationship("Posicao", back_populates="ativo")
    movimentacoes = relationship("MovimentacaoAtivo", back_populates="ativo")

    def __repr__(self):
        return f"<Ativo {self.codigo} ({self.ticker_yf})>"


class PrecoHistorico(Base):
    """Histórico de preços - Schema: mercado"""
    __tablename__ = "precos_historicos"
    __table_args__ = (
        UniqueConstraint("idativo", "data", name="uq_preco_ativo_data"),
        Index("idx_precos_ativo_data", "idativo", "data"),
        {"schema": "mercado"},
    )

    id = Column(Integer, primary_key=True)
    idativo = Column(Integer, ForeignKey("mercado.ativos.idativo", ondelete="CASCADE"), nullable=False)
    data = Column(Date, nullable=False)
    preco_moeda_local = Column(Numeric(10, 4))
    preco_real = Column(Numeric(10, 4))
    volume = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relacionamentos
    ativo = relationship("Ativo", back_populates="precos")

    def __repr__(self):
        return f"<PrecoHistorico {self.data}: R$ {self.preco_real}>"


class TaxaCambio(Base):
    """Taxa de câmbio USD/BRL - Schema: mercado"""
    __tablename__ = "taxa_cambio"
    __table_args__ = {"schema": "mercado"}

    id = Column(Integer, primary_key=True)
    data = Column(Date, unique=True)
    usd_brl = Column(Numeric(10, 4))
    criado_em = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<TaxaCambio {self.data}: {self.usd_brl}>"


# ============================================================
# SCHEMA: FINANCEIRO
# ============================================================

class Fundo(Base):
    """Fundo principal - Schema: financeiro"""
    __tablename__ = "fundo"
    __table_args__ = {"schema": "financeiro"}

    id = Column(Integer, primary_key=True)
    nome = Column(String(255), nullable=False)
    data_criacao = Column(Date, nullable=False)
    valor_cota_inicial = Column(Numeric(10, 2))
    pl_atual = Column(Numeric(15, 2))
    cotas_emitidas = Column(Numeric(15, 4))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relacionamentos
    posicoes = relationship("Posicao", back_populates="fundo")
    operacoes = relationship("OperacaoCota", back_populates="fundo")

    def __repr__(self):
        return f"<Fundo {self.nome}>"


class Posicao(Base):
    """Posição atual de cada ativo - Schema: financeiro"""
    __tablename__ = "posicoes"
    __table_args__ = (
        Index("idx_posicoes_fundo", "fundo_id"),
        Index("idx_posicoes_ativo", "idativo"),
        {"schema": "financeiro"},
    )

    id = Column(Integer, primary_key=True)
    fundo_id = Column(Integer, ForeignKey("financeiro.fundo.id", ondelete="CASCADE"), nullable=False)
    idativo = Column(Integer, ForeignKey("mercado.ativos.idativo", ondelete="CASCADE"), nullable=False)
    quantidade = Column(Numeric(15, 4))
    preco_medio_entrada = Column(Numeric(10, 4))
    data_ultima_atualizacao = Column(Date)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relacionamentos
    fundo = relationship("Fundo", back_populates="posicoes")
    ativo = relationship("Ativo", back_populates="posicoes")

    def __repr__(self):
        return f"<Posicao {self.ativo.codigo}: {self.quantidade}>"


class CotaHistorico(Base):
    """Histórico de cotas - Schema: financeiro"""
    __tablename__ = "cotas_historico"
    __table_args__ = (
        Index("idx_cotas_data", "data_calculo"),
        {"schema": "financeiro"},
    )

    id = Column(Integer, primary_key=True)
    valor_cota = Column(Numeric(10, 2))
    pl = Column(Numeric(15, 2))
    data_calculo = Column(Date)
    criado_em = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<CotaHistorico {self.data_calculo}: Cota={self.valor_cota}>"


# ============================================================
# SCHEMA: OPERACIONAL
# ============================================================

class MovimentacaoAtivo(Base):
    """Movimentações (compras/vendas) - Schema: operacional"""
    __tablename__ = "movimentacoes_ativos"
    __table_args__ = (
        CheckConstraint("tipo IN ('COMPRA', 'VENDA')", name="ck_movimentacao_tipo"),
        Index("idx_movimentacoes_data", "data_operacao"),
        Index("idx_movimentacoes_ativo", "idativo"),
        {"schema": "operacional"},
    )

    id = Column(Integer, primary_key=True)
    idativo = Column(Integer, ForeignKey("mercado.ativos.idativo", ondelete="CASCADE"), nullable=False)
    tipo = Column(String(10), nullable=False)
    quantidade = Column(Numeric(15, 4))
    preco_unitario = Column(Numeric(10, 4))
    data_operacao = Column(Date, nullable=False)
    comissao = Column(Numeric(10, 2), default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relacionamentos
    ativo = relationship("Ativo", back_populates="movimentacoes")

    def __repr__(self):
        return f"<MovimentacaoAtivo {self.tipo} {self.quantidade} de {self.ativo.codigo}>"


class OperacaoCota(Base):
    """Operações de cotas (aportes/resgates) - Schema: operacional"""
    __tablename__ = "operacoes_cota"
    __table_args__ = (
        CheckConstraint("tipo IN ('APORTE', 'RESGATE')", name="ck_operacao_tipo"),
        Index("idx_operacoes_fundo", "fundo_id"),
        Index("idx_operacoes_data", "data_operacao"),
        {"schema": "operacional"},
    )

    id = Column(Integer, primary_key=True)
    fundo_id = Column(Integer, ForeignKey("financeiro.fundo.id", ondelete="CASCADE"), nullable=False)
    tipo = Column(String(10), nullable=False)
    quantidade_cotas = Column(Numeric(15, 4))
    valor_total = Column(Numeric(15, 2))
    valor_cota_na_operacao = Column(Numeric(10, 2))
    data_operacao = Column(Date, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relacionamentos
    fundo = relationship("Fundo", back_populates="operacoes")

    def __repr__(self):
        return f"<OperacaoCota {self.tipo}: {self.quantidade_cotas} cotas>"
