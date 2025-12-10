"""
Conexão com PostgreSQL usando SQLAlchemy
"""
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from config import DATABASE_URL, DB_SCHEMA

logger = logging.getLogger(__name__)

# Base para models ORM
Base = declarative_base()

# Criar engine
try:
    engine = create_engine(
        DATABASE_URL,
        echo=False,  # Mudar para True para debug SQL
        pool_pre_ping=True,  # Testar conexão antes de usar
    )
    
    # Testar conexão
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        logger.info("✓ Conexão PostgreSQL estabelecida com sucesso")
        print("✓ Conexão PostgreSQL OK")
except Exception as e:
    logger.error(f"✗ Erro ao conectar PostgreSQL: {e}")
    print(f"✗ Erro ao conectar PostgreSQL: {e}")
    raise

# Session factory
Session = sessionmaker(bind=engine, expire_on_commit=False)


def get_session():
    """Obter nova sessão de banco de dados"""
    return Session()


def create_schema():
    """Criar schemas necessários se não existirem"""
    try:
        with engine.connect() as conn:
            # Criar schemas
            schemas = ["financeiro", "mercado", "operacional"]
            for schema in schemas:
                conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema}"))
            conn.commit()
            logger.info("✓ Schemas criados/verificados com sucesso")
            print("✓ Schemas criados/verificados com sucesso")
    except Exception as e:
        logger.error(f"✗ Erro ao criar schemas: {e}")
        print(f"✗ Erro ao criar schemas: {e}")
        raise


def create_all_tables():
    """Criar todas as tabelas no banco de dados"""
    try:
        # Importar models para registrar no Base
        from .models import (
            Fundo,
            Ativo,
            PrecoHistorico,
            Posicao,
            MovimentacaoAtivo,
            OperacaoCota,
            CotaHistorico,
            TaxaCambio,
        )
        
        # Criar schema primeiro
        create_schema()
        
        # Criar tabelas
        Base.metadata.create_all(engine)
        logger.info("✓ Tabelas criadas/verificadas com sucesso")
        print("✓ Tabelas criadas/verificadas com sucesso")
    except Exception as e:
        logger.error(f"✗ Erro ao criar tabelas: {e}")
        print(f"✗ Erro ao criar tabelas: {e}")
        raise
