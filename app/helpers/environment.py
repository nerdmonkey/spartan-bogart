from functools import lru_cache
from typing import Literal, Optional

from dotenv import load_dotenv
from pydantic import ConfigDict, field_validator
from pydantic_settings import BaseSettings


load_dotenv(dotenv_path=".env")


class EnvironmentVariables(BaseSettings):
    """
    EnvironmentVariables is a configuration class for managing application
    environment variables.
    Attributes:
        APP_NAME (str): The name of the application.
        APP_ENVIRONMENT (str): The current environment
            (one of: local, dev, uat, prod, test).
        APP_DEBUG (bool): Flag to enable or disable debug mode.
        APP_MAINTENANCE (bool): Flag to enable or disable maintenance mode.
            Defaults to False.
        ALLOWED_ORIGINS (str): Comma-separated list of allowed CORS origins.
        LOG_LEVEL (str): The logging level (e.g., INFO, DEBUG).
        LOG_CHANNEL (str): The logging channel to use.
        LOG_DIR (str): Directory path for storing log files.
        DB_TYPE (str): The type of database (e.g., postgres, mysql).
        DB_DRIVER (str): The database driver to use.
        DB_HOST (str): The database host address.
        DB_PORT (Optional[int]): The database port.
            Defaults to None if not provided.
        DB_NAME (str): The name of the database.
        DB_USERNAME (str): The database username.
        DB_PASSWORD (str): The database password.
        DB_SSL_CA (Optional[str]): Path to the SSL CA certificate for the
            database. Optional.
        DB_SSL_VERIFY_CERT (Optional[bool]): Whether to verify the database
            SSL certificate. Optional.
        STORAGE_TYPE (str): The storage type to use. Defaults to "local".
        STORAGE_BUCKET (Optional[str]): The storage bucket name. Optional.
        STORAGE_PATH (str): The storage path. Defaults to "storage/core".
    Class Attributes:
        model_config: Configuration for environment file loading.
    Methods:
        default_db_port(cls, v): Validator to ensure DB_PORT is an integer or None.
    """

    APP_NAME: str
    APP_ENVIRONMENT: Literal["local", "dev", "uat", "prod", "test"]
    APP_VERSION: Optional[str] = "unknown"
    APP_RUNTIME: Optional[str] = "lambda"
    APP_DEBUG: bool
    ALLOWED_ORIGINS: str
    APP_MAINTENANCE: bool = False

    LOG_LEVEL: str
    LOG_CHANNEL: str
    LOG_DIR: str
    LOG_SAMPLE_RATE: Optional[str] = "1.0"

    DB_TYPE: str
    DB_DRIVER: str
    DB_HOST: str
    DB_PORT: Optional[int] = None
    DB_NAME: str
    DB_USERNAME: str
    DB_PASSWORD: str

    DB_SSL_CA: Optional[str] = None
    DB_SSL_VERIFY_CERT: Optional[bool] = None

    DDB_TYPE: str
    DDB_TABLE_NAME: str
    DDB_MAX_POOL_CONNECTIONS: Optional[int] = 50
    DDB_MAX_RETRY_ATTEMPTS: Optional[int] = 3
    DDB_READ_TIMEOUT: Optional[int] = 60
    DDB_CONNECT_TIMEOUT: Optional[int] = 10
    DDB_REGION: Optional[str] = "ap-southeast-1"

    STORAGE_TYPE: str = "local"
    STORAGE_BUCKET: Optional[str] = None
    STORAGE_PATH: str = "storage/core"

    model_config = ConfigDict(env_file=".env", env_file_encoding="utf-8")

    @field_validator("APP_ENVIRONMENT")
    def validate_app_environment(cls, v):
        """Validate APP_ENVIRONMENT is one of the expected values."""
        valid_environments = ["local", "dev", "uat", "prod", "test"]
        if v not in valid_environments:
            raise ValueError(
                f"APP_ENVIRONMENT must be one of {valid_environments}, got '{v}'"
            )
        return v

    @field_validator("DB_PORT", mode="before")
    def default_db_port(cls, v):
        if v is None or v == "":
            return None
        try:
            return int(v)
        except (TypeError, ValueError):
            return None

    @field_validator("DB_SSL_CA", "STORAGE_BUCKET", mode="before")
    def convert_empty_to_none(cls, v):
        if v == "":
            return None
        return v

    @field_validator("DB_SSL_VERIFY_CERT", mode="before")
    def convert_bool_or_empty_to_none(cls, v):
        # Handle empty string as None first
        if v == "":
            return None
        if v is None:
            return None
        if isinstance(v, str):
            if v.lower() in ("false", "0", "no"):
                return False
            elif v.lower() in ("true", "1", "yes"):
                return True
            else:
                return None
        return bool(v)


@lru_cache()
def env(var_name: Optional[str] = None, default: Optional[str] = None) -> Optional[str]:
    """
    Create and return an instance of EnvironmentVariables or a specific
    environment variable.

    This function initializes and returns an EnvironmentVariables object,
    which is used to manage and access environment variables for the
    application. If a variable name is provided, it returns the value of
    that specific environment variable. If the variable is not found, it
    returns the provided default value.

    Args:
        var_name (Optional[str]): The name of the environment variable to
            retrieve.
        default (Optional[str]): The default value to return if the
            variable is not found. Defaults to None.

    Returns:
        EnvironmentVariables or Optional[str]: An instance of the
        EnvironmentVariables class or the value of the specified
        environment variable, or the default value if not found.
    """
    env_vars = EnvironmentVariables()
    if var_name:
        return getattr(env_vars, var_name, default)
    return env_vars
