"""
Unit tests for app/services/tracing/gcloud.py GCloudTracer.
Tests initialization, decorators, and context managers with OpenTelemetry.
"""

import pytest

from app.services.tracing.gcloud import GCloudTracer


def test_gcloud_tracer_import_error_when_unavailable(mocker):
    """Test GCloudTracer raises ImportError when OpenTelemetry not available."""
    mocker.patch("app.services.tracing.gcloud.GCP_TRACING_AVAILABLE", False)

    with pytest.raises(ImportError) as exc_info:
        GCloudTracer("test-service")

    assert "OpenTelemetry dependencies not available" in str(exc_info.value)


def test_gcloud_tracer_initialization(mocker):
    """Test GCloudTracer initializes with service name and OpenTelemetry tracer."""
    mocker.patch("app.services.tracing.gcloud.GCP_TRACING_AVAILABLE", True)
    mock_exporter = mocker.Mock()
    mock_provider = mocker.Mock()
    mock_tracer = mocker.Mock()
    mock_trace = mocker.Mock()
    mock_trace.get_tracer = mocker.Mock(return_value=mock_tracer)
    mock_trace.set_tracer_provider = mocker.Mock()

    mocker.patch(
        "app.services.tracing.gcloud.CloudTraceSpanExporter",
        return_value=mock_exporter,
        create=True,
    )
    mocker.patch(
        "app.services.tracing.gcloud.TracerProvider",
        return_value=mock_provider,
        create=True,
    )
    mocker.patch(
        "app.services.tracing.gcloud.ResourceAttributes",
        mocker.Mock(SERVICE_NAME="service.name"),
        create=True,
    )
    mocker.patch("app.services.tracing.gcloud.Resource", mocker.Mock(), create=True)
    mocker.patch(
        "app.services.tracing.gcloud.BatchSpanProcessor", mocker.Mock(), create=True
    )
    mocker.patch("app.services.tracing.gcloud.trace", mock_trace, create=True)

    tracer = GCloudTracer("my-service")

    assert tracer.service_name == "my-service"
    assert tracer.tracer is mock_tracer


def test_gcloud_tracer_initialization_with_project_id(mocker):
    """Test GCloudTracer initializes with project_id."""
    mocker.patch("app.services.tracing.gcloud.GCP_TRACING_AVAILABLE", True)
    mock_exporter = mocker.Mock()
    mock_provider = mocker.Mock()
    mock_tracer = mocker.Mock()
    mock_trace = mocker.Mock()
    mock_trace.get_tracer = mocker.Mock(return_value=mock_tracer)
    mock_trace.set_tracer_provider = mocker.Mock()

    mocker.patch(
        "app.services.tracing.gcloud.CloudTraceSpanExporter",
        return_value=mock_exporter,
        create=True,
    )
    mocker.patch(
        "app.services.tracing.gcloud.TracerProvider",
        return_value=mock_provider,
        create=True,
    )
    mocker.patch(
        "app.services.tracing.gcloud.ResourceAttributes",
        mocker.Mock(SERVICE_NAME="service.name"),
        create=True,
    )
    mocker.patch("app.services.tracing.gcloud.Resource", mocker.Mock(), create=True)
    mocker.patch(
        "app.services.tracing.gcloud.BatchSpanProcessor", mocker.Mock(), create=True
    )
    mocker.patch("app.services.tracing.gcloud.trace", mock_trace, create=True)

    tracer = GCloudTracer("my-service", project_id="my-project")

    assert tracer.service_name == "my-service"
    assert tracer.project_id == "my-project"


def test_gcloud_tracer_capture_lambda_handler(mocker):
    """Test capture_lambda_handler decorator wraps function and creates span."""
    mocker.patch("app.services.tracing.gcloud.GCP_TRACING_AVAILABLE", True)
    mock_span = mocker.Mock()
    mock_span.__enter__ = mocker.Mock(return_value=mock_span)
    mock_span.__exit__ = mocker.Mock(return_value=None)

    mock_tracer = mocker.Mock()
    mock_tracer.start_as_current_span = mocker.Mock(return_value=mock_span)

    mock_trace = mocker.Mock()
    mock_trace.get_tracer = mocker.Mock(return_value=mock_tracer)
    mock_trace.set_tracer_provider = mocker.Mock()
    mock_trace.SpanKind = mocker.Mock()

    mock_provider = mocker.Mock()
    mocker.patch("app.services.tracing.gcloud.CloudTraceSpanExporter", create=True)
    mocker.patch(
        "app.services.tracing.gcloud.TracerProvider",
        return_value=mock_provider,
        create=True,
    )
    mocker.patch(
        "app.services.tracing.gcloud.ResourceAttributes",
        mocker.Mock(SERVICE_NAME="service.name"),
        create=True,
    )
    mocker.patch("app.services.tracing.gcloud.Resource", mocker.Mock(), create=True)
    mocker.patch(
        "app.services.tracing.gcloud.BatchSpanProcessor", mocker.Mock(), create=True
    )
    mocker.patch("app.services.tracing.gcloud.trace", mock_trace, create=True)
    mocker.patch("app.services.tracing.gcloud.Status", mocker.Mock(), create=True)
    mocker.patch(
        "app.services.tracing.gcloud.StatusCode",
        mocker.Mock(OK=mocker.Mock(), ERROR=mocker.Mock()),
        create=True,
    )

    tracer = GCloudTracer("test-service")
    tracer.tracer = mock_tracer

    @tracer.capture_lambda_handler
    def handler(event, context):
        return {"statusCode": 200, "body": "ok"}

    result = handler({"key": "value"}, type("Context", (), {"request_id": "123"})())

    assert result == {"statusCode": 200, "body": "ok"}
    mock_tracer.start_as_current_span.assert_called_once()


def test_gcloud_tracer_capture_lambda_handler_with_exception(mocker):
    """Test capture_lambda_handler records exceptions on span."""
    mocker.patch("app.services.tracing.gcloud.GCP_TRACING_AVAILABLE", True)
    mock_span = mocker.Mock()
    mock_span.__enter__ = mocker.Mock(return_value=mock_span)
    mock_span.__exit__ = mocker.Mock(return_value=None)

    mock_tracer = mocker.Mock()
    mock_tracer.start_as_current_span = mocker.Mock(return_value=mock_span)

    mock_trace = mocker.Mock()
    mock_trace.get_tracer = mocker.Mock(return_value=mock_tracer)
    mock_trace.set_tracer_provider = mocker.Mock()
    mock_trace.SpanKind = mocker.Mock()

    mock_provider = mocker.Mock()
    mocker.patch("app.services.tracing.gcloud.CloudTraceSpanExporter", create=True)
    mocker.patch(
        "app.services.tracing.gcloud.TracerProvider",
        return_value=mock_provider,
        create=True,
    )
    mocker.patch(
        "app.services.tracing.gcloud.ResourceAttributes",
        mocker.Mock(SERVICE_NAME="service.name"),
        create=True,
    )
    mocker.patch("app.services.tracing.gcloud.Resource", mocker.Mock(), create=True)
    mocker.patch(
        "app.services.tracing.gcloud.BatchSpanProcessor", mocker.Mock(), create=True
    )
    mocker.patch("app.services.tracing.gcloud.trace", mock_trace, create=True)
    mocker.patch("app.services.tracing.gcloud.Status", mocker.Mock(), create=True)
    mocker.patch(
        "app.services.tracing.gcloud.StatusCode",
        mocker.Mock(OK=mocker.Mock(), ERROR=mocker.Mock()),
        create=True,
    )
    mocker.patch("app.services.tracing.gcloud.Status", create=True)
    mocker.patch("app.services.tracing.gcloud.StatusCode", create=True)

    tracer = GCloudTracer("test-service")
    tracer.tracer = mock_tracer

    @tracer.capture_lambda_handler
    def handler(event, context):
        raise ValueError("Handler error")

    with pytest.raises(ValueError) as exc_info:
        handler({"key": "value"}, type("Context", (), {})())

    assert str(exc_info.value) == "Handler error"
    mock_span.record_exception.assert_called_once()
    mock_span.set_status.assert_called()


def test_gcloud_tracer_capture_method(mocker):
    """Test capture_method decorator wraps instance methods."""
    mocker.patch("app.services.tracing.gcloud.GCP_TRACING_AVAILABLE", True)
    mock_span = mocker.Mock()
    mock_span.__enter__ = mocker.Mock(return_value=mock_span)
    mock_span.__exit__ = mocker.Mock(return_value=None)

    mock_tracer = mocker.Mock()
    mock_tracer.start_as_current_span = mocker.Mock(return_value=mock_span)

    mock_trace = mocker.Mock()
    mock_trace.get_tracer = mocker.Mock(return_value=mock_tracer)
    mock_trace.set_tracer_provider = mocker.Mock()

    mock_provider = mocker.Mock()
    mocker.patch("app.services.tracing.gcloud.CloudTraceSpanExporter", create=True)
    mocker.patch(
        "app.services.tracing.gcloud.TracerProvider",
        return_value=mock_provider,
        create=True,
    )
    mocker.patch(
        "app.services.tracing.gcloud.ResourceAttributes",
        mocker.Mock(SERVICE_NAME="service.name"),
        create=True,
    )
    mocker.patch("app.services.tracing.gcloud.Resource", mocker.Mock(), create=True)
    mocker.patch(
        "app.services.tracing.gcloud.BatchSpanProcessor", mocker.Mock(), create=True
    )
    mocker.patch("app.services.tracing.gcloud.trace", mock_trace, create=True)
    mocker.patch("app.services.tracing.gcloud.Status", create=True)
    mocker.patch("app.services.tracing.gcloud.StatusCode", create=True)

    tracer = GCloudTracer("test-service")
    tracer.tracer = mock_tracer

    class MyClass:
        @tracer.capture_method
        def my_method(self, arg1, arg2=None):
            return f"arg1={arg1}, arg2={arg2}"

    instance = MyClass()
    result = instance.my_method("value1", arg2="value2")

    assert result == "arg1=value1, arg2=value2"
    mock_tracer.start_as_current_span.assert_called_once()
    call_args = mock_tracer.start_as_current_span.call_args
    assert "MyClass.my_method" in call_args[0][0]


def test_gcloud_tracer_capture_method_with_exception(mocker):
    """Test capture_method records exceptions on span."""
    mocker.patch("app.services.tracing.gcloud.GCP_TRACING_AVAILABLE", True)
    mock_span = mocker.Mock()
    mock_span.__enter__ = mocker.Mock(return_value=mock_span)
    mock_span.__exit__ = mocker.Mock(return_value=None)

    mock_tracer = mocker.Mock()
    mock_tracer.start_as_current_span = mocker.Mock(return_value=mock_span)

    mock_trace = mocker.Mock()
    mock_trace.get_tracer = mocker.Mock(return_value=mock_tracer)
    mock_trace.set_tracer_provider = mocker.Mock()

    mock_provider = mocker.Mock()
    mocker.patch("app.services.tracing.gcloud.CloudTraceSpanExporter", create=True)
    mocker.patch(
        "app.services.tracing.gcloud.TracerProvider",
        return_value=mock_provider,
        create=True,
    )
    mocker.patch(
        "app.services.tracing.gcloud.ResourceAttributes",
        mocker.Mock(SERVICE_NAME="service.name"),
        create=True,
    )
    mocker.patch("app.services.tracing.gcloud.Resource", mocker.Mock(), create=True)
    mocker.patch(
        "app.services.tracing.gcloud.BatchSpanProcessor", mocker.Mock(), create=True
    )
    mocker.patch("app.services.tracing.gcloud.trace", mock_trace, create=True)
    mocker.patch("app.services.tracing.gcloud.Status", create=True)
    mocker.patch("app.services.tracing.gcloud.StatusCode", create=True)

    tracer = GCloudTracer("test-service")
    tracer.tracer = mock_tracer

    class MyClass:
        @tracer.capture_method
        def process(self, data):
            raise RuntimeError("Method error")

    instance = MyClass()

    with pytest.raises(RuntimeError) as exc_info:
        instance.process("test")

    assert str(exc_info.value) == "Method error"
    mock_span.record_exception.assert_called_once()
    mock_span.set_status.assert_called()


def test_gcloud_tracer_create_segment(mocker):
    """Test create_segment context manager creates span with metadata."""
    mocker.patch("app.services.tracing.gcloud.GCP_TRACING_AVAILABLE", True)
    mock_span = mocker.Mock()
    mock_span.__enter__ = mocker.Mock(return_value=mock_span)
    mock_span.__exit__ = mocker.Mock(return_value=None)

    mock_tracer = mocker.Mock()
    mock_tracer.start_as_current_span = mocker.Mock(return_value=mock_span)

    mock_trace = mocker.Mock()
    mock_trace.get_tracer = mocker.Mock(return_value=mock_tracer)
    mock_trace.set_tracer_provider = mocker.Mock()

    mock_provider = mocker.Mock()
    mocker.patch("app.services.tracing.gcloud.CloudTraceSpanExporter", create=True)
    mocker.patch(
        "app.services.tracing.gcloud.TracerProvider",
        return_value=mock_provider,
        create=True,
    )
    mocker.patch(
        "app.services.tracing.gcloud.ResourceAttributes",
        mocker.Mock(SERVICE_NAME="service.name"),
        create=True,
    )
    mocker.patch("app.services.tracing.gcloud.Resource", mocker.Mock(), create=True)
    mocker.patch(
        "app.services.tracing.gcloud.BatchSpanProcessor", mocker.Mock(), create=True
    )
    mocker.patch("app.services.tracing.gcloud.trace", mock_trace, create=True)
    mocker.patch("app.services.tracing.gcloud.Status", create=True)
    mocker.patch("app.services.tracing.gcloud.StatusCode", create=True)

    tracer = GCloudTracer("test-service")
    tracer.tracer = mock_tracer

    executed = False
    with tracer.create_segment("test-segment", metadata={"key": "value", "count": 42}):
        executed = True

    assert executed
    mock_tracer.start_as_current_span.assert_called_once_with("test-segment")
    assert mock_span.set_attribute.call_count >= 2


def test_gcloud_tracer_create_segment_exception_handling(mocker):
    """Test create_segment records exceptions on span."""
    mocker.patch("app.services.tracing.gcloud.GCP_TRACING_AVAILABLE", True)
    mock_span = mocker.Mock()
    mock_span.__enter__ = mocker.Mock(return_value=mock_span)
    mock_span.__exit__ = mocker.Mock(return_value=None)

    mock_tracer = mocker.Mock()
    mock_tracer.start_as_current_span = mocker.Mock(return_value=mock_span)

    mock_trace = mocker.Mock()
    mock_trace.get_tracer = mocker.Mock(return_value=mock_tracer)
    mock_trace.set_tracer_provider = mocker.Mock()

    mock_provider = mocker.Mock()
    mocker.patch("app.services.tracing.gcloud.CloudTraceSpanExporter", create=True)
    mocker.patch(
        "app.services.tracing.gcloud.TracerProvider",
        return_value=mock_provider,
        create=True,
    )
    mocker.patch(
        "app.services.tracing.gcloud.ResourceAttributes",
        mocker.Mock(SERVICE_NAME="service.name"),
        create=True,
    )
    mocker.patch("app.services.tracing.gcloud.Resource", mocker.Mock(), create=True)
    mocker.patch(
        "app.services.tracing.gcloud.BatchSpanProcessor", mocker.Mock(), create=True
    )
    mocker.patch("app.services.tracing.gcloud.trace", mock_trace, create=True)
    mocker.patch("app.services.tracing.gcloud.Status", create=True)
    mocker.patch("app.services.tracing.gcloud.StatusCode", create=True)

    tracer = GCloudTracer("test-service")
    tracer.tracer = mock_tracer

    with pytest.raises(ValueError) as exc_info:
        with tracer.create_segment("error-segment"):
            raise ValueError("User code error")

    assert str(exc_info.value) == "User code error"
    mock_span.record_exception.assert_called_once()
    mock_span.set_status.assert_called()


def test_gcloud_tracer_create_subsegment(mocker):
    """Test create_subsegment context manager creates child span."""
    mocker.patch("app.services.tracing.gcloud.GCP_TRACING_AVAILABLE", True)
    mock_span = mocker.Mock()
    mock_span.__enter__ = mocker.Mock(return_value=mock_span)
    mock_span.__exit__ = mocker.Mock(return_value=None)

    mock_tracer = mocker.Mock()
    mock_tracer.start_as_current_span = mocker.Mock(return_value=mock_span)

    mock_trace = mocker.Mock()
    mock_trace.get_tracer = mocker.Mock(return_value=mock_tracer)
    mock_trace.set_tracer_provider = mocker.Mock()

    mock_provider = mocker.Mock()
    mocker.patch("app.services.tracing.gcloud.CloudTraceSpanExporter", create=True)
    mocker.patch(
        "app.services.tracing.gcloud.TracerProvider",
        return_value=mock_provider,
        create=True,
    )
    mocker.patch(
        "app.services.tracing.gcloud.ResourceAttributes",
        mocker.Mock(SERVICE_NAME="service.name"),
        create=True,
    )
    mocker.patch("app.services.tracing.gcloud.Resource", mocker.Mock(), create=True)
    mocker.patch(
        "app.services.tracing.gcloud.BatchSpanProcessor", mocker.Mock(), create=True
    )
    mocker.patch("app.services.tracing.gcloud.trace", mock_trace, create=True)
    mocker.patch("app.services.tracing.gcloud.Status", create=True)
    mocker.patch("app.services.tracing.gcloud.StatusCode", create=True)

    tracer = GCloudTracer("test-service")
    tracer.tracer = mock_tracer

    executed = False
    with tracer.create_subsegment("sub-segment"):
        executed = True

    assert executed
    mock_tracer.start_as_current_span.assert_called_once_with("sub-segment")


def test_gcloud_tracer_create_subsegment_exception_handling(mocker):
    """Test create_subsegment records exceptions on span."""
    mocker.patch("app.services.tracing.gcloud.GCP_TRACING_AVAILABLE", True)
    mock_span = mocker.Mock()
    mock_span.__enter__ = mocker.Mock(return_value=mock_span)
    mock_span.__exit__ = mocker.Mock(return_value=None)

    mock_tracer = mocker.Mock()
    mock_tracer.start_as_current_span = mocker.Mock(return_value=mock_span)

    mock_trace = mocker.Mock()
    mock_trace.get_tracer = mocker.Mock(return_value=mock_tracer)
    mock_trace.set_tracer_provider = mocker.Mock()

    mock_provider = mocker.Mock()
    mocker.patch("app.services.tracing.gcloud.CloudTraceSpanExporter", create=True)
    mocker.patch(
        "app.services.tracing.gcloud.TracerProvider",
        return_value=mock_provider,
        create=True,
    )
    mocker.patch(
        "app.services.tracing.gcloud.ResourceAttributes",
        mocker.Mock(SERVICE_NAME="service.name"),
        create=True,
    )
    mocker.patch("app.services.tracing.gcloud.Resource", mocker.Mock(), create=True)
    mocker.patch(
        "app.services.tracing.gcloud.BatchSpanProcessor", mocker.Mock(), create=True
    )
    mocker.patch("app.services.tracing.gcloud.trace", mock_trace, create=True)
    mocker.patch("app.services.tracing.gcloud.Status", create=True)
    mocker.patch("app.services.tracing.gcloud.StatusCode", create=True)

    tracer = GCloudTracer("test-service")
    tracer.tracer = mock_tracer

    with pytest.raises(RuntimeError) as exc_info:
        with tracer.create_subsegment("error-subsegment"):
            raise RuntimeError("Subsegment error")

    assert str(exc_info.value) == "Subsegment error"
    mock_span.record_exception.assert_called_once()
    mock_span.set_status.assert_called()


def test_gcloud_tracer_handles_exporter_initialization_failure(mocker, capsys):
    """Test GCloudTracer handles Cloud Trace exporter initialization
    failure gracefully."""
    mocker.patch("app.services.tracing.gcloud.GCP_TRACING_AVAILABLE", True)
    mocker.patch(
        "app.services.tracing.gcloud.CloudTraceSpanExporter",
        side_effect=Exception("No credentials"),
        create=True,
    )
    mock_provider = mocker.Mock()
    mock_tracer = mocker.Mock()
    mock_trace = mocker.Mock()
    mock_trace.get_tracer = mocker.Mock(return_value=mock_tracer)
    mock_trace.set_tracer_provider = mocker.Mock()

    mocker.patch(
        "app.services.tracing.gcloud.TracerProvider",
        return_value=mock_provider,
        create=True,
    )
    mocker.patch(
        "app.services.tracing.gcloud.ResourceAttributes",
        mocker.Mock(SERVICE_NAME="service.name"),
        create=True,
    )
    mocker.patch("app.services.tracing.gcloud.Resource", mocker.Mock(), create=True)
    mocker.patch(
        "app.services.tracing.gcloud.BatchSpanProcessor", mocker.Mock(), create=True
    )
    mocker.patch("app.services.tracing.gcloud.trace", mock_trace, create=True)

    tracer = GCloudTracer("test-service")

    captured = capsys.readouterr()
    assert "Warning: Failed to initialize Cloud Trace exporter" in captured.err
    assert tracer.service_name == "test-service"
