from contextlib import contextmanager
from functools import lru_cache, wraps
from typing import Any, Dict, Optional

from app.services.tracing.factory import get_tracer as _get_tracer


class TracerService:
    """Centralized tracer service for the application."""

    @staticmethod
    @lru_cache(maxsize=1)
    def get_tracer():
        """Get cached tracer instance."""
        return _get_tracer()

    @staticmethod
    def trace_function(name: Optional[str] = None):
        """Decorator for tracing functions."""

        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                tracer = TracerService.get_tracer()
                segment_name = name or func.__name__
                with tracer.create_segment(segment_name):
                    return func(*args, **kwargs)

            return wrapper

        return decorator

    @staticmethod
    @contextmanager
    def trace_segment(name: str, metadata: Optional[Dict[str, Any]] = None):
        """Context manager for creating trace segments."""
        tracer = TracerService.get_tracer()
        with tracer.create_segment(name, metadata):
            yield

    @staticmethod
    def capture_lambda_handler(handler):
        """Decorator for tracing Lambda handlers."""
        tracer = TracerService.get_tracer()
        return tracer.capture_lambda_handler(handler)

    @staticmethod
    def capture_method(method):
        """Decorator for tracing class methods."""
        tracer = TracerService.get_tracer()
        return tracer.capture_method(method)


# Helper functions for backward compatibility
def trace_function(name: Optional[str] = None):
    return TracerService.trace_function(name)


def trace_segment(name: str, metadata: Optional[Dict[str, Any]] = None):
    return TracerService.trace_segment(name, metadata)


def capture_lambda_handler(handler):
    return TracerService.capture_lambda_handler(handler)


def capture_method(method):
    return TracerService.capture_method(method)


def get_tracer():
    return TracerService.get_tracer()
