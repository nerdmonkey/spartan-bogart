# Unit tests for Secret Manager request models
# This file will contain tests for the secret manager request models

import pytest
from pydantic import ValidationError

from app.requests.secret_manager import (
    SecretAccessRequest,
    SecretCreateRequest,
    SecretVersionCreateRequest,
)


def test_secret_create_request_valid():
    """Test valid SecretCreateRequest creation."""
    request = SecretCreateRequest(secret_name="test-secret", secret_value="test-value")
    assert request.secret_name == "test-secret"
    assert request.secret_value == "test-value"
    assert request.replication_policy == "automatic"
    assert request.labels is None


def test_secret_create_request_with_labels():
    """Test SecretCreateRequest with labels."""
    labels = {"env": "test", "team": "backend"}
    request = SecretCreateRequest(
        secret_name="test-secret", secret_value="test-value", labels=labels
    )
    assert request.labels == labels


def test_secret_create_request_empty_name():
    """Test SecretCreateRequest with empty name raises validation error."""
    with pytest.raises(ValidationError):
        SecretCreateRequest(secret_name="", secret_value="test-value")


def test_secret_create_request_whitespace_name():
    """Test SecretCreateRequest with whitespace name raises validation error."""
    with pytest.raises(ValidationError):
        SecretCreateRequest(secret_name="   ", secret_value="test-value")


def test_secret_create_request_empty_value():
    """Test SecretCreateRequest with empty value raises validation error."""
    with pytest.raises(ValidationError):
        SecretCreateRequest(secret_name="test-secret", secret_value="")


def test_secret_version_create_request_valid():
    """Test valid SecretVersionCreateRequest creation."""
    request = SecretVersionCreateRequest(
        secret_name="test-secret", secret_value="new-value"
    )
    assert request.secret_name == "test-secret"
    assert request.secret_value == "new-value"


def test_secret_access_request_valid():
    """Test valid SecretAccessRequest creation."""
    request = SecretAccessRequest(secret_name="test-secret")
    assert request.secret_name == "test-secret"
    assert request.version == "latest"


def test_secret_access_request_with_version():
    """Test SecretAccessRequest with specific version."""
    request = SecretAccessRequest(secret_name="test-secret", version="1")
    assert request.version == "1"


def test_secret_create_request_name_trimming():
    """Test SecretCreateRequest trims whitespace from secret name."""
    request = SecretCreateRequest(
        secret_name="  test-secret  ", secret_value="test-value"
    )
    assert request.secret_name == "test-secret"


def test_secret_create_request_long_name():
    """Test SecretCreateRequest with maximum length name."""
    long_name = "a" * 255
    request = SecretCreateRequest(secret_name=long_name, secret_value="test-value")
    assert request.secret_name == long_name


def test_secret_create_request_custom_replication_policy():
    """Test SecretCreateRequest with custom replication policy."""
    request = SecretCreateRequest(
        secret_name="test-secret",
        secret_value="test-value",
        replication_policy="user-managed",
    )
    assert request.replication_policy == "user-managed"


def test_secret_version_create_request_name_trimming():
    """Test SecretVersionCreateRequest trims whitespace from secret name."""
    request = SecretVersionCreateRequest(
        secret_name="  test-secret  ", secret_value="new-value"
    )
    assert request.secret_name == "test-secret"


def test_secret_access_request_name_trimming():
    """Test SecretAccessRequest trims whitespace from secret name."""
    request = SecretAccessRequest(secret_name="  test-secret  ")
    assert request.secret_name == "test-secret"
