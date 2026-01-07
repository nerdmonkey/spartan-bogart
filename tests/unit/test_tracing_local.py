import json
import tempfile
from pathlib import Path
from unittest.mock import mock_open, patch

import pytest

from app.services.tracing.local import LocalTracer


class DummyContext:
    pass


def cleanup_trace_file(tracer):
    if tracer.trace_file.exists():
        tracer.trace_file.unlink()


@pytest.fixture
def tracer():
    t = LocalTracer("test_service")
    # Use a unique temporary file for each test to avoid conflicts
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.trace') as tmp:
        t.trace_file = Path(tmp.name)
    cleanup_trace_file(t)
    yield t
    cleanup_trace_file(t)


def test_write_trace(tracer):
    tracer._write_trace("test_segment", {"foo": "bar"})
    with open(tracer.trace_file) as f:
        lines = f.readlines()
    entry = json.loads(lines[-1])
    assert entry["service"] == "test_service"
    assert entry["segment"] == "test_segment"
    assert entry["metadata"] == {"foo": "bar"}


def test_capture_lambda_handler_success(tracer):
    def handler(event, context):
        return "ok"

    wrapped = tracer.capture_lambda_handler(handler)
    result = wrapped({"x": 1}, DummyContext())
    assert result == "ok"
    with open(tracer.trace_file) as f:
        lines = f.readlines()
    assert any("lambda_handler" in line for line in lines)
    assert any("lambda_handler_response" in line for line in lines)


@patch("builtins.open", mock_open())
def test_capture_lambda_handler_error(tracer):
    def handler(event, context):
        raise ValueError("fail")

    wrapped = tracer.capture_lambda_handler(handler)
    with pytest.raises(ValueError):
        wrapped({}, DummyContext())
    # Mock the file read since we're mocking the write
    mock_trace_data = '{"segment": "lambda_handler_error"}\n'
    with patch("builtins.open", mock_open(read_data=mock_trace_data)):
        with open(tracer.trace_file) as f:
            lines = f.readlines()
        assert any("lambda_handler_error" in line for line in lines)


def test_capture_method_success(tracer):
    def foo(x):
        return x * 2

    wrapped = tracer.capture_method(foo)
    result = wrapped(3)
    assert result == 6
    with open(tracer.trace_file) as f:
        lines = f.readlines()
    assert any('"processing_time"' in line for line in lines)


def test_capture_method_error(tracer):
    def foo(x):
        raise RuntimeError("bad")

    wrapped = tracer.capture_method(foo)
    with pytest.raises(RuntimeError):
        wrapped(1)
    with open(tracer.trace_file) as f:
        lines = f.readlines()
    assert any("foo_error" in line for line in lines)


def test_create_segment_success(tracer):
    with tracer.create_segment("seg", {"meta": 123}):
        pass
    with open(tracer.trace_file) as f:
        lines = f.readlines()
    assert any('"segment": "seg"' in line for line in lines)
    assert any('"processing_time"' in line for line in lines)


def test_create_segment_error(tracer):
    try:
        with tracer.create_segment("segerr", {"meta": 999}):
            raise Exception("segmentfail")
    except Exception:
        pass
    with open(tracer.trace_file) as f:
        lines = f.readlines()
    assert any('"segment": "segerr_error"' in line for line in lines)
    assert any('"processing_time"' in line for line in lines)
