import pytest


def test_logger_factory_stream_and_invalid(monkeypatch):
    from app.services.logging.factory import LoggerFactory
    from app.services.logging.stream import StreamLogger

    # Explicit stream logger
    logger = LoggerFactory.create_logger("svc", logger_type="stream")
    assert isinstance(logger, StreamLogger)

    # Unknown type raises
    with pytest.raises(ValueError):
        LoggerFactory.create_logger("svc", logger_type="nope")


def test_stream_logger_format_and_fallback(monkeypatch):
    from app.services.logging.stream import StreamLogger

    class FakeInternalLogger:
        def __init__(self):
            self.calls = []

        def info(self, msg):
            self.calls.append(("info", msg))

        def debug(self, msg):
            self.calls.append(("debug", msg))

        def error(self, msg, **kwargs):
            self.calls.append(("error", msg))

        def warning(self, msg):
            self.calls.append(("warning", msg))

        def exception(self, msg, **kwargs):
            self.calls.append(("exception", msg))

    s = StreamLogger(service_name="svc", level="INFO")
    fake = FakeInternalLogger()
    # Replace underlying logger
    s.logger = fake

    # Format message directly
    formatted = s._format_message("INFO", "hello", extra={"a": 1})
    assert "svc" in formatted
    assert "hello" in formatted
    assert "extra" in formatted

    # info should call fake.info
    s.info("hi")
    assert fake.calls[-1][0] == "info"

    # unknown level should fallback to info
    s.log("msg", level="UNKNOWN")
    assert fake.calls[-1][0] == "info"


def test_prettify_extra_and_bothlogger_delegation(monkeypatch):
    """Test _prettify_extra behavior and BothLogger delegation."""
    _test_prettify_extra()
    _test_bothlogger_delegation(monkeypatch)


def _test_prettify_extra():
    """Test _prettify_extra behavior directly."""
    from app.services.logging.both import _prettify_extra

    extra = {"password": "s", "name": "bob"}
    pretty = _prettify_extra(extra)
    # Should redact password and be valid JSON inside string
    assert "[REDACTED]" in pretty
    assert "bob" in pretty


def _test_bothlogger_delegation(monkeypatch):
    """Test BothLogger delegates to file and stream loggers."""
    from app.services.logging.both import BothLogger

    calls = {"file": [], "stream": []}
    fake_file = _create_fake_file_logger(calls)
    fake_stream = _create_fake_stream_logger(calls)

    _patch_logger_classes(monkeypatch, fake_file, fake_stream)

    b = BothLogger(service_name="svc", level="INFO")
    b.info("hello", extra={"password": "x", "foo": "bar"})

    _assert_delegation_worked(calls)


def _create_fake_file_logger(calls):
    """Create fake file logger class."""

    class FakeFile:
        def __init__(self, *args, **kwargs):
            pass

        def log(self, message, level=None):
            calls["file"].append(("log", message, level))

        def info(self, message, **kwargs):
            calls["file"].append(("info", message, kwargs))

        def warning(self, message, **kwargs):
            calls["file"].append(("warning", message, kwargs))

        def error(self, message, **kwargs):
            calls["file"].append(("error", message, kwargs))

        def debug(self, message, **kwargs):
            calls["file"].append(("debug", message, kwargs))

        def exception(self, message, *args, **kwargs):
            calls["file"].append(("exception", message, args, kwargs))

    return FakeFile


def _create_fake_stream_logger(calls):
    """Create fake stream logger class."""

    class FakeStream:
        def __init__(self, *args, **kwargs):
            pass

        def log(self, message, level=None):
            calls["stream"].append(("log", message, level))

        def info(self, message, **kwargs):
            calls["stream"].append(("info", message))

        def warning(self, message, **kwargs):
            calls["stream"].append(("warning", message))

        def error(self, message, **kwargs):
            calls["stream"].append(("error", message))

        def debug(self, message, **kwargs):
            calls["stream"].append(("debug", message))

        def exception(self, message, *args, **kwargs):
            calls["stream"].append(("exception", message))

    return FakeStream


def _patch_logger_classes(monkeypatch, fake_file, fake_stream):
    """Patch the concrete logger classes in the both module."""
    import app.services.logging.both as both_mod

    monkeypatch.setattr(both_mod, "FileLogger", fake_file)
    monkeypatch.setattr(both_mod, "StreamLogger", fake_stream)


def _assert_delegation_worked(calls):
    """Assert that delegation to both loggers worked correctly."""
    # File logger should have received an info call with kwargs containing stacklevel
    assert any(c[0] == "info" for c in calls["file"])
    # Stream logger should have an info call where message includes prettified extra
    assert any(c[0] == "info" and "extra" in c[1] for c in calls["stream"])
