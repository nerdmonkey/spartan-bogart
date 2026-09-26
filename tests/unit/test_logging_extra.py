import json


def test_base_logger_abstract_methods_via_subclass():
    from app.services.logging.base import BaseLogger

    class ConcreteLogger(BaseLogger):
        def info(self, message: str, **kwargs):
            return super().info(message, **kwargs)

        def error(self, message: str, **kwargs):
            return super().error(message, **kwargs)

        def warning(self, message: str, **kwargs):
            return super().warning(message, **kwargs)

        def debug(self, message: str, **kwargs):
            return super().debug(message, **kwargs)

        def exception(self, message: str, **kwargs):
            return super().exception(message, **kwargs)

    logger = ConcreteLogger()
    assert logger.info("m") is None
    assert logger.error("m") is None
    assert logger.warning("m") is None
    assert logger.debug("m") is None
    assert logger.exception("m") is None


def test_prettify_extra_falls_back_on_serialization_error():
    from app.services.logging.both import _prettify_extra

    class Unserializable:
        def __repr__(self):
            return "unserializable-obj"

    pretty = _prettify_extra({"thing": Unserializable()})
    assert "unserializable-obj" in pretty


def test_bothlogger_log_warning_debug_error_exception(monkeypatch):
    from app.services.logging.both import BothLogger

    calls = {"file": [], "stream": []}

    class FakeFile:
        def __init__(self, *a, **k):
            pass

        def log(self, message, level=None):
            calls["file"].append(("log", message, level))

        def warning(self, message, **kwargs):
            calls["file"].append(("warning", message, kwargs))

        def error(self, message, **kwargs):
            calls["file"].append(("error", message, kwargs))

        def debug(self, message, **kwargs):
            calls["file"].append(("debug", message, kwargs))

        def exception(self, message, *args, **kwargs):
            calls["file"].append(("exception", message, args, kwargs))

    class FakeStream:
        def __init__(self, *a, **k):
            pass

        def log(self, message, level=None):
            calls["stream"].append(("log", message, level))

        def warning(self, message, **kwargs):
            calls["stream"].append(("warning", message))

        def error(self, message, **kwargs):
            calls["stream"].append(("error", message))

        def debug(self, message, **kwargs):
            calls["stream"].append(("debug", message))

        def exception(self, message, *args, **kwargs):
            calls["stream"].append(("exception", message))

    import app.services.logging.both as both_mod

    monkeypatch.setattr(both_mod, "FileLogger", FakeFile)
    monkeypatch.setattr(both_mod, "StreamLogger", FakeStream)

    b = BothLogger(service_name="svc", level="INFO")

    b.log("plain", level="INFO")
    assert ("log", "plain", "INFO") in calls["file"]
    assert ("log", "plain", "INFO") in calls["stream"]

    b.warning("w", extra={"a": 1})
    assert any(c[0] == "warning" for c in calls["file"])
    assert any(c[0] == "warning" for c in calls["stream"])

    b.error("e", extra={"a": 1})
    assert any(c[0] == "error" for c in calls["file"])
    assert any(c[0] == "error" for c in calls["stream"])

    b.debug("d", extra={"a": 1})
    assert any(c[0] == "debug" for c in calls["file"])
    assert any(c[0] == "debug" for c in calls["stream"])

    b.exception("x", extra={"a": 1})
    assert any(c[0] == "exception" for c in calls["file"])
    assert any(c[0] == "exception" for c in calls["stream"])


def test_file_logger_creates_missing_log_dir(tmp_path, monkeypatch):
    from app.services.logging.file import FileLogger

    monkeypatch.setattr(
        "app.services.logging.file.env",
        lambda k, d=None: {"APP_ENVIRONMENT": "test", "APP_VERSION": "1.0"}.get(k, d),
    )

    missing_dir = tmp_path / "does" / "not" / "exist"
    assert not missing_dir.exists()

    FileLogger(service_name="svc", level="INFO", log_dir=str(missing_dir))

    assert missing_dir.exists()


def test_file_logger_log_debug_critical_and_inject_lambda_context(tmp_path, monkeypatch):
    from app.services.logging.file import FileLogger

    monkeypatch.setattr(
        "app.services.logging.file.env",
        lambda k, d=None: {"APP_ENVIRONMENT": "test", "APP_VERSION": "1.0"}.get(k, d),
    )

    fl = FileLogger(service_name="svc", level="DEBUG", log_dir=str(tmp_path))

    fl.log("via-log")
    fl.debug("dbg")
    fl.critical("crit")

    for h in fl.logger.handlers:
        h.flush()

    log_file = tmp_path / "svc.log"
    lines = [line for line in log_file.read_text().splitlines() if line.strip()]
    messages = [json.loads(line)["message"] for line in lines]
    assert "via-log" in messages
    assert "dbg" in messages
    assert "crit" in messages

    wrapped = fl.inject_lambda_context(lambda event, context: (event, context))
    assert wrapped("evt", "ctx") == ("evt", "ctx")


def test_json_formatter_fallback_location_when_no_valid_frame(tmp_path, monkeypatch):
    from app.services.logging.file import _JsonFormatter

    monkeypatch.setattr(
        "app.services.logging.file.env",
        lambda k, d=None: {"APP_ENVIRONMENT": "test", "APP_VERSION": "1.0"}.get(k, d),
    )

    formatter = _JsonFormatter(service_name="svc")
    monkeypatch.setattr(
        "app.services.logging.file.inspect.stack",
        lambda: [],
    )

    class FakeRecord:
        levelname = "INFO"
        pathname = "/services/logging/inside.py"
        lineno = 42
        exc_info = None

        def getMessage(self):
            return "hi"

    record = FakeRecord()
    record.__dict__.update(
        {
            "levelname": "INFO",
            "pathname": "/services/logging/inside.py",
            "lineno": 42,
            "exc_info": None,
        }
    )

    formatted = formatter.format(record)
    entry = json.loads(formatted)
    assert entry["location"].endswith(":42")


def test_json_formatter_fallback_location_relpath_error(monkeypatch):
    from app.services.logging.file import _JsonFormatter

    monkeypatch.setattr(
        "app.services.logging.file.env",
        lambda k, d=None: {"APP_ENVIRONMENT": "test", "APP_VERSION": "1.0"}.get(k, d),
    )
    formatter = _JsonFormatter(service_name="svc")

    class FakeRecord:
        pathname = "/some/path.py"
        lineno = 7

    record = FakeRecord()

    def raise_value_error(*args, **kwargs):
        raise ValueError("cannot relpath")

    monkeypatch.setattr(
        "app.services.logging.file.os.path.relpath", raise_value_error
    )

    rel_path, lineno = formatter._get_fallback_location(record)
    assert rel_path == "path.py"
    assert lineno == 7


def test_stream_logger_exception_writes_error_with_exc_info(monkeypatch):
    from app.services.logging.stream import StreamLogger

    s = StreamLogger(service_name="svc", level="ERROR")

    calls = []

    def fake_error(message, exc_info=False):
        calls.append((message, exc_info))

    s.logger.error = fake_error

    try:
        raise RuntimeError("boom")
    except RuntimeError:
        s.exception("caught", extra={"a": 1})

    assert calls
    message, exc_info = calls[0]
    assert "caught" in message
    assert exc_info is True


def test_stream_logger_colorama_import_fallback(monkeypatch):
    import builtins
    import importlib
    import sys

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "colorama":
            raise ImportError("no colorama")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    sys.modules.pop("app.services.logging.stream", None)

    try:
        stream_mod = importlib.import_module("app.services.logging.stream")
        assert stream_mod.COLORAMA_AVAILABLE is False
        assert stream_mod.LEVEL_COLORS["INFO"] == ""
        assert stream_mod.RESET == ""
    finally:
        sys.modules.pop("app.services.logging.stream", None)
        importlib.import_module("app.services.logging.stream")
