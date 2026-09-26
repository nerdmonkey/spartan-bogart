import sys
import types

import pytest


# Prevent aws_xray_sdk from creating real sockets/segments during import.
fake_core = types.ModuleType("aws_xray_sdk.core")


class _FakeRecorder:
    def __init__(self):
        self.calls = []

    def put_annotation(self, key, value):
        self.calls.append(("annotation", key, value))

    def begin_segment(self, name):
        self.calls.append(("begin_segment", name))

    def end_segment(self):
        self.calls.append(("end_segment",))

    def begin_subsegment(self, name):
        self.calls.append(("begin_subsegment", name))

    def end_subsegment(self):
        self.calls.append(("end_subsegment",))


fake_core.xray_recorder = _FakeRecorder()
sys.modules["aws_xray_sdk.core"] = fake_core
sys.modules["aws_xray_sdk"] = types.ModuleType("aws_xray_sdk")
sys.modules["aws_xray_sdk"].core = fake_core


def test_capture_lambda_handler_puts_annotations_and_calls_func():
    from app.services.tracing.cloud import CloudTracer

    tracer = CloudTracer("svc")

    @tracer.capture_lambda_handler
    def handler(event, context):
        return {"event": event, "context": context}

    result = handler({"a": 1}, "ctx")
    assert result == {"event": {"a": 1}, "context": "ctx"}
    assert ("annotation", "service", "svc") in tracer.tracer.calls
    assert ("annotation", "handler", "handler") in tracer.tracer.calls


def test_capture_method_puts_annotations_and_calls_method():
    from app.services.tracing.cloud import CloudTracer

    tracer = CloudTracer("svc")

    class Thing:
        @tracer.capture_method
        def do_work(self, x):
            return x * 2

    t = Thing()
    assert t.do_work(21) == 42
    assert ("annotation", "service", "svc") in tracer.tracer.calls
    assert ("annotation", "method", "do_work") in tracer.tracer.calls


def test_create_segment_begins_and_ends():
    from app.services.tracing.cloud import CloudTracer

    tracer = CloudTracer("svc")
    with tracer.create_segment("seg-a"):
        pass

    assert ("begin_segment", "seg-a") in tracer.tracer.calls
    assert ("end_segment",) in tracer.tracer.calls


def test_create_segment_ends_even_on_exception():
    from app.services.tracing.cloud import CloudTracer

    tracer = CloudTracer("svc")
    with pytest.raises(ValueError):
        with tracer.create_segment("seg-b"):
            raise ValueError("boom")

    assert ("end_segment",) in tracer.tracer.calls


def test_create_subsegment_begins_and_ends():
    from app.services.tracing.cloud import CloudTracer

    tracer = CloudTracer("svc")
    with tracer.create_subsegment("sub-a"):
        pass

    assert ("begin_subsegment", "sub-a") in tracer.tracer.calls
    assert ("end_subsegment",) in tracer.tracer.calls


def test_base_tracer_abstract_methods_are_callable_via_subclass():
    from app.services.tracing.base import BaseTracer

    class ConcreteTracer(BaseTracer):
        def capture_lambda_handler(self, handler):
            return super().capture_lambda_handler(handler)

        def capture_method(self, method):
            return super().capture_method(method)

        def create_segment(self, name, metadata=None):
            return super().create_segment(name, metadata)

    tracer = ConcreteTracer()
    assert tracer.capture_lambda_handler(lambda: None) is None
    assert tracer.capture_method(lambda: None) is None
    # The abstract body is a bare `pass` (not a real generator), so calling
    # it executes the body immediately without needing to enter the CM.
    tracer.create_segment("n")


def test_tracer_factory_selects_cloud_when_environment_not_local(monkeypatch):
    from app.services.tracing.cloud import CloudTracer
    from app.services.tracing.factory import TracerFactory

    monkeypatch.setattr(
        "app.services.tracing.factory.env",
        lambda k, d=None: {"APP_ENVIRONMENT": "prod"}.get(k, d),
    )
    tracer = TracerFactory.create_tracer(service_name="svc")
    assert isinstance(tracer, CloudTracer)


def test_tracer_factory_explicit_cloud_override(monkeypatch):
    from app.services.tracing.cloud import CloudTracer
    from app.services.tracing.factory import TracerFactory

    monkeypatch.setattr(
        "app.services.tracing.factory.env",
        lambda k, d=None: {"APP_ENVIRONMENT": "local"}.get(k, d),
    )
    tracer = TracerFactory.create_tracer(service_name="svc", tracer_type="aws")
    assert isinstance(tracer, CloudTracer)


def test_validate_service_name_raises_on_blank():
    from app.services.tracing.factory import validate_service_name

    with pytest.raises(ValueError):
        validate_service_name("   ")
    with pytest.raises(ValueError):
        validate_service_name(None)
