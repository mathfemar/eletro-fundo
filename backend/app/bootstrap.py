from sqlalchemy import inspect, text

from .db import Base, engine


def init_database() -> None:
    Base.metadata.create_all(bind=engine)
    with engine.begin() as connection:
        inspector = inspect(connection)
        existing = set(inspector.get_table_names())
        if 'DIM_ATIVO' not in existing:
            connection.execute(text('CREATE TABLE IF NOT EXISTS DIM_ATIVO (ID_ATIVO INTEGER PRIMARY KEY, CD_ATIVO TEXT, PRECO_ONLINE INTEGER DEFAULT 0)'))
        if 'DIM_ATIVO_MAPPING' not in existing:
            connection.execute(text('CREATE TABLE IF NOT EXISTS DIM_ATIVO_MAPPING (ID_ATIVO INTEGER PRIMARY KEY, CD_ATIVO TEXT, CD_YF TEXT)'))
