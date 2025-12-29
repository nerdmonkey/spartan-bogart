from app.helpers.environment import env


class StorageSettings:
    storage_type: str = env("STORAGE_TYPE", "local")
    storage_bucket: str = env("STORAGE_BUCKET", "spartan-bucket")
    storage_path: str = env("STORAGE_PATH", "storage/core")
