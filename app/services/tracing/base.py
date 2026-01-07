from abc import ABC, abstractmethod
from contextlib import contextmanager
from typing import Any, Dict, Optional


class BaseTracer(ABC):
    @abstractmethod
    def capture_lambda_handler(self, handler):
        pass

    @abstractmethod
    def capture_method(self, method):
        pass

    @abstractmethod
    @contextmanager
    def create_segment(self, name: str, metadata: Optional[Dict[str, Any]] = None):
        pass
