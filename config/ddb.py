from app.helpers.environment import env


class DDBSettings:
    ddb_type: str = env("DDB_TYPE", "local")
    ddb_table_name: str = env("DDB_TABLE_NAME", "SpartanDDBTable")
    ddb_max_pool_connections: int = env("DDB_MAX_POOL_CONNECTIONS", 50)
    ddb_max_retry_attempts: int = env("DDB_MAX_RETRY_ATTEMPTS", 3)
    ddb_read_timeout: int = env("DDB_READ_TIMEOUT", 60)
    ddb_connect_timeout: int = env("DDB_CONNECT_TIMEOUT", 10)
    ddb_region: str = env("DDB_REGION", "ap-southeast-1")
