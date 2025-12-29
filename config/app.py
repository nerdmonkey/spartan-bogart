from typing import Any, List

from app.helpers.environment import env

from .database import DatabaseSettings
from .ddb import DDBSettings
from .log import LogSettings


class AppSettings:
    app_name: str = env("APP_NAME", "spartan")
    app_maintenance: bool = env("APP_MAINTENANCE", False)
    app_version: str = env("APP_VERSION", "0.1.0")
    app_environment: str = env("APP_ENVIRONMENT", "test")
    app_debug: bool = env("APP_DEBUG", False)
    app_runtime: str = env("APP_RUNTIME", "lambda")
    allowed_origins: List[str] = [
        o.strip() for o in env("ALLOWED_ORIGINS", "*").split(",")
    ]

    log: LogSettings = LogSettings()
    db: DatabaseSettings = DatabaseSettings()
    ddb: DDBSettings = DDBSettings()

    @property
    def environment(self) -> str:
        return self.app_environment

    @property
    def debug(self) -> bool:
        return self.app_debug

    def __call__(self, dotted_key: str, default: Any = None) -> Any:
        """
        Allow dynamic access via dot-notation:
        e.g. config("log.level") → "DEBUG"
        """
        keys = dotted_key.split(".")
        current = self
        for key in keys:
            if hasattr(current, key):
                current = getattr(current, key)
            else:
                return default
        return current


config = AppSettings()
