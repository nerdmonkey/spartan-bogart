from typing import Dict, List, Optional, Type

from app.helpers.environment import env
from app.services.logging.both import BothLogger
from app.services.logging.cloud import CloudWatchLogger
from app.services.logging.file import FileLogger
from app.services.logging.stream import StreamLogger

from .base import BaseLogger


class LoggerFactory:
    """Factory class for creating different types of loggers with lazy
    loading support."""

    # Cache for lazy-loaded logger classes
    _lazy_logger_cache: Dict[str, Type[BaseLogger]] = {}

    # Registry of available logger types
    _logger_registry = {
        "stream": StreamLogger,
        "file": FileLogger,
        "cloud": CloudWatchLogger,
        "both": BothLogger,
    }

    @classmethod
    def _resolve_logger_type(cls, logger_type: Optional[str]) -> str:
        """Resolve the logger type from parameters or environment variables."""
        return (logger_type or env("LOGGER_TYPE", env("LOG_CHANNEL", "file"))).lower()

    @classmethod
    def _get_logger_params(
        cls, service_name: str, level: str, logger_type: str
    ) -> Dict:
        """Get common parameters for logger initialization."""
        base_params = {"service_name": service_name, "level": level}

        # Add sample_rate for loggers that support it
        if logger_type in ["file", "cloud", "both"]:
            base_params["sample_rate"] = float(env("LOG_SAMPLE_RATE", "1.0"))

        return base_params

    @classmethod
    def get_supported_types(cls) -> List[str]:
        """Get list of all supported logger types."""
        return list(cls._logger_registry.keys())

    @classmethod
    def create_logger(
        cls,
        service_name: str,
        level: str = "INFO",
        logger_type: Optional[str] = None,
    ) -> BaseLogger:
        """
        Create a logger instance based on the specified type.

        Args:
            service_name: Name of the service for logging identification
            level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            logger_type: Type of logger to create (stream, file, cloud, both)

        Returns:
            BaseLogger: Configured logger instance

        Raises:
            ValueError: If logger_type is not supported
            ImportError: If required dependencies for the logger type are not available
        """
        resolved_type = cls._resolve_logger_type(logger_type)
        params = cls._get_logger_params(service_name, level, resolved_type)

        # Handle logger types
        if resolved_type in cls._logger_registry:
            logger_class = cls._logger_registry[resolved_type]
            return logger_class(**params)

        # Unknown logger type
        else:
            supported_types = ", ".join([f"'{t}'" for t in cls.get_supported_types()])
            raise ValueError(
                f"Unknown logger_type: '{resolved_type}'. "
                f"Must be one of: {supported_types}."
            )
