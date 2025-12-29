# Secret Manager Response Models
# This file will contain all Pydantic response models for the Secret Manager service

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict


class SecretResponse(BaseModel):
    """Response model for secret retrieval operations."""

    secret_name: str
    secret_value: str
    version: str
    created_time: datetime
    state: str

    model_config = ConfigDict()


class SecretCreateResponse(BaseModel):
    """Response model for secret creation operations."""

    secret_name: str
    version: str
    created_time: datetime
    replication_policy: str

    model_config = ConfigDict()


class SecretMetadataResponse(BaseModel):
    """Response model for secret metadata without the actual value."""

    secret_name: str
    created_time: datetime
    labels: Optional[Dict[str, str]] = None
    replication_policy: str
    version_count: int

    model_config = ConfigDict()


class SecretListResponse(BaseModel):
    """Response model for listing secrets."""

    secrets: List[SecretMetadataResponse]
    next_page_token: Optional[str] = None
    total_size: Optional[int] = None


class SecretVersionResponse(BaseModel):
    """Response model for secret version operations."""

    secret_name: str
    version: str
    created_time: datetime
    state: str

    model_config = ConfigDict()


class SecretVersionListResponse(BaseModel):
    """Response model for listing secret versions."""

    versions: List[SecretVersionResponse]
    next_page_token: Optional[str] = None
    total_size: Optional[int] = None


class SecretOperationResponse(BaseModel):
    """Response model for secret operations that don't return data."""

    success: bool
    message: str
    operation_time: datetime

    model_config = ConfigDict()
