import importlib
from types import SimpleNamespace

import pytest


def make_env(mapping):
    """Return an env(...) replacement that supports var_name or no-arg calls."""

    def _env(var_name=None, default=None):
        if var_name is None:
            # Return an object with attributes for no-arg usage
            return SimpleNamespace(**{k: v for k, v in mapping.items()})
        return mapping.get(var_name, default)

    return _env


def test_appsettings_dot_access_and_defaults(monkeypatch):
    mapping = {
        "APP_NAME": "myapp",
        "APP_ENVIRONMENT": "dev",
        "APP_DEBUG": True,
        "ALLOWED_ORIGINS": "a,b",
        "LOG_LEVEL": "INFO",
        "LOG_DIR": "logs",
        "DB_NAME": "ddb",
    }

    monkeypatch.setattr("app.helpers.environment.env", make_env(mapping))

    # Reload the module so class-level env() calls pick up the patched env
    cfg_mod = importlib.reload(importlib.import_module("config.app"))
    cfg = cfg_mod.config

    assert cfg.app_name == "myapp"
    assert cfg.environment == "dev"
    assert cfg.debug is True
    assert cfg.allowed_origins == ["a", "b"]

    # Dot access into nested settings
    assert cfg("log.level") == "INFO"
    assert cfg("db.name") == "ddb"
    # Missing key returns default
    assert cfg("no.such.key", default=123) == 123


def test_database_settings_port_conversion_and_defaults(monkeypatch):
    mapping = {"DB_PORT": "5432", "DB_TYPE": "postgres", "DB_NAME": "spartan"}
    monkeypatch.setattr("app.helpers.environment.env", make_env(mapping))

    db_mod = importlib.reload(importlib.import_module("config.database"))
    # The class attributes should reflect env values
    ds = db_mod.DatabaseSettings()

    assert ds.type == "postgres"
    # Note: DatabaseSettings reads env() directly, which returns strings here — expect '5432'
    assert ds.port == "5432"
    assert ds.name == "spartan"


def test_handlers_singleton_and_handler_configs(monkeypatch):
    mapping = {"APP_NAME": "appx", "LOG_LEVEL": "WARN", "LOG_FILE": "/tmp/appx.log"}
    monkeypatch.setattr("app.helpers.environment.env", make_env(mapping))

    # Reload logging config module to re-create singleton with patched env
    log_mod = importlib.reload(importlib.import_module("config.logging"))

    # handler() convenience should return the pydantic config models
    file_handler = log_mod.handler("file")
    assert file_handler is not None
    assert file_handler.class_ == "logging.FileHandler"
    assert file_handler.path == "/tmp/appx.log"

    console_handler = log_mod.handler("console")
    assert console_handler.name == "appx"

    # TcpHandlerConfig port validation: invalid port should raise
    from config.logging import TcpHandlerConfig

    with pytest.raises(Exception):
        TcpHandlerConfig(
            class_="x", formatter="json", name="n", level="INFO", host="h", port=70000
        )


def test_filehandler_pydantic_serialization_and_validation(monkeypatch):
    """Ensure json_deserializer attribute exists but is excluded from model dumps and invalid values raise."""

    mapping = {"APP_NAME": "appx", "LOG_LEVEL": "WARN", "LOG_FILE": "/tmp/appx.log"}
    monkeypatch.setattr("app.helpers.environment.env", make_env(mapping))

    log_mod = importlib.reload(importlib.import_module("config.logging"))

    # Default FileHandlerConfig should have a callable json_deserializer attribute
    fh = log_mod.FileHandlerConfig(
        class_="logging.FileHandler",
        formatter="json",
        name="appx",
        level="WARN",
        path="/tmp/a",
    )
    assert callable(getattr(fh, "json_deserializer"))

    # model dump should not contain json_deserializer (field has exclude=True)
    dump = fh.model_dump() if hasattr(fh, "model_dump") else fh.dict()
    assert "json_deserializer" not in dump

    # Passing a non-callable json_deserializer should raise
    with pytest.raises(Exception):
        log_mod.FileHandlerConfig(
            class_="x",
            formatter="json",
            name="n",
            level="INFO",
            path="/tmp/a",
            json_deserializer=123,
        )


def test_handlers_singleton_behavior(monkeypatch):
    mapping = {"APP_NAME": "appx", "LOG_LEVEL": "WARN", "LOG_FILE": "/tmp/appx.log"}
    monkeypatch.setattr("app.helpers.environment.env", make_env(mapping))

    log_mod = importlib.reload(importlib.import_module("config.logging"))
    h1 = log_mod.Handlers()
    h2 = log_mod.Handlers()
    assert h1 is h2
    # get_handler should return None for unknown types
    assert h1.get_handler("unknown") is None
