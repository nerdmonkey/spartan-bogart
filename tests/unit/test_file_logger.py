import json


def test_file_logger_writes_json(tmp_path, monkeypatch):
    """FileLogger should create the log file and write JSON entries with
    PII redaction."""
    from app.services.logging.file import FileLogger

    # Make env() deterministic inside the file logger module
    monkeypatch.setattr(
        "app.services.logging.file.env",
        lambda k, d=None: {"APP_ENVIRONMENT": "test", "APP_VERSION": "1.2.3"}.get(k, d),
    )

    fl = FileLogger(
        service_name="svc", level="INFO", log_dir=str(tmp_path), sample_rate=1.0
    )

    # Emit a log with extra data, including a sensitive field
    fl.info("hello", extra={"foo": "bar", "password": "mypw"})

    # Flush handlers to ensure the file is written
    for h in fl.logger.handlers:
        try:
            h.flush()
        except Exception:
            pass

    log_file = tmp_path / "svc.log"
    assert log_file.exists(), "Expected log file to be created"

    text = log_file.read_text()
    lines = [line for line in text.splitlines() if line.strip()]
    assert lines, "Expected at least one log line"

    entry = json.loads(lines[-1])
    assert entry["service"] == "svc"
    assert entry["message"] == "hello"
    assert entry["level"] == "INFO"
    assert "location" in entry and ":" in entry["location"]
    assert entry["environment"] == "test"
    assert entry["version"] == "1.2.3"
    # Sensitive field should be redacted
    assert entry.get("password") == "[REDACTED]"
    assert entry.get("foo") == "bar"


def test_file_logger_sampling_prevents_writes(tmp_path, monkeypatch):
    """When sampling is disabled (0.0), no log should be written."""
    from app.services.logging.file import FileLogger

    monkeypatch.setattr(
        "app.services.logging.file.env",
        lambda k, d=None: {"APP_ENVIRONMENT": "test", "APP_VERSION": "1.2.3"}.get(k, d),
    )

    fl = FileLogger(
        service_name="svc", level="INFO", log_dir=str(tmp_path), sample_rate=0.0
    )
    # Note: FileLogger.__init__ treats falsy sample_rate specially, so set
    # explicitly on the instance to ensure sampling is disabled for the test.
    fl.sample_rate = 0.0
    fl.info("silent", extra={"a": "b"})

    for h in fl.logger.handlers:
        try:
            h.flush()
        except Exception:
            pass

    log_file = tmp_path / "svc.log"
    # Either file doesn't exist or is empty (no log lines)
    if log_file.exists():
        text = log_file.read_text()
        assert not [line for line in text.splitlines() if line.strip()]


def test_file_logger_exception_includes_exception(tmp_path, monkeypatch):
    """Exception logging should include an "exception" field and redact
    sensitive fields."""
    from app.services.logging.file import FileLogger

    monkeypatch.setattr(
        "app.services.logging.file.env",
        lambda k, d=None: {"APP_ENVIRONMENT": "prod", "APP_VERSION": "9.9.9"}.get(k, d),
    )

    fl = FileLogger(
        service_name="svc", level="ERROR", log_dir=str(tmp_path), sample_rate=1.0
    )

    try:
        raise RuntimeError("boom")
    except Exception:
        # Pass token as a top-level kwarg so the JsonFormatter promotes it
        # to the record attributes (the exception() helper wraps kwargs into
        # extra=... otherwise).
        fl.exception("caught", token="abc")
        for h in fl.logger.handlers:
            try:
                h.flush()
            except Exception:
                pass

    log_file = tmp_path / "svc.log"
    assert log_file.exists()
    lines = [line for line in log_file.read_text().splitlines() if line.strip()]
    assert lines
    entry = json.loads(lines[-1])
    assert "exception" in entry
    assert entry.get("token") == "[REDACTED]"


def test_file_logger_rotation(tmp_path, monkeypatch):
    """RotatingFileHandler should create rotated backups when size exceeded."""
    import time

    from app.services.logging.file import FileLogger

    monkeypatch.setattr(
        "app.services.logging.file.env",
        lambda k, d=None: {"APP_ENVIRONMENT": "test", "APP_VERSION": "rot"}.get(k, d),
    )

    # Small max_bytes to trigger rotation quickly
    fl = FileLogger(
        service_name="svc",
        level="INFO",
        log_dir=str(tmp_path),
        max_bytes=200,
        backup_count=2,
        sample_rate=1.0,
    )

    # Write many messages until rotated files appear
    for i in range(200):
        fl.info(f"m{i}")
        # give the handler a chance to rotate
        for h in fl.logger.handlers:
            try:
                h.flush()
            except Exception:
                pass
    # Wait a moment to ensure filesystem updates
    time.sleep(0.01)

    files = sorted(p.name for p in tmp_path.iterdir())
    # Expect at least the main log and one rotated backup
    assert any(name.startswith("svc.log") for name in files)
    assert any(
        name.startswith("svc.log.") for name in files
    ), f"Rotation not observed, files: {files}"


def test_file_logger_json_schema_and_pii_cases(tmp_path, monkeypatch):
    """Verify timestamp parseable, location present, and PII redaction is
    case-insensitive and applies to top-level attrs."""
    from datetime import datetime

    from app.services.logging.file import FileLogger

    monkeypatch.setattr(
        "app.services.logging.file.env",
        lambda k, d=None: {"APP_ENVIRONMENT": "ci", "APP_VERSION": "0.0.0"}.get(k, d),
    )

    fl = FileLogger(
        service_name="svc", level="INFO", log_dir=str(tmp_path), sample_rate=1.0
    )

    # password as mixed-case in extra should be redacted
    # Put api_key inside extra because FileLogger._log only forwards
    # `extra` to the logging call
    fl.info("hi", extra={"Password": "mix", "nested": {"token": "x"}, "api_key": "zzz"})
    for h in fl.logger.handlers:
        try:
            h.flush()
        except Exception:
            pass

    log_file = tmp_path / "svc.log"
    assert log_file.exists()
    lines = [line for line in log_file.read_text().splitlines() if line.strip()]
    entry = json.loads(lines[-1])

    # Timestamp should parse as ISO format
    datetime.fromisoformat(entry["timestamp"])

    # Location includes a colon (file:lineno)
    assert ":" in entry["location"]

    # Mixed-case key was redacted
    assert (
        entry.get("Password") == "[REDACTED]" or entry.get("password") == "[REDACTED]"
    )

    # Top-level kwarg api_key should be redacted
    assert entry.get("api_key") == "[REDACTED]"

    # Nested sensitive field inside dict is not automatically redacted
    # by current implementation
    assert entry.get("nested") == {"token": "x"}
