# Secret Manager Request Models
# This file will contain all Pydantic request models for the Secret Manager service

from typing import Dict, Optional

from pydantic import BaseModel, Field, field_validator


class SecretCreateRequest(BaseModel):
    """Request model for creating a new secret."""

    secret_name: str = Field(..., min_length=1, max_length=255)
    secret_value: str = Field(..., min_length=1)
    replication_policy: Optional[str] = Field(default="automatic")
    labels: Optional[Dict[str, str]] = Field(default=None)

    @field_validator("secret_name")
    @classmethod
    def validate_secret_name(cls, v):
        if not v or v.isspace():
            raise ValueError("Secret name cannot be empty or whitespace")
        return v.strip()

    @field_validator("secret_value")
    @classmethod
    def validate_secret_value(cls, v):
        if not v or v.isspace():
            raise ValueError("Secret value cannot be empty or whitespace")
        return v


class SecretVersionCreateRequest(BaseModel):
    """Request model for creating a new secret version."""

    secret_name: str = Field(..., min_length=1, max_length=255)
    secret_value: str = Field(..., min_length=1)

    @field_validator("secret_name")
    @classmethod
    def validate_secret_name(cls, v):
        if not v or v.isspace():
            raise ValueError("Secret name cannot be empty or whitespace")
        return v.strip()

    @field_validator("secret_value")
    @classmethod
    def validate_secret_value(cls, v):
        if not v or v.isspace():
            raise ValueError("Secret value cannot be empty or whitespace")
        return v


class SecretAccessRequest(BaseModel):
    """Request model for accessing a secret."""

    secret_name: str = Field(..., min_length=1, max_length=255)
    version: str = Field(default="latest")

    @field_validator("secret_name")
    @classmethod
    def validate_secret_name(cls, v):
        if not v or v.isspace():
            raise ValueError("Secret name cannot be empty or whitespace")
        return v.strip()
