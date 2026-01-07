import importlib
from types import SimpleNamespace


def test_tracer_factory_returns_local_when_local_env(monkeypatch):
    monkeypatch.setattr(
        "app.helpers.environment.env",
        lambda k=None, d=None: {"APP_ENVIRONMENT": "local", "APP_NAME": "svc"}.get(
            k, d
        ),
    )
    # Prevent aws_xray_sdk side-effects during import
    import sys

    fake_xray = SimpleNamespace(
        xray_recorder=SimpleNamespace(
            begin_segment=lambda *a, **k: None,
            end_segment=lambda *a, **k: None,
            begin_subsegment=lambda *a, **k: None,
            end_subsegment=lambda *a, **k: None,
            put_annotation=lambda *a, **k: None,
        )
    )
    monkeypatch.setitem(sys.modules, "aws_xray_sdk", SimpleNamespace())
    monkeypatch.setitem(sys.modules, "aws_xray_sdk.core", fake_xray)

    factory = importlib.reload(importlib.import_module("app.services.tracing.factory"))
    tracer = factory.get_tracer("svc")
    assert tracer.__class__.__name__ == "LocalTracer"
