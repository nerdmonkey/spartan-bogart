# Unit tests for Secret Manager response models
# This file will contain tests for the secret manager response models

from datetime import datetime

from app.responses.secret_manager import (
    SecretCreateResponse,
    SecretListResponse,
    SecretMetadataResponse,
    SecretOperationResponse,
    SecretResponse,
)


def test_secret_response_creation():
    """Test SecretResponse model creation."""
    now = datetime.now()
    response = SecretResponse(
        secret_name="test-secret",
        secret_value="test-value",
        version="1",
        created_time=now,
        state="ENABLED",
    )
    assert response.secret_name == "test-secret"
    assert response.secret_value == "test-value"
    assert response.version == "1"
    assert response.created_time == now
    assert response.state == "ENABLED"


def test_secret_create_response_creation():
    """Test SecretCreateResponse model creation."""
    now = datetime.now()
    response = SecretCreateResponse(
        secret_name="test-secret",
        version="1",
        created_time=now,
        replication_policy="automatic",
    )
    assert response.secret_name == "test-secret"
    assert response.version == "1"
    assert response.created_time == now
    assert response.replication_policy == "automatic"


def test_secret_metadata_response_creation():
    """Test SecretMetadataResponse model creation."""
    now = datetime.now()
    labels = {"env": "test"}
    response = SecretMetadataResponse(
        secret_name="test-secret",
        created_time=now,
        labels=labels,
        replication_policy="automatic",
        version_count=3,
    )
    assert response.secret_name == "test-secret"
    assert response.created_time == now
    assert response.labels == labels
    assert response.replication_policy == "automatic"
    assert response.version_count == 3


def test_secret_list_response_creation():
    """Test SecretListResponse model creation."""
    now = datetime.now()
    metadata = SecretMetadataResponse(
        secret_name="test-secret",
        created_time=now,
        replication_policy="automatic",
        version_count=1,
    )
    response = SecretListResponse(
        secrets=[metadata], next_page_token="token123", total_size=1
    )
    assert len(response.secrets) == 1
    assert response.next_page_token == "token123"
    assert response.total_size == 1


def test_secret_operation_response_creation():
    """Test SecretOperationResponse model creation."""
    now = datetime.now()
    response = SecretOperationResponse(
        success=True, message="Operation completed successfully", operation_time=now
    )
    assert response.success is True
    assert response.message == "Operation completed successfully"
    assert response.operation_time == now


def test_secret_response_datetime_serialization():
    """Test SecretResponse datetime serialization."""
    now = datetime.now()
    response = SecretResponse(
        secret_name="test-secret",
        secret_value="test-value",
        version="1",
        created_time=now,
        state="ENABLED",
    )

    # Test model_dump includes datetime
    data = response.model_dump()
    assert "created_time" in data
    assert data["created_time"] == now

    # Test reconstruction from dict
    reconstructed = SecretResponse(**data)
    assert reconstructed.created_time == now


def test_secret_metadata_response_optional_fields():
    """Test SecretMetadataResponse with optional fields."""
    now = datetime.now()

    # Test with None labels
    response_no_labels = SecretMetadataResponse(
        secret_name="test-secret",
        created_time=now,
        labels=None,
        replication_policy="automatic",
        version_count=1,
    )
    assert response_no_labels.labels is None

    # Test serialization with None labels
    data = response_no_labels.model_dump()
    reconstructed = SecretMetadataResponse(**data)
    assert reconstructed.labels is None


def test_secret_list_response_optional_pagination():
    """Test SecretListResponse with optional pagination fields."""
    now = datetime.now()
    metadata = SecretMetadataResponse(
        secret_name="test-secret",
        created_time=now,
        replication_policy="automatic",
        version_count=1,
    )

    # Test with None pagination fields
    response = SecretListResponse(
        secrets=[metadata], next_page_token=None, total_size=None
    )
    assert response.next_page_token is None
    assert response.total_size is None

    # Test serialization preserves None values
    data = response.model_dump()
    reconstructed = SecretListResponse(**data)
    assert reconstructed.next_page_token is None
    assert reconstructed.total_size is None
