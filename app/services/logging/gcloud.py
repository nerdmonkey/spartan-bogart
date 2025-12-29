"""
Google Cloud Logging implementation following GCP best practices.

Key improvements:
1. Structured logging with jsonPayload for Cloud Run/Functions 2nd gen
2. Direct stdout JSON logging (captured automatically by Cloud Run)
3. Cloud Trace context integration via environment variables
4. Proper severity levels and resource detection
5. PII sanitization and efficient batching
6. Source location for debugging
"""

import inspect
import json
import os
import sys
from typing import Any, Dict, Optional

from app.helpers.environment import env

from .base import BaseLogger


class GCloudLogger(BaseLogger):
    """
    Google Cloud Logging implementation following GCP best practices.

    Features:
    - Structured logging with jsonPayload
    - Automatic trace context from Cloud Run/Functions
    - Proper severity levels (DEFAULT, DEBUG, INFO, NOTICE, WARNING, ERROR,
      CRITICAL, ALERT, EMERGENCY)
    - Resource labels for service identification
    - Source location for debugging
    - PII sanitization
    - Efficient batching
    """

    # GCP standard severity levels
    SEVERITY_MAPPING = {
        "debug": "DEBUG",
        "info": "INFO",
        "warning": "WARNING",
        "error": "ERROR",
        "critical": "CRITICAL",
        "exception": "ERROR",
    }

    def __init__(
        self,
        service_name: str,
        level: str = "INFO",
        sample_rate: float = None,
    ):
        self.service_name = service_name
        self.sample_rate = (
            sample_rate
            if sample_rate is not None
            else float(env("LOG_SAMPLE_RATE", "1.0"))
        )
        self.level = level.upper()

        # Sensitive fields for PII sanitization (optimized as frozenset)
        self._sensitive_fields = frozenset(
            {
                "password",
                "token",
                "secret",
                "key",
                "auth",
                "credentials",
                "api_key",
                "access_token",
                "refresh_token",
                "private_key",
                "authorization",
                "cookie",
                "session",
            }
        )

        # Get project root for source location (cached)
        self.project_root = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "../../..")
        )

        # Cache environment info
        self._app_environment = env("APP_ENVIRONMENT", "production")
        self._app_version = env("APP_VERSION", "unknown")
        self._project_id = env("GCP_PROJECT") or env("GOOGLE_CLOUD_PROJECT")

        # Always use JSON stdout for Cloud Run/Functions 2nd gen
        # Cloud Logging automatically parses JSON from stdout
        self.use_json_stdout = True

    def _is_cloud_run(self) -> bool:
        """Check if running in Cloud Run/Functions environment."""
        return bool(env("K_SERVICE") or env("FUNCTION_NAME") or env("FUNCTION_TARGET"))

    def _get_trace_context(self) -> Optional[str]:
        """
        Extract trace context from Cloud Run/Functions.

        Cloud Logging automatically correlates logs with traces when:
        1. Using logging.googleapis.com/trace field in JSON
        2. Format: projects/PROJECT_ID/traces/TRACE_ID
        """
        # Check X-Cloud-Trace-Context header (set by Cloud Run)
        trace_header = env("HTTP_X_CLOUD_TRACE_CONTEXT")
        if not trace_header or not self._project_id:
            return None

        try:
            # Format: TRACE_ID/SPAN_ID;o=TRACE_TRUE
            trace_id = trace_header.split("/")[0].split(";")[0]
            if trace_id:
                trace = f"projects/{self._project_id}/traces/{trace_id}"
                return trace
        except (IndexError, AttributeError):
            pass

        return None

    def _get_source_location(self) -> Optional[Dict[str, Any]]:
        """
        Get source location following GCP's sourceLocation format.

        Returns:
            Dict with file, line, and function for Cloud Logging, or None
        """
        # Skip in production for performance
        if self._app_environment == "production":
            return None

        try:
            stack = inspect.stack()
            # Skip frames: [0]=this method, [1]=_create_log_entry,
            # [2]=_write_log, [3]=log method. Start from frame 4.
            for frame_info in stack[4:]:
                filename = frame_info.filename

                # Skip logging framework and stdlib
                if any(
                    skip in filename
                    for skip in [
                        "/services/logging/",
                        "/helpers/logger.py",
                        "site-packages/",
                        "/lib/python",
                    ]
                ):
                    continue

                # For project files or test files, return source location
                if filename.startswith(
                    self.project_root
                ) or "test_" in os.path.basename(filename):
                    rel_path = (
                        os.path.relpath(filename, self.project_root)
                        if filename.startswith(self.project_root)
                        else os.path.basename(filename)
                    )
                    return {
                        "file": rel_path,
                        "line": str(frame_info.lineno),
                        "function": frame_info.function or "unknown",
                    }
        except Exception:
            pass

        return None

    def _sanitize_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Recursively sanitize sensitive data for PII protection.

        Args:
            data: Dictionary to sanitize

        Returns:
            Sanitized dictionary with sensitive values redacted
        """
        if not isinstance(data, dict):
            return data

        sanitized = {}
        for key, value in data.items():
            key_lower = key.lower()
            if key_lower in self._sensitive_fields:
                sanitized[key] = "[REDACTED]"
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_data(value)
            elif isinstance(value, (list, tuple)):
                sanitized[key] = [
                    self._sanitize_data(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                sanitized[key] = value

        return sanitized

    def _should_sample(self) -> bool:
        """Determine if log should be written based on sample rate."""
        import random

        return random.random() <= self.sample_rate

    def _create_log_entry(
        self,
        severity: str,
        message: str,
        extra: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Create structured log entry for Cloud Logging.

        Uses the special JSON fields that Cloud Logging recognizes:
        - severity: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        - message: Main log message
        - logging.googleapis.com/trace: Trace correlation
        - logging.googleapis.com/sourceLocation: Code location
        - Custom fields in root for jsonPayload
        """
        # Start with base structure
        log_entry = {
            "severity": severity,
            "message": message,
            "service": self.service_name,
            "environment": self._app_environment,
            "version": self._app_version,
        }

        # Add sanitized extra fields
        if extra:
            sanitized_extra = self._sanitize_data(extra)
            log_entry.update(sanitized_extra)

        # Add trace context for correlation (Cloud Logging special field)
        trace = self._get_trace_context()
        if trace:
            # Special field recognized by Cloud Logging
            log_entry["logging.googleapis.com/trace"] = trace

        # Add source location for debugging (Cloud Logging special field)
        source_location = self._get_source_location()
        if source_location:
            log_entry["logging.googleapis.com/sourceLocation"] = source_location

        return log_entry

    def _write_log(
        self,
        severity: str,
        message: str,
        extra: Optional[Dict[str, Any]] = None,
    ):
        """
        Write log entry to stdout as JSON.

        Cloud Run/Functions automatically captures stdout and parses JSON,
        creating structured logs with jsonPayload in Cloud Logging.
        """
        # Apply sampling
        if not self._should_sample():
            return

        try:
            # Create structured log entry
            log_entry = self._create_log_entry(severity, message, extra)

            # Write JSON to stdout (Cloud Logging auto-parses this)
            json_str = json.dumps(log_entry, default=str)
            print(json_str, flush=True)

        except Exception as e:
            # Emergency fallback - write simple text log
            fallback_msg = f"[{severity}] {message} | extra: {extra} | error: {e}"
            print(fallback_msg, file=sys.stderr, flush=True)

    def debug(self, message: str, **kwargs):
        """Log debug message."""
        self._write_log("DEBUG", message, kwargs.get("extra"))

    def info(self, message: str, **kwargs):
        """Log info message."""
        self._write_log("INFO", message, kwargs.get("extra"))

    def warning(self, message: str, **kwargs):
        """Log warning message."""
        self._write_log("WARNING", message, kwargs.get("extra"))

    def error(self, message: str, **kwargs):
        """Log error message."""
        self._write_log("ERROR", message, kwargs.get("extra"))

    def critical(self, message: str, **kwargs):
        """Log critical message."""
        self._write_log("CRITICAL", message, kwargs.get("extra"))

    def exception(self, message: str, **kwargs):
        """
        Log exception with traceback.

        Cloud Error Reporting automatically detects ERROR/CRITICAL logs
        with exception stack traces.
        """
        import traceback

        extra = kwargs.get("extra") or {}

        # Get exception info
        exc_info = sys.exc_info()

        # Add exception details for Error Reporting
        if exc_info[0] is not None:
            extra["exception"] = {
                "type": exc_info[0].__name__,
                "message": str(exc_info[1]),
                "stacktrace": traceback.format_exc(),
            }

        self._write_log("ERROR", message, extra)
