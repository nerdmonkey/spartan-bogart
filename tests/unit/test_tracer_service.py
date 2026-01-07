import sys
import types
from contextlib import contextmanager

import pytest

from app.services.tracing.factory import TracerFactory
from app.services.tracing.local import LocalTracer


# Prevent aws_xray_sdk from creating sockets during import in tests by
# inserting a lightweight fake module into sys.modules before importing
# any tracing modules that may import aws_xray_sdk.core at module load.
fake_core = types.ModuleType("aws_xray_sdk.core")
fake_core.xray_recorder = types.SimpleNamespace()
sys.modules["aws_xray_sdk.core"] = fake_core
sys.modules["aws_xray_sdk"] = types.ModuleType("aws_xray_sdk")
sys.modules["aws_xray_sdk"].core = fake_core


def test_param_override_selects_local(monkeypatch):
    # Even if environment indicates cloud, explicit parameter should win
    monkeypatch.setattr(
        "app.services.tracing.factory.env",
        lambda k, d=None: {"TRACER_TYPE": "cloud", "APP_ENVIRONMENT": "production"}.get(
            k, d
        ),
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


def test_tracerservice_delegation(monkeypatch):
    """TracerService helpers should delegate to the underlying tracer instance."""
    fake_tracer = _create_fake_tracer()
    _patch_tracer_service(monkeypatch, fake_tracer)

    _test_trace_function_decorator(fake_tracer)
    _test_trace_segment_context_manager(fake_tracer)
    _test_capture_decorators()


def _create_fake_tracer():
    """Create a fake tracer that records calls."""

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

    return FakeTracer()


def _patch_tracer_service(monkeypatch, fake_tracer):
    """Patch TracerService to return fake tracer."""
    from app.services.tracer import TracerService

    monkeypatch.setattr(TracerService, "get_tracer", staticmethod(lambda: fake_tracer))


def _test_trace_function_decorator(fake_tracer):
    """Test trace_function decorator."""
    from app.services.tracer import trace_function

    @trace_function(name="myseg")
    def f():
        return 42

    assert f() == 42
    assert ("enter", "myseg", None) in fake_tracer.segments
    assert ("exit", "myseg", None) in fake_tracer.segments


def _test_trace_segment_context_manager(fake_tracer):
    """Test trace_segment context manager."""
    from app.services.tracer import trace_segment

    with trace_segment("outer", {"a": 1}):
        pass
    assert ("enter", "outer", {"a": 1}) in fake_tracer.segments
    assert ("exit", "outer", {"a": 1}) in fake_tracer.segments


def _test_capture_decorators():
    """Test capture decorators return callables."""
    from app.services.tracer import capture_lambda_handler, capture_method

    def handler(e, c):
        return "ok"

    deco = capture_lambda_handler(handler)
    assert callable(deco)

    class C:
        def m(self):
            return "m"

    cm = capture_method(C.m)
    assert callable(cm)
