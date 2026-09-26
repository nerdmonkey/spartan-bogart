import io
import json

import pytest


def _make_logger(
    monkeypatch, sample_rate=1.0, environment="test", version="1.0.0", level="DEBUG"
):
    from app.services.logging.cloud import CloudWatchLogger

    monkeypatch.setattr(
        "app.services.logging.cloud.env",
        lambda k=None, d=None: {
            "LOG_SAMPLE_RATE": str(sample_rate),
            "APP_ENVIRONMENT": environment,
            "APP_VERSION": version,
        }.get(k, d),
    )

    cw = CloudWatchLogger(service_name="svc", level=level, sample_rate=sample_rate)

    buffer = io.StringIO()
    for handler in cw.logger._logger.handlers:
        if hasattr(handler, "stream"):
            handler.stream = buffer

    return cw, buffer


def _lines(buffer):
    return [line for line in buffer.getvalue().splitlines() if line.strip()]


def test_info_emits_json_with_environment_metadata_and_redacts_pii(monkeypatch):
    cw, buffer = _make_logger(monkeypatch)

    cw.info(
        "hello",
        normal_field="value",
        password="secret",
        api_key="abc",
    )

    lines = _lines(buffer)
    assert lines
    entry = json.loads(lines[-1])
    assert entry["environment"] == "test"
    assert entry["version"] == "1.0.0"
    assert "location" in entry
    assert entry["normal_field"] == "value"
    assert entry["password"] == "[REDACTED]"
    assert entry["api_key"] == "[REDACTED]"


@pytest.mark.parametrize(
    "method_name", ["info", "error", "warning", "debug", "critical"]
)
def test_all_log_levels_emit_and_redact_top_level_pii(monkeypatch, method_name):
    cw, buffer = _make_logger(monkeypatch)

    getattr(cw, method_name)("msg", other="ok", token="topsecret")

    lines = _lines(buffer)
    assert lines
    entry = json.loads(lines[-1])
    assert entry["other"] == "ok"
    assert entry["message"] == "msg"
    assert entry["token"] == "[REDACTED]"


def test_exception_emits_and_redacts_top_level_pii(monkeypatch):
    cw, buffer = _make_logger(monkeypatch)

    try:
        raise RuntimeError("boom")
    except RuntimeError:
        cw.exception("caught", extra_field="value", secret="hide-me")

    lines = _lines(buffer)
    assert lines
    entry = json.loads(lines[-1])
    assert entry["message"] == "caught"
    assert entry["extra_field"] == "value"
    assert entry["secret"] == "[REDACTED]"


def test_sampling_zero_prevents_all_log_calls(monkeypatch):
    cw, buffer = _make_logger(monkeypatch, sample_rate=0.0)
    cw.sample_rate = 0.0

    cw.info("silent")
    cw.error("silent")
    cw.warning("silent")
    cw.debug("silent")
    cw.critical("silent")
    try:
        raise RuntimeError("x")
    except RuntimeError:
        cw.exception("silent")

    assert not _lines(buffer)


def test_custom_formatter_also_redacts_a_nested_extra_dict(monkeypatch):
    """Belt-and-suspenders: sanitize a nested "extra" dict too, in case an
    upstream formatter ever nests fields that way instead of flattening
    them (which is what aws_lambda_powertools actually does today)."""
    cw, _ = _make_logger(monkeypatch)

    handler = next(h for h in cw.logger._logger.handlers if hasattr(h, "formatter"))

    def fake_original_format(record):
        return json.dumps(
            {
                "message": "hi",
                "extra": {"password": "secret", "keep": "value"},
            }
        )

    handler.formatter.format = fake_original_format
    cw._setup_custom_formatter()

    result = handler.formatter.format(object())
    entry = json.loads(result)
    assert entry["extra"]["password"] == "[REDACTED]"
    assert entry["extra"]["keep"] == "value"


def test_custom_formatter_falls_back_on_non_json_message(monkeypatch):
    cw, _ = _make_logger(monkeypatch)

    handler = next(h for h in cw.logger._logger.handlers if hasattr(h, "formatter"))

    def fake_original_format(record):
        return "not-json-at-all"

    handler.formatter.format = fake_original_format
    cw._setup_custom_formatter()

    result = handler.formatter.format(object())
    assert result == "not-json-at-all"


def test_get_caller_location_fallback_when_no_matching_frame(monkeypatch):
    cw, _ = _make_logger(monkeypatch)

    class FakeFrame:
        def __init__(self, filename, lineno):
            self.filename = filename
            self.lineno = lineno

    monkeypatch.setattr(
        "app.services.logging.cloud.inspect.stack",
        lambda: [FakeFrame("/services/logging/cloud.py", 10)],
    )

    assert cw._get_caller_location() == "unknown:0"


def test_get_caller_location_handles_relpath_error(monkeypatch):
    cw, _ = _make_logger(monkeypatch)

    class FakeFrame:
        def __init__(self, filename, lineno):
            self.filename = filename
            self.lineno = lineno

    valid_filename = f"{cw.project_root}/some_module.py"

    monkeypatch.setattr(
        "app.services.logging.cloud.inspect.stack",
        lambda: [FakeFrame(valid_filename, 99)],
    )

    def raise_value_error(*args, **kwargs):
        raise ValueError("cannot relpath")

    monkeypatch.setattr(
        "app.services.logging.cloud.os.path.relpath", raise_value_error
    )

    location = cw._get_caller_location()
    assert location == "some_module.py:99"


def test_inject_lambda_context_delegates(monkeypatch):
    cw, _ = _make_logger(monkeypatch)

    calls = {}

    def fake_inject(*args, **kwargs):
        calls["args"] = args
        calls["kwargs"] = kwargs
        return "decorated"

    cw.logger.inject_lambda_context = fake_inject

    result = cw.inject_lambda_context(log_event=True)
    assert result == "decorated"
    assert calls["kwargs"] == {"log_event": True}
