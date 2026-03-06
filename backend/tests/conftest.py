from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from backend.app.bootstrap import init_database
from backend.app.db import Base, get_session
from backend.app.main import app


@pytest.fixture()
def test_db(tmp_path: Path):
    db_path = tmp_path / 'test.db'
    engine = create_engine(f"sqlite:///{db_path.as_posix()}", connect_args={'check_same_thread': False}, future=True)
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    Base.metadata.create_all(bind=engine)
    with engine.begin() as conn:
        conn.execute(text('CREATE TABLE DIM_ATIVO (ID_ATIVO INTEGER PRIMARY KEY, CD_ATIVO TEXT, MOEDA TEXT, PRECO_ONLINE INTEGER DEFAULT 0, FATOR_PRECO NUMERIC DEFAULT 1)'))
        conn.execute(text('CREATE TABLE DIM_ATIVO_MAPPING (ID_ATIVO INTEGER PRIMARY KEY, CD_ATIVO TEXT, CD_YF TEXT)'))
    yield engine, TestingSessionLocal
    engine.dispose()


@pytest.fixture()
def client(test_db):
    engine, TestingSessionLocal = test_db

    def override_get_session():
        session = TestingSessionLocal()
        try:
            yield session
            session.commit()
        finally:
            session.close()

    app.dependency_overrides[get_session] = override_get_session
    with TestClient(app) as test_client:
        yield test_client, TestingSessionLocal
    app.dependency_overrides.clear()
