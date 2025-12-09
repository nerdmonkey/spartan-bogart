import sys
import types
from contextlib import contextmanager


# Prevent aws_xray_sdk from creating sockets during import in tests by
# inserting a lightweight fake module into sys.modules before importing
# any tracing modules that may import aws_xray_sdk.core at module load.
fake_core = types.ModuleType("aws_xray_sdk.core")
fake_core.xray_recorder = types.SimpleNamespace()
sys.modules["aws_xray_sdk.core"] = fake_core
sys.modules["aws_xray_sdk"] = types.ModuleType("aws_xray_sdk")
sys.modules["aws_xray_sdk"].core = fake_core

import pytest  # noqa: E402

from app.services.tracing.factory import TracerFactory  # noqa: E402
from app.services.tracing.gcloud import GCloudTracer  # noqa: E402
from app.services.tracing.local import LocalTracer  # noqa: E402


def test_env_override_selects_gcloud(monkeypatch):
    # Ensure env('TRACER_TYPE') returns 'gcloud'
    monkeypatch.setattr(
        "app.services.tracing.factory.env",
        lambda k, d=None: {
            "TRACER_TYPE": "gcloud",
            "APP_ENVIRONMENT": "production",
        }.get(k, d),
    )
    # Patch GCloudTracer to simulate GCP tracing available
    from unittest.mock import MagicMock

    import app.services.tracing.gcloud as gcloud_mod

    monkeypatch.setattr(gcloud_mod, "GCP_TRACING_AVAILABLE", True)
    monkeypatch.setattr(
        gcloud_mod, "CloudTraceSpanExporter", MagicMock(), raising=False
    )
    monkeypatch.setattr(gcloud_mod, "TracerProvider", MagicMock(), raising=False)
    monkeypatch.setattr(gcloud_mod, "BatchSpanProcessor", MagicMock(), raising=False)
    monkeypatch.setattr(gcloud_mod, "ResourceAttributes", MagicMock(), raising=False)
    monkeypatch.setattr(gcloud_mod, "Resource", MagicMock(), raising=False)
    monkeypatch.setattr(gcloud_mod, "trace", MagicMock(), raising=False)

    tracer = TracerFactory.create_tracer(service_name="svc")
    assert isinstance(tracer, GCloudTracer)


def test_param_override_selects_local(monkeypatch):
    # Even if environment indicates cloud, explicit parameter should win
    monkeypatch.setattr(
        "app.services.tracing.factory.env",
        lambda k, d=None: {
            "TRACER_TYPE": "gcloud",
            "APP_ENVIRONMENT": "production",
        }.get(k, d),
    )
    tracer = TracerFactory.create_tracer(service_name="svc", tracer_type="local")
    assert isinstance(tracer, LocalTracer)


def test_invalid_override_raises(monkeypatch):
    monkeypatch.setattr(
        "app.services.tracing.factory.env",
        lambda k, d=None: {"APP_ENVIRONMENT": "production"}.get(k, d),
    )
    with pytest.raises(ValueError):
        TracerFactory.create_tracer(
            service_name="svc", tracer_type="unsupported-tracer"
        )


def test_gcloud_tracer_basic_behaviour(monkeypatch, mocker):
    """
    GCloudTracer should construct with OpenTelemetry and its
    wrappers should call through.
    """
    mod = __import__("app.services.tracing.gcloud", fromlist=["*"])

    # Make OpenTelemetry available
    monkeypatch.setattr(mod, "GCP_TRACING_AVAILABLE", True)

    # Mock OpenTelemetry components
    mock_span = mocker.Mock()
    mock_span.__enter__ = mocker.Mock(return_value=mock_span)
    mock_span.__exit__ = mocker.Mock(return_value=None)

    mock_tracer = mocker.Mock()
    mock_tracer.start_as_current_span = mocker.Mock(return_value=mock_span)

    mock_trace = mocker.Mock()
    mock_trace.get_tracer = mocker.Mock(return_value=mock_tracer)
    mock_trace.set_tracer_provider = mocker.Mock()
    mock_trace.SpanKind = mocker.Mock(SERVER=mocker.Mock())

    monkeypatch.setattr(mod, "CloudTraceSpanExporter", mocker.Mock(), raising=False)
    monkeypatch.setattr(mod, "TracerProvider", mocker.Mock(), raising=False)
    monkeypatch.setattr(mod, "BatchSpanProcessor", mocker.Mock(), raising=False)
    monkeypatch.setattr(mod, "ResourceAttributes", mocker.Mock(), raising=False)
    monkeypatch.setattr(mod, "Resource", mocker.Mock(), raising=False)
    monkeypatch.setattr(mod, "Status", mocker.Mock(), raising=False)
    monkeypatch.setattr(
        mod,
        "StatusCode",
        mocker.Mock(OK=mocker.Mock(), ERROR=mocker.Mock()),
        raising=False,
    )
    monkeypatch.setattr(mod, "trace", mock_trace, raising=False)

    from app.services.tracing.gcloud import GCloudTracer

    gw = GCloudTracer("svc")
    gw.tracer = mock_tracer

    # capture_lambda_handler should return a wrapper that calls the original
    called = {}

    def handler(event, context):
        called["ok"] = True
        return "result"

    wrapped = gw.capture_lambda_handler(handler)
    res = wrapped({}, {})
    assert res == "result"
    assert called.get("ok") is True

    # create_segment should be usable as a context manager
    with gw.create_segment("seg"):
        x = 1
    assert x == 1


def test_tracerservice_delegation(monkeypatch):  # noqa: C901
    """
    TracerService helpers should delegate to the underlying tracer
    instance.
    """
    from app.services.tracer import (
        TracerService,
        capture_lambda_handler,
        capture_method,
        trace_function,
        trace_segment,
    )

    # Create a fake tracer that records calls
    class FakeTracer:
        def __init__(self):
            self.segments = []

        @contextmanager
        def create_segment(self, name, metadata=None):
            self.segments.append(("enter", name, metadata))
            try:
                yield
            finally:
                self.segments.append(("exit", name, metadata))

        def capture_lambda_handler(self, handler):
            def wrapper(event, context):
                return handler(event, context)

            return wrapper

        def capture_method(self, method):
            def wrapper(*args, **kwargs):
                return method(*args, **kwargs)

            return wrapper

    fake = FakeTracer()

    # Monkeypatch TracerService.get_tracer to return our fake tracer
    monkeypatch.setattr(TracerService, "get_tracer", staticmethod(lambda: fake))

    # Test trace_function decorator
    @trace_function(name="myseg")
    def f():
        return 42

    assert f() == 42
    # Should have entered and exited the segment
    assert ("enter", "myseg", None) in fake.segments
    assert ("exit", "myseg", None) in fake.segments

    # Test trace_segment context manager
    with trace_segment("outer", {"a": 1}):
        pass
    assert ("enter", "outer", {"a": 1}) in fake.segments
    assert ("exit", "outer", {"a": 1}) in fake.segments

    # Test capture_lambda_handler and capture_method delegate
    def handler(e, c):
        return "ok"

    deco = capture_lambda_handler(handler)
    # capture_lambda_handler returns a callable that wraps the handler
    assert callable(deco)

    class C:
        def m(self):
            return "m"

    cm = capture_method(C.m)
    assert callable(cm)
