from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, scoped_session, sessionmaker

from app.helpers.environment import env
from app.helpers.logger import get_logger


logger = get_logger("spartan.database")


def _build_database_url() -> str:
    """Build database URL based on environment configuration."""
    settings = env()
    db_type = settings.DB_TYPE

    if db_type == "sqlite":
        return f"sqlite:///./database/{settings.DB_NAME}.db"

    urls = {
        "psql": "postgresql+pg8000",
        "mysql": "mysql+pymysql",
        "mssql": "mssql+pyodbc",
    }

    if db_type not in urls:
        raise ValueError(f"Unsupported database type: {db_type}")

    base_url = (
        f"{urls[db_type]}://{settings.DB_USERNAME}:"
        f"{settings.DB_PASSWORD}@{settings.DB_HOST}:"
        f"{settings.DB_PORT}/{settings.DB_NAME}"
    )

    if db_type == "mssql":
        return f"{base_url}?driver={settings.DB_DRIVER}"
    return base_url


@lru_cache(maxsize=1)
def get_engine():
    """Get cached database engine with environment-specific configuration."""
    settings = env()
    url = _build_database_url()
    connect_args = {"check_same_thread": False} if settings.DB_TYPE == "sqlite" else {}

    # Container vs Lambda configuration
    is_container = getattr(settings, "APP_RUNTIME", "lambda") == "container"

    engine_kwargs = {
        "url": url,
        "connect_args": connect_args,
    }

    if is_container:
        # Container: Larger connection pool for concurrent requests
        engine_kwargs.update(
            {
                "pool_size": 20,
                "max_overflow": 30,
                "pool_pre_ping": True,
                "pool_recycle": 3600,
            }
        )
        logger.info("Database engine created for CONTAINER environment")
    else:
        # Lambda: Minimal pool for serverless
        engine_kwargs.update(
            {
                "pool_size": 1,
                "max_overflow": 0,
            }
        )
        logger.info("Database engine created for LAMBDA environment")

    return create_engine(**engine_kwargs)


@lru_cache(maxsize=1)
def get_session_factory():
    """Get session factory based on runtime environment."""
    settings = env()
    engine = get_engine()
    is_container = getattr(settings, "APP_RUNTIME", "lambda") == "container"

    if is_container:
        # Container: Thread-safe scoped sessions
        return scoped_session(sessionmaker(bind=engine))
    else:
        # Lambda: Simple session factory
        return sessionmaker(bind=engine)


def db() -> Session:
    """Get database session optimized for runtime environment."""
    session_factory = get_session_factory()
    return session_factory()


# For backward compatibility
engine = get_engine()
