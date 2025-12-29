# Parameter Manager Response Models
# This file contains all Pydantic response models for the Parameter Manager service

from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, ConfigDict, field_serializer


class ParameterResponse(BaseModel):
    """Response model for parameter retrieval operations."""

    parameter_name: str
    data: Union[str, Dict, Any]
    format_type: str
    version: str
    created_time: datetime
    updated_time: datetime
    labels: Optional[Dict[str, str]] = None

    model_config = ConfigDict()

    @field_serializer("created_time", "updated_time")
    def serialize_datetime(self, value: datetime) -> str:
        return value.isoformat()


class ParameterCreateResponse(BaseModel):
    """Response model for parameter creation operations."""

    parameter_name: str
    created_time: datetime
    format_type: str

    model_config = ConfigDict()

    @field_serializer("created_time")
    def serialize_datetime(self, value: datetime) -> str:
        return value.isoformat()


class ParameterUpdateResponse(BaseModel):
    """Response model for parameter update operations."""

    parameter_name: str
    version: str
    updated_time: datetime

    model_config = ConfigDict()

    @field_serializer("updated_time")
    def serialize_datetime(self, value: datetime) -> str:
        return value.isoformat()


class ParameterMetadataResponse(BaseModel):
    """Response model for parameter metadata without the actual data."""

    parameter_name: str
    format_type: str
    created_time: datetime
    updated_time: datetime
    labels: Optional[Dict[str, str]] = None
    version_count: int

    model_config = ConfigDict()

    @field_serializer("created_time", "updated_time")
    def serialize_datetime(self, value: datetime) -> str:
        return value.isoformat()


class ParameterListResponse(BaseModel):
    """Response model for listing parameters."""

    parameters: List[ParameterMetadataResponse]
    next_page_token: Optional[str] = None
    total_size: Optional[int] = None


class ParameterVersionResponse(BaseModel):
    """Response model for parameter version operations."""

    parameter_name: str
    version: str
    data: Union[str, Dict, Any]
    format_type: str
    created_time: datetime

    model_config = ConfigDict()

    @field_serializer("created_time")
    def serialize_datetime(self, value: datetime) -> str:
        return value.isoformat()


class ParameterVersionListResponse(BaseModel):
    """Response model for listing parameter versions."""

    versions: List[ParameterVersionResponse]
    next_page_token: Optional[str] = None
    total_size: Optional[int] = None


class ParameterOperationResponse(BaseModel):
    """Response model for parameter operations that don't return data."""

    success: bool
    message: str
    operation_time: datetime

    model_config = ConfigDict()

    @field_serializer("operation_time")
    def serialize_datetime(self, value: datetime) -> str:
        return value.isoformat()
