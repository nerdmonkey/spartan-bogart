import inspect
import json
import os
import random

from aws_lambda_powertools import Logger
from aws_lambda_powertools.logging import correlation_paths

from app.helpers.environment import env

from .base import BaseLogger


class CloudWatchLogger(BaseLogger):
    def __init__(
        self, service_name: str, level: str = "INFO", sample_rate: float = None
    ):
        self.sample_rate = sample_rate or float(env("LOG_SAMPLE_RATE", "1.0"))
        # Define sensitive field names for PII sanitization
        self._sensitive_fields = {
            "password",
            "token",
            "secret",
            "key",
            "auth",
            "credentials",
            "api_key",
        }

        # Keep the default location behavior but we'll override it per call
        self.logger = Logger(
            service=service_name,
            level=level,
            correlation_id_path=correlation_paths.API_GATEWAY_REST,
            use_rfc3339=True,
        )
        self.project_root = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "../../..")
        )

        # Override the formatter to use our custom location
        self._setup_custom_formatter()

    def _setup_custom_formatter(self):
        """Setup custom formatter that uses our location detection."""
        for handler in self.logger._logger.handlers:
            if hasattr(handler, "formatter"):
                original_format = handler.formatter.format

                def custom_format(record):
                    # Get original formatted message
                    original_msg = original_format(record)

                    # Parse JSON to modify location and add metadata
                    try:
                        log_data = json.loads(original_msg)
                        # Replace location with our custom caller_location if it exists
                        if hasattr(record, "caller_location"):
                            log_data["location"] = record.caller_location

                        # Add environment metadata
                        log_data["environment"] = env("APP_ENVIRONMENT", "unknown")
                        log_data["version"] = env("APP_VERSION", "unknown")

                        # Sanitize sensitive data in extra field
                        if "extra" in log_data and isinstance(log_data["extra"], dict):
                            for key in list(log_data["extra"].keys()):
                                if key.lower() in self._sensitive_fields:
                                    log_data["extra"][key] = "[REDACTED]"

                        return json.dumps(log_data)
                    except (json.JSONDecodeError, AttributeError):
                        pass

                    return original_msg

                # Monkey patch the formatter
                handler.formatter.format = custom_format

    def _get_caller_location(self):
        """Get the actual caller location, excluding logging-related files."""
        stack = inspect.stack()
        for frame_info in stack:
            filename = frame_info.filename
            # Only consider frames inside the project root and outside the logging-related directories
            normalized_path = filename.replace("\\", "/")
            rel_normalized = normalized_path.replace(
                self.project_root.replace("\\", "/"), ""
            )

            # Skip frames from logging-related files
            is_logging_frame = (
                "/services/logging/" in rel_normalized
                or "/helpers/logger.py" in rel_normalized
                or "/logging/" in rel_normalized
            )

            if filename.startswith(self.project_root) and not is_logging_frame:
                try:
                    rel_path = os.path.relpath(filename, self.project_root)
                    return f"{rel_path}:{frame_info.lineno}"
                except (ValueError, OSError):
                    return f"{os.path.basename(filename)}:{frame_info.lineno}"

        # Fallback
        return "unknown:0"

    def _should_sample_log(self) -> bool:
        """Determine if this log should be sampled based on sample rate."""
        return random.random() <= self.sample_rate

    def info(self, message: str, **kwargs):
        # Apply sampling for high-volume scenarios
        if not self._should_sample_log():
            return

        location = self._get_caller_location()
        # Add location as an attribute to the record for our custom formatter
        self.logger.info(message, extra=kwargs, caller_location=location)

    def error(self, message: str, **kwargs):
        # Apply sampling for high-volume scenarios
        if not self._should_sample_log():
            return

        location = self._get_caller_location()
        self.logger.error(message, extra=kwargs, caller_location=location)

    def warning(self, message: str, **kwargs):
        # Apply sampling for high-volume scenarios
        if not self._should_sample_log():
            return

        location = self._get_caller_location()
        self.logger.warning(message, extra=kwargs, caller_location=location)

    def debug(self, message: str, **kwargs):
        # Apply sampling for high-volume scenarios
        if not self._should_sample_log():
            return

        location = self._get_caller_location()
        self.logger.debug(message, extra=kwargs, caller_location=location)

    def exception(self, message: str, **kwargs):
        # Apply sampling for high-volume scenarios
        if not self._should_sample_log():
            return

        location = self._get_caller_location()
        self.logger.exception(message, extra=kwargs, caller_location=location)

    def critical(self, message: str, **kwargs):
        # Apply sampling for high-volume scenarios
        if not self._should_sample_log():
            return

        location = self._get_caller_location()
        self.logger.critical(message, extra=kwargs, caller_location=location)

    def inject_lambda_context(self, *args, **kwargs):
        """Decorator to inject lambda context"""
        return self.logger.inject_lambda_context(*args, **kwargs)
