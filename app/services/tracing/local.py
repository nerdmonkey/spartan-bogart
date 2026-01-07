import json
from contextlib import contextmanager
from datetime import datetime
from functools import wraps
from pathlib import Path
from time import time
from typing import Any, Dict, Optional

from .base import BaseTracer


class LocalTracer(BaseTracer):
    def __init__(self, service_name: str):
        self.service_name = service_name
        self.trace_file = self._get_trace_file_path()
        self._ensure_trace_directory_exists()

    def _get_trace_file_path(self) -> Path:
        base_path = Path(__file__).parent.parent.parent.parent
        return base_path / "storage" / "traces" / "spartan.trace"

    def _ensure_trace_directory_exists(self):
        self.trace_file.parent.mkdir(parents=True, exist_ok=True)

    def _write_trace(self, segment_name: str, metadata: Optional[Dict] = None):
        trace_entry = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "service": self.service_name,
            "segment": segment_name,
            "metadata": metadata or {},
        }
        trace_message = json.dumps(trace_entry, default=str)

        with open(self.trace_file, "a") as f:
            f.write(trace_message + "\n")
        print(trace_message)

    def capture_lambda_handler(self, handler):
        @wraps(handler)
        def wrapper(event, context):
            start_time = time()
            self._write_trace("lambda_handler", {"event": event})
            try:
                result = handler(event, context)
                end_time = time()
                processing_time = end_time - start_time
                self._write_trace(
                    "lambda_handler_response",
                    {"result": result, "processing_time": processing_time},
                )
                return result
            except Exception as e:
                end_time = time()
                processing_time = end_time - start_time
                self._write_trace(
                    "lambda_handler_error",
                    {"error": str(e), "processing_time": processing_time},
                )
                raise

        return wrapper

    def capture_method(self, method):
        @wraps(method)
        def wrapper(*args, **kwargs):
            start_time = time()
            self._write_trace(method.__name__)
            try:
                result = method(*args, **kwargs)
                end_time = time()
                processing_time = end_time - start_time
                self._write_trace(method.__name__, {"processing_time": processing_time})
                return result
            except Exception as e:
                end_time = time()
                processing_time = end_time - start_time
                self._write_trace(
                    f"{method.__name__}_error",
                    {"error": str(e), "processing_time": processing_time},
                )
                raise

        return wrapper

    @contextmanager
    def create_segment(self, name: str, metadata: Optional[Dict[str, Any]] = None):
        start_time = time()
        self._write_trace(name, metadata)
        try:
            yield
        except Exception as e:
            end_time = time()
            processing_time = end_time - start_time
            self._write_trace(
                f"{name}_error",
                {"error": str(e), "processing_time": processing_time},
            )
            raise
        else:
            end_time = time()
            processing_time = end_time - start_time
            self._write_trace(name, {"processing_time": processing_time})
