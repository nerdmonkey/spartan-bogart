from functools import lru_cache

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from app.helpers.environment import env
from app.helpers.logger import get_logger


logger = get_logger("dynamodb_helper")


@lru_cache(maxsize=1)
def get_dynamodb_clients():
    """Get cached DynamoDB clients optimized for runtime environment."""
    settings = env()
    is_local = settings.DDB_TYPE == "local"
    is_container = getattr(settings, "APP_RUNTIME", "lambda") == "container"

    # Build configuration based on environment
    if is_local:
        config = Config(
            max_pool_connections=10,
            retries={"max_attempts": 2},
            read_timeout=30,
            connect_timeout=5,
            parameter_validation=False,
        )
        kwargs = {"config": config, "endpoint_url": "http://localhost:8000"}
        env_type = "LOCAL"
    else:
        max_connections = (
            settings.DDB_MAX_POOL_CONNECTIONS
            if is_container
            else min(settings.DDB_MAX_POOL_CONNECTIONS, 10)
        )
        config = Config(
            max_pool_connections=max_connections,
            retries={
                "max_attempts": settings.DDB_MAX_RETRY_ATTEMPTS,
                "mode": "adaptive",
            },
            read_timeout=settings.DDB_READ_TIMEOUT,
            connect_timeout=settings.DDB_CONNECT_TIMEOUT,
            parameter_validation=False,
            region_name=settings.DDB_REGION,
            signature_version="v4",
        )
        kwargs = {"config": config}
        env_type = "CONTAINER" if is_container else "LAMBDA"

    try:
        resource = boto3.resource("dynamodb", **kwargs)
        client = boto3.client("dynamodb", **kwargs)
        table = resource.Table(settings.DDB_TABLE_NAME)

        # Test connection
        try:
            response = client.describe_table(TableName=settings.DDB_TABLE_NAME)
            logger.info(
                f"DynamoDB connected - Status: {response['Table']['TableStatus']}"
            )
        except ClientError as e:
            if e.response["Error"]["Code"] != "ResourceNotFoundException":
                raise
            logger.warning(f"Table '{settings.DDB_TABLE_NAME}' not found")

        logger.info(f"Initialized {env_type} DynamoDB clients")
        return resource, client, table

    except Exception as e:
        logger.error(f"Failed to initialize DynamoDB clients: {e}")
        raise


# Initialize clients lazily for testing compatibility


# Do not initialize DynamoDB clients at import time. Keep lazy initialization
# so tests (and other consumers) can control client creation (and use moto).
# This prevents accidental network calls during test collection.
dynamodb_resource = None
dynamodb_client = None
table = None
table_name = None


def get_clients():
    """Get clients with lazy initialization for testing."""
    global dynamodb_resource, dynamodb_client, table, table_name
    if dynamodb_resource is None:
        dynamodb_resource, dynamodb_client, table = get_dynamodb_clients()
        table_name = env().DDB_TABLE_NAME
    return dynamodb_resource, dynamodb_client, table
