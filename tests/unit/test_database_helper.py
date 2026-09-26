from types import SimpleNamespace

import pytest


def _settings(**overrides):
    base = dict(
        DB_TYPE="sqlite",
        DB_NAME="spartan",
        DB_USERNAME="user",
        DB_PASSWORD="pw",
        DB_HOST="localhost",
        DB_PORT=5432,
        DB_DRIVER="ODBC Driver 17 for SQL Server",
        APP_RUNTIME="lambda",
    )
    base.update(overrides)
    return SimpleNamespace(**base)


@pytest.fixture(autouse=True)
def _clear_cache():
    from app.helpers import database

    database.get_engine.cache_clear()
    database.get_session_factory.cache_clear()
    yield
    database.get_engine.cache_clear()
    database.get_session_factory.cache_clear()


def test_build_database_url_sqlite(monkeypatch):
    from app.helpers import database

    monkeypatch.setattr(database, "env", lambda: _settings(DB_TYPE="sqlite"))
    url = database._build_database_url()
    assert url == "sqlite:///./database/spartan.db"


def test_build_database_url_psql(monkeypatch):
    from app.helpers import database

    monkeypatch.setattr(database, "env", lambda: _settings(DB_TYPE="psql"))
    url = database._build_database_url()
    assert url.startswith("postgresql+pg8000://user:pw@localhost:5432/spartan")


def test_build_database_url_mysql(monkeypatch):
    from app.helpers import database

    monkeypatch.setattr(database, "env", lambda: _settings(DB_TYPE="mysql"))
    url = database._build_database_url()
    assert url.startswith("mysql+pymysql://user:pw@localhost:5432/spartan")


def test_build_database_url_mssql_includes_driver(monkeypatch):
    from app.helpers import database

    monkeypatch.setattr(database, "env", lambda: _settings(DB_TYPE="mssql"))
    url = database._build_database_url()
    assert url.startswith("mssql+pyodbc://user:pw@localhost:5432/spartan")
    assert "driver=ODBC Driver 17 for SQL Server" in url


def test_build_database_url_unsupported_raises(monkeypatch):
    from app.helpers import database

    monkeypatch.setattr(database, "env", lambda: _settings(DB_TYPE="oracle"))
    with pytest.raises(ValueError):
        database._build_database_url()


def test_get_engine_container_uses_larger_pool(monkeypatch, tmp_path):
    from app.helpers import database

    monkeypatch.chdir(tmp_path)
    (tmp_path / "database").mkdir()
    monkeypatch.setattr(
        database, "env", lambda: _settings(DB_TYPE="sqlite", APP_RUNTIME="container")
    )
    engine = database.get_engine()
    assert engine.pool.size() == 20


def test_get_engine_lambda_uses_minimal_pool(monkeypatch, tmp_path):
    from app.helpers import database

    monkeypatch.chdir(tmp_path)
    (tmp_path / "database").mkdir()
    monkeypatch.setattr(
        database, "env", lambda: _settings(DB_TYPE="sqlite", APP_RUNTIME="lambda")
    )
    engine = database.get_engine()
    assert engine.pool.size() == 1


def test_get_session_factory_container_is_scoped(monkeypatch, tmp_path):
    from sqlalchemy.orm import scoped_session

    from app.helpers import database

    monkeypatch.chdir(tmp_path)
    (tmp_path / "database").mkdir()
    monkeypatch.setattr(
        database, "env", lambda: _settings(DB_TYPE="sqlite", APP_RUNTIME="container")
    )
    factory = database.get_session_factory()
    assert isinstance(factory, scoped_session)


def test_get_session_factory_lambda_is_plain_sessionmaker(monkeypatch, tmp_path):
    from sqlalchemy.orm import scoped_session

    from app.helpers import database

    monkeypatch.chdir(tmp_path)
    (tmp_path / "database").mkdir()
    monkeypatch.setattr(
        database, "env", lambda: _settings(DB_TYPE="sqlite", APP_RUNTIME="lambda")
    )
    factory = database.get_session_factory()
    assert not isinstance(factory, scoped_session)
