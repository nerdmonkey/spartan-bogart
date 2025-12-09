"""
Unit tests for the improved GCloudLogger implementation.
Tests the GCP best practices version with structured logging.
"""

import json
from unittest.mock import patch


def test_gcloud_logger_basic_initialization(monkeypatch):
    """Test that GCloudLogger initializes correctly."""
    from app.services.logging.gcloud import GCloudLogger

    logger = GCloudLogger("test-service", level="INFO", sample_rate=1.0)

    assert logger.service_name == "test-service"
    assert logger.level == "INFO"
    assert logger.sample_rate == 1.0
    assert logger.use_json_stdout is True


def test_gcloud_logger_fallback_when_client_unavailable(monkeypatch):
    """Test that logger always uses JSON stdout (no GCP client needed)."""
    from app.services.logging.gcloud import GCloudLogger

    logger = GCloudLogger("test-service")

    assert logger.use_json_stdout is True


def test_gcloud_logger_info_with_structured_data(monkeypatch, capsys):
    """Test that info() creates structured logs with user data."""
    from app.services.logging.gcloud import GCloudLogger

    logger = GCloudLogger("test-service", sample_rate=1.0)
    logger.info("Test message", extra={"user_id": "123", "action": "login"})

    # Capture stdout
    captured = capsys.readouterr()
    log_output = json.loads(captured.out.strip())

    # Check JSON payload contains our data
    assert log_output["message"] == "Test message"
    assert log_output["user_id"] == "123"
    assert log_output["action"] == "login"
    assert log_output["service"] == "test-service"
    assert log_output["severity"] == "INFO"


def test_gcloud_logger_pii_sanitization(monkeypatch, capsys):
    """Test that sensitive fields are redacted."""
    from app.services.logging.gcloud import GCloudLogger

    logger = GCloudLogger("test-service", sample_rate=1.0)
    logger.info(
        "Test",
        extra={"password": "secret123", "token": "abc", "safe_field": "visible"},
    )

    captured = capsys.readouterr()
    log_output = json.loads(captured.out.strip())

    assert log_output["password"] == "[REDACTED]"
    assert log_output["token"] == "[REDACTED]"
    assert log_output["safe_field"] == "visible"


def test_gcloud_logger_sampling(monkeypatch, capsys):
    """Test that sampling works correctly."""
    from app.services.logging.gcloud import GCloudLogger

    # Test 0% sampling - nothing should be logged
    logger = GCloudLogger("test-service", sample_rate=0.0)
    logger.info("Should not log")

    captured = capsys.readouterr()
    assert captured.out == ""

    # Test 100% sampling - should log
    logger = GCloudLogger("test-service", sample_rate=1.0)
    logger.info("Should log")

    captured = capsys.readouterr()
    assert "Should log" in captured.out


def test_gcloud_logger_cloud_run_detection(monkeypatch, capsys):
    """Test that Cloud Run environment is detected."""

    # Mock env() to return Cloud Run environment values
    def mock_env(key, default=None):
        env_values = {
            "K_SERVICE": "my-service",
            "APP_ENVIRONMENT": "production",
            "APP_VERSION": "v1.0",
        }
        return env_values.get(key, default)

    with patch("app.services.logging.gcloud.env", side_effect=mock_env):
        from app.services.logging.gcloud import GCloudLogger

        logger = GCloudLogger("test-service", sample_rate=1.0)

        # Should detect Cloud Run
        assert logger._is_cloud_run() is True

        # Log should include service metadata
        logger.info("Test")
        captured = capsys.readouterr()
        log_output = json.loads(captured.out.strip())

        assert log_output["service"] == "test-service"
        assert log_output["environment"] == "production"
        assert log_output["version"] == "v1.0"


def test_gcloud_logger_exception_with_context(monkeypatch, capsys):
    """Test that exception() captures exception details."""
    from app.services.logging.gcloud import GCloudLogger

    logger = GCloudLogger("test-service", sample_rate=1.0)

    try:
        raise ValueError("Test error")
    except ValueError:
        logger.exception("An error occurred", extra={"context": "test"})

    captured = capsys.readouterr()
    log_output = json.loads(captured.out.strip())

    # Check exception details are included
    assert "exception" in log_output
    assert log_output["exception"]["type"] == "ValueError"
    assert log_output["exception"]["message"] == "Test error"
    assert "stacktrace" in log_output["exception"]
    assert log_output["context"] == "test"
    assert log_output["severity"] == "ERROR"


def test_gcloud_logger_source_location(monkeypatch, capsys):
    """Test that source location is captured in non-production."""

    # Mock env for non-production
    def mock_env(key, default=None):
        env_values = {
            "APP_ENVIRONMENT": "development",
            "LOG_SAMPLE_RATE": "1.0",
        }
        return env_values.get(key, default)

    with patch("app.services.logging.gcloud.env", side_effect=mock_env):
        from app.services.logging.gcloud import GCloudLogger

        logger = GCloudLogger("test-service", sample_rate=1.0)
        logger.info("Test")

        captured = capsys.readouterr()
        log_output = json.loads(captured.out.strip())

        # Source location should be included in dev environment
        assert "logging.googleapis.com/sourceLocation" in log_output
        source_loc = log_output["logging.googleapis.com/sourceLocation"]
        assert "file" in source_loc
        assert "line" in source_loc
        assert "function" in source_loc


def test_gcloud_logger_all_severity_levels(monkeypatch, capsys):
    """Test all logging methods work with correct severity."""
    from app.services.logging.gcloud import GCloudLogger

    logger = GCloudLogger("test-service", sample_rate=1.0)

    # Test DEBUG
    logger.debug("Debug message")
    captured = capsys.readouterr()
    log_output = json.loads(captured.out.strip())
    assert log_output["severity"] == "DEBUG"

    # Test INFO
    logger.info("Info message")
    captured = capsys.readouterr()
    log_output = json.loads(captured.out.strip())
    assert log_output["severity"] == "INFO"

    # Test WARNING
    logger.warning("Warning message")
    captured = capsys.readouterr()
    log_output = json.loads(captured.out.strip())
    assert log_output["severity"] == "WARNING"

    # Test ERROR
    logger.error("Error message")
    captured = capsys.readouterr()
    log_output = json.loads(captured.out.strip())
    assert log_output["severity"] == "ERROR"

    # Test CRITICAL
    logger.critical("Critical message")
    captured = capsys.readouterr()
    log_output = json.loads(captured.out.strip())
    assert log_output["severity"] == "CRITICAL"


def test_gcloud_logger_json_stdout(monkeypatch, capsys):
    """Test that logger outputs valid JSON to stdout."""
    from app.services.logging.gcloud import GCloudLogger

    logger = GCloudLogger("test-service", sample_rate=1.0)
    logger.info("Test message", extra={"user": "123"})

    captured = capsys.readouterr()

    # Should be valid JSON
    log_output = json.loads(captured.out.strip())
    assert log_output["message"] == "Test message"
    assert log_output["user"] == "123"
    assert log_output["severity"] == "INFO"
    assert log_output["service"] == "test-service"
