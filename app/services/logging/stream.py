import logging
import sys
from datetime import datetime

from .base import BaseLogger


try:
    from colorama import Fore, Style, init

    init(autoreset=True)
    COLORAMA_AVAILABLE = True
except ImportError:
    COLORAMA_AVAILABLE = False

LEVEL_COLORS = {
    "DEBUG": Fore.CYAN if COLORAMA_AVAILABLE else "",
    "INFO": Fore.GREEN if COLORAMA_AVAILABLE else "",
    "WARNING": Fore.YELLOW if COLORAMA_AVAILABLE else "",
    "ERROR": Fore.RED if COLORAMA_AVAILABLE else "",
    "CRITICAL": Fore.MAGENTA if COLORAMA_AVAILABLE else "",
}
RESET = Style.RESET_ALL if COLORAMA_AVAILABLE else ""


class StreamLogger(BaseLogger):
    def __init__(self, service_name: str, level: str = "INFO"):
        self.service_name = service_name
        self.level = level
        self.logger = logging.getLogger(f"{service_name}-stream")
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            "%(message)s"
        )  # We'll handle formatting ourselves
        handler.setFormatter(formatter)
        self.logger.handlers = []  # Remove any existing handlers
        self.logger.addHandler(handler)
        self.logger.setLevel(getattr(logging, level.upper(), logging.INFO))
        self.logger.propagate = False

    def _format_message(self, level: str, message: str, extra=None):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        color = LEVEL_COLORS.get(level, "")
        reset = RESET
        extra_str = f" | extra: {extra}" if extra else ""
        return (
            f"{color}[{timestamp}] [{level}] {self.service_name}:{reset} "
            f"{message}{extra_str}"
        )

    def log(self, message: str, level: str = None, **kwargs):
        level = (level or self.level).upper()
        extra = kwargs.get("extra")
        formatted = self._format_message(level, message, extra)
        log_method = getattr(self.logger, level.lower(), self.logger.info)
        log_method(formatted)

    def info(self, message: str, **kwargs):
        self.log(message, level="INFO", **kwargs)

    def warning(self, message: str, **kwargs):
        self.log(message, level="WARNING", **kwargs)

    def error(self, message: str, **kwargs):
        self.log(message, level="ERROR", **kwargs)

    def debug(self, message: str, **kwargs):
        self.log(message, level="DEBUG", **kwargs)

    def exception(self, message: str, *args, **kwargs):
        extra = kwargs.get("extra")
        formatted = self._format_message("ERROR", message, extra)
        self.logger.error(formatted, exc_info=True)
