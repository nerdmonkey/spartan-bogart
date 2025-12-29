# Parameter Manager Request Models
# This file contains all Pydantic request models for the Parameter Manager service

import json
from typing import Any, Dict, Optional, Union

import yaml
from pydantic import BaseModel, Field, field_validator


class ParameterCreateRequest(BaseModel):
    """Request model for creating a new parameter."""

    parameter_name: str = Field(..., min_length=1, max_length=255)
    format_type: str = Field(default="UNFORMATTED")
    labels: Optional[Dict[str, str]] = Field(default=None)

    @field_validator("parameter_name")
    @classmethod
    def validate_parameter_name(cls, v):
        if not v or v.isspace():
            raise ValueError("Parameter name cannot be empty or whitespace")
        return v.strip()

    @field_validator("format_type")
    @classmethod
    def validate_format_type(cls, v):
        valid_formats = ["UNFORMATTED", "JSON", "YAML"]
        if v not in valid_formats:
            raise ValueError(f"Format type must be one of {valid_formats}")
        return v


class ParameterVersionCreateRequest(BaseModel):
    """Request model for creating a new parameter version."""

    parameter_name: str = Field(..., min_length=1, max_length=255)
    version_name: str = Field(..., min_length=1, max_length=255)
    data: Union[str, Dict, Any]
    format_type: str = Field(default="UNFORMATTED")

    @field_validator("parameter_name")
    @classmethod
    def validate_parameter_name(cls, v):
        if not v or v.isspace():
            raise ValueError("Parameter name cannot be empty or whitespace")
        return v.strip()

    @field_validator("version_name")
    @classmethod
    def validate_version_name(cls, v):
        if not v or v.isspace():
            raise ValueError("Version name cannot be empty or whitespace")
        return v.strip()

    @field_validator("format_type")
    @classmethod
    def validate_format_type(cls, v):
        valid_formats = ["UNFORMATTED", "JSON", "YAML"]
        if v not in valid_formats:
            raise ValueError(f"Format type must be one of {valid_formats}")
        return v

    @staticmethod
    def _convert_to_string(data: Any) -> str:
        """Convert data to string representation."""
        if isinstance(data, dict):
            return json.dumps(data)
        elif isinstance(data, str):
            return data
        else:
            return str(data)

    @staticmethod
    def _validate_size(data_str: str) -> None:
        """Validate that data size does not exceed 1 MiB."""
        data_bytes = data_str.encode("utf-8")
        if len(data_bytes) > 1_048_576:
            raise ValueError("Parameter data cannot exceed 1 MiB")

    @staticmethod
    def _validate_json_data(data: Any) -> None:
        """Validate JSON format data."""
        if isinstance(data, dict):
            try:
                json.dumps(data)
            except (TypeError, ValueError) as e:
                raise ValueError(f"Invalid JSON data: {e}")
        elif isinstance(data, str):
            try:
                json.loads(data)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON format: {e}")
        else:
            raise ValueError("JSON format requires string or dict data")

    @staticmethod
    def _validate_yaml_data(data: Any) -> None:
        """Validate YAML format data."""
        if isinstance(data, dict):
            try:
                yaml.dump(data)
            except yaml.YAMLError as e:
                raise ValueError(f"Invalid YAML data: {e}")
        elif isinstance(data, str):
            try:
                yaml.safe_load(data)
            except yaml.YAMLError as e:
                raise ValueError(f"Invalid YAML format: {e}")
        else:
            raise ValueError("YAML format requires string or dict data")

    @field_validator("data")
    @classmethod
    def validate_data(cls, v, info):
        # Get format_type from the values dict
        format_type = info.data.get("format_type", "UNFORMATTED")

        # Convert data to string and validate size
        data_str = cls._convert_to_string(v)
        cls._validate_size(data_str)

        # Validate format-specific constraints
        if format_type == "JSON":
            cls._validate_json_data(v)
        elif format_type == "YAML":
            cls._validate_yaml_data(v)

        return v


class ParameterUpdateRequest(BaseModel):
    """Request model for updating a parameter."""

    parameter_name: str = Field(..., min_length=1, max_length=255)
    version_name: str = Field(..., min_length=1, max_length=255)
    data: Union[str, Dict, Any]
    labels: Optional[Dict[str, str]] = Field(default=None)

    @field_validator("parameter_name")
    @classmethod
    def validate_parameter_name(cls, v):
        if not v or v.isspace():
            raise ValueError("Parameter name cannot be empty or whitespace")
        return v.strip()

    @field_validator("version_name")
    @classmethod
    def validate_version_name(cls, v):
        if not v or v.isspace():
            raise ValueError("Version name cannot be empty or whitespace")
        return v.strip()

    @field_validator("data")
    @classmethod
    def validate_data(cls, v):
        # Convert data to string for size validation
        if isinstance(v, dict):
            data_str = json.dumps(v)
        elif isinstance(v, str):
            data_str = v
        else:
            data_str = str(v)

        # Validate size (1 MiB = 1,048,576 bytes)
        data_bytes = data_str.encode("utf-8")
        if len(data_bytes) > 1_048_576:
            raise ValueError("Parameter data cannot exceed 1 MiB")

        return v


class ParameterAccessRequest(BaseModel):
    """Request model for accessing a parameter."""

    parameter_name: str = Field(..., min_length=1, max_length=255)
    version: Optional[str] = Field(default=None)

    @field_validator("parameter_name")
    @classmethod
    def validate_parameter_name(cls, v):
        if not v or v.isspace():
            raise ValueError("Parameter name cannot be empty or whitespace")
        return v.strip()


class ParameterListRequest(BaseModel):
    """Request model for listing parameters."""

    page_size: int = Field(default=100, ge=1, le=1000)
    page_token: Optional[str] = Field(default=None)
    filter_expression: Optional[str] = Field(default=None)

    @field_validator("page_size")
    @classmethod
    def validate_page_size(cls, v):
        if v < 1 or v > 1000:
            raise ValueError("Page size must be between 1 and 1000")
        return v


class ParameterVersionListRequest(BaseModel):
    """Request model for listing parameter versions."""

    parameter_name: str = Field(..., min_length=1, max_length=255)
    page_size: int = Field(default=100, ge=1, le=1000)
    page_token: Optional[str] = Field(default=None)

    @field_validator("parameter_name")
    @classmethod
    def validate_parameter_name(cls, v):
        if not v or v.isspace():
            raise ValueError("Parameter name cannot be empty or whitespace")
        return v.strip()

    @field_validator("page_size")
    @classmethod
    def validate_page_size(cls, v):
        if v < 1 or v > 1000:
            raise ValueError("Page size must be between 1 and 1000")
        return v
