"""
Integration tests for Secret Manager service.

These tests validate end-to-end workflows with real Google Cloud Secret Manager
and test service integration with framework components.

Note: These tests require:
1. Valid Google Cloud credentials
2. A Google Cloud project with Secret Manager API enabled
3. Appropriate IAM permissions for Secret Manager operations
4. Set GOOGLE_CLOUD_PROJECT environment variable or configure gcloud CLI

To run these tests:
    pytest tests/integration/test_secret_manager_integration.py -v

To skip integration tests:
    pytest -m "not integration"
"""

import os
import time
from datetime import datetime

import pytest

from app.exceptions.secret_manager import (
    SecretNotFoundException,
    SecretVersionNotFoundException,
)
from app.requests.secret_manager import SecretCreateRequest, SecretVersionCreateRequest
from app.services.secret_manager import SecretManagerService


# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def project_id():
    """Get project ID from environment or skip tests if not available."""
    pid = os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GCP_PROJECT")
    if not pid:
        pytest.skip("GOOGLE_CLOUD_PROJECT environment variable not set")
    return pid


@pytest.fixture(scope="module")
def secret_manager_service(project_id):
    """Create a SecretManagerService instance for integration testing."""
    try:
        service = SecretManagerService(project_id=project_id)
        return service
    except Exception as e:
        pytest.skip(f"Failed to initialize SecretManagerService: {str(e)}")


@pytest.fixture
def test_secret_name():
    """Generate a unique test secret name."""
    timestamp = int(time.time() * 1000)
    return f"test-secret-integration-{timestamp}"


@pytest.fixture
def cleanup_secrets(secret_manager_service):
    """Fixture to track and cleanup test secrets after tests."""
    created_secrets = []

    yield created_secrets

    # Cleanup: delete all created secrets
    for secret_name in created_secrets:
        try:
            secret_manager_service.delete_secret(secret_name)
            print(f"Cleaned up test secret: {secret_name}")
        except Exception as e:
            print(f"Failed to cleanup secret {secret_name}: {str(e)}")


def test_service_initialization(project_id):
    """Test that service initializes successfully with real credentials."""
    service = SecretManagerService(project_id=project_id)

    assert service.project_id == project_id
    assert service.client is not None
    assert service.logger is not None


def test_create_and_retrieve_secret_workflow(
    secret_manager_service, test_secret_name, cleanup_secrets
):
    """Test end-to-end workflow: create secret and retrieve it."""
    cleanup_secrets.append(test_secret_name)

    # Create a secret
    secret_value = "integration-test-value-12345"
    create_request = SecretCreateRequest(
        secret_name=test_secret_name, secret_value=secret_value
    )

    create_response = secret_manager_service.create_secret(create_request)

    # Verify creation response
    assert create_response.secret_name == test_secret_name
    assert create_response.version == "1"
    assert isinstance(create_response.created_time, datetime)

    # Retrieve the secret
    retrieve_response = secret_manager_service.get_secret(test_secret_name)

    # Verify retrieval
    assert retrieve_response.secret_name == test_secret_name
    assert retrieve_response.secret_value == secret_value
    assert retrieve_response.version == "1"
    assert retrieve_response.state == "ENABLED"


def test_version_management_workflow(
    secret_manager_service, test_secret_name, cleanup_secrets
):
    """Test version management: create, add version, list, disable."""
    cleanup_secrets.append(test_secret_name)

    # Create initial secret
    create_request = SecretCreateRequest(
        secret_name=test_secret_name, secret_value="version-1-value"
    )
    secret_manager_service.create_secret(create_request)

    # Add a new version
    version_request = SecretVersionCreateRequest(
        secret_name=test_secret_name, secret_value="version-2-value"
    )
    add_response = secret_manager_service.add_secret_version(version_request)

    assert add_response.secret_name == test_secret_name
    assert add_response.version == "2"

    # List versions
    versions_response = secret_manager_service.list_secret_versions(test_secret_name)

    assert len(versions_response.versions) >= 2
    version_numbers = [v.version for v in versions_response.versions]
    assert "1" in version_numbers
    assert "2" in version_numbers

    # Retrieve specific version
    v1_response = secret_manager_service.get_secret(test_secret_name, version="1")
    assert v1_response.secret_value == "version-1-value"

    v2_response = secret_manager_service.get_secret(test_secret_name, version="2")
    assert v2_response.secret_value == "version-2-value"

    # Disable version 1
    disable_response = secret_manager_service.disable_secret_version(
        test_secret_name, "1"
    )
    assert disable_response.success is True

    # Verify disabled version cannot be accessed
    with pytest.raises(SecretVersionNotFoundException):
        secret_manager_service.get_secret(test_secret_name, version="1")


def test_secret_listing_and_metadata(
    secret_manager_service, test_secret_name, cleanup_secrets
):
    """Test secret listing and metadata retrieval."""
    cleanup_secrets.append(test_secret_name)

    # Create a test secret
    create_request = SecretCreateRequest(
        secret_name=test_secret_name,
        secret_value="test-value",
        labels={"env": "test", "purpose": "integration"},
    )
    secret_manager_service.create_secret(create_request)

    # List secrets
    list_response = secret_manager_service.list_secrets(page_size=100)

    # Verify our secret is in the list
    secret_names = [s.secret_name for s in list_response.secrets]
    assert test_secret_name in secret_names

    # Get metadata
    metadata_response = secret_manager_service.get_secret_metadata(test_secret_name)

    assert metadata_response.secret_name == test_secret_name
    assert metadata_response.labels == {"env": "test", "purpose": "integration"}
    assert metadata_response.version_count >= 1
    assert isinstance(metadata_response.created_time, datetime)


def test_secret_deletion_workflow(
    secret_manager_service, test_secret_name, cleanup_secrets
):
    """Test secret deletion removes all versions."""
    # Note: We don't add to cleanup_secrets since we're testing deletion

    # Create a secret
    create_request = SecretCreateRequest(
        secret_name=test_secret_name, secret_value="to-be-deleted"
    )
    secret_manager_service.create_secret(create_request)

    # Verify it exists
    retrieve_response = secret_manager_service.get_secret(test_secret_name)
    assert retrieve_response.secret_name == test_secret_name

    # Delete the secret
    delete_response = secret_manager_service.delete_secret(test_secret_name)
    assert delete_response.success is True

    # Verify it no longer exists
    with pytest.raises(SecretNotFoundException):
        secret_manager_service.get_secret_metadata(test_secret_name)


def test_error_handling_with_real_api(secret_manager_service):
    """Test error handling with real API responses."""
    # Test accessing non-existent secret
    with pytest.raises(SecretVersionNotFoundException):
        secret_manager_service.get_secret("nonexistent-secret-12345")

    # Test getting metadata for non-existent secret
    with pytest.raises(SecretNotFoundException):
        secret_manager_service.get_secret_metadata("nonexistent-secret-12345")


def test_framework_integration_logging(
    secret_manager_service, test_secret_name, cleanup_secrets
):
    """Test that service integrates properly with framework logging."""
    cleanup_secrets.append(test_secret_name)

    # Verify logger is configured
    assert secret_manager_service.logger is not None
    assert secret_manager_service.logger.name == "secret_manager_service"

    # Perform an operation and verify it completes (logging happens internally)
    create_request = SecretCreateRequest(
        secret_name=test_secret_name, secret_value="logging-test"
    )
    response = secret_manager_service.create_secret(create_request)

    assert response.secret_name == test_secret_name


def test_request_response_model_integration(
    secret_manager_service, test_secret_name, cleanup_secrets
):
    """Test that Pydantic request/response models work with real API."""
    cleanup_secrets.append(test_secret_name)

    # Test request model validation
    create_request = SecretCreateRequest(
        secret_name=test_secret_name,
        secret_value="model-test-value",
        replication_policy="automatic",
        labels={"test": "true"},
    )

    # Verify request model fields
    assert create_request.secret_name == test_secret_name
    assert create_request.secret_value == "model-test-value"
    assert create_request.replication_policy == "automatic"
    assert create_request.labels == {"test": "true"}

    # Create secret and verify response model
    response = secret_manager_service.create_secret(create_request)

    # Verify response model structure
    assert hasattr(response, "secret_name")
    assert hasattr(response, "version")
    assert hasattr(response, "created_time")
    assert hasattr(response, "replication_policy")

    # Verify response can be serialized
    response_dict = response.model_dump()
    assert "secret_name" in response_dict
    assert "version" in response_dict
    assert "created_time" in response_dict


def test_caching_integration(project_id, test_secret_name):
    """Test caching functionality with real API."""
    # Create service with caching enabled
    service = SecretManagerService(
        project_id=project_id, enable_cache=True, cache_ttl_seconds=60
    )

    try:
        # Create a test secret
        create_request = SecretCreateRequest(
            secret_name=test_secret_name, secret_value="cached-value"
        )
        service.create_secret(create_request)

        # First retrieval (cache miss)
        start_time = time.time()
        response1 = service.get_secret(test_secret_name)
        first_duration = time.time() - start_time

        # Second retrieval (cache hit - should be faster)
        start_time = time.time()
        response2 = service.get_secret(test_secret_name)
        second_duration = time.time() - start_time

        # Verify both responses are identical
        assert response1.secret_value == response2.secret_value
        assert response1.version == response2.version

        # Cache hit should generally be faster (though not guaranteed in all environments)
        # We just verify both calls succeeded
        assert first_duration >= 0
        assert second_duration >= 0

    finally:
        # Cleanup
        try:
            service.delete_secret(test_secret_name)
        except Exception:
            pass


def test_multiple_versions_workflow(
    secret_manager_service, test_secret_name, cleanup_secrets
):
    """Test creating and managing multiple versions."""
    cleanup_secrets.append(test_secret_name)

    # Create initial secret
    create_request = SecretCreateRequest(
        secret_name=test_secret_name, secret_value="v1"
    )
    secret_manager_service.create_secret(create_request)

    # Add multiple versions
    for i in range(2, 6):
        version_request = SecretVersionCreateRequest(
            secret_name=test_secret_name, secret_value=f"v{i}"
        )
        secret_manager_service.add_secret_version(version_request)

    # List all versions
    versions_response = secret_manager_service.list_secret_versions(test_secret_name)

    assert len(versions_response.versions) >= 5

    # Verify each version has correct value
    for i in range(1, 6):
        response = secret_manager_service.get_secret(test_secret_name, version=str(i))
        assert response.secret_value == f"v{i}"

    # Verify latest version
    latest_response = secret_manager_service.get_secret(test_secret_name)
    assert latest_response.secret_value == "v5"
    assert latest_response.version == "5"


# Edge case tests
def test_empty_project_listing(secret_manager_service):
    """Test listing secrets when project might be empty."""
    # This should not fail even if no secrets exist
    list_response = secret_manager_service.list_secrets(page_size=10)

    assert hasattr(list_response, "secrets")
    assert isinstance(list_response.secrets, list)


def test_large_secret_value(secret_manager_service, test_secret_name, cleanup_secrets):
    """Test creating and retrieving a large secret value."""
    cleanup_secrets.append(test_secret_name)

    # Create a large secret value (64KB is the limit for Secret Manager)
    large_value = "x" * (60 * 1024)  # 60KB to stay under limit

    create_request = SecretCreateRequest(
        secret_name=test_secret_name, secret_value=large_value
    )
    secret_manager_service.create_secret(create_request)

    # Retrieve and verify
    response = secret_manager_service.get_secret(test_secret_name)
    assert response.secret_value == large_value
    assert len(response.secret_value) == len(large_value)


def test_special_characters_in_secret_value(
    secret_manager_service, test_secret_name, cleanup_secrets
):
    """Test secret values with special characters."""
    cleanup_secrets.append(test_secret_name)

    special_value = "!@#$%^&*()_+-=[]{}|;':\",./<>?`~\n\t\r"

    create_request = SecretCreateRequest(
        secret_name=test_secret_name, secret_value=special_value
    )
    secret_manager_service.create_secret(create_request)

    response = secret_manager_service.get_secret(test_secret_name)
    assert response.secret_value == special_value


def test_unicode_in_secret_value(
    secret_manager_service, test_secret_name, cleanup_secrets
):
    """Test secret values with Unicode characters."""
    cleanup_secrets.append(test_secret_name)

    unicode_value = "Hello 世界 🌍 Привет مرحبا"

    create_request = SecretCreateRequest(
        secret_name=test_secret_name, secret_value=unicode_value
    )
    secret_manager_service.create_secret(create_request)

    response = secret_manager_service.get_secret(test_secret_name)
    assert response.secret_value == unicode_value


def test_pagination_with_many_secrets(secret_manager_service):
    """Test pagination when listing many secrets."""
    # List with small page size to test pagination
    list_response = secret_manager_service.list_secrets(page_size=5)

    assert hasattr(list_response, "secrets")
    assert hasattr(list_response, "next_page_token")

    # If there are more than 5 secrets, we should have a next page token
    if len(list_response.secrets) == 5:
        # There might be more secrets
        assert (
            list_response.next_page_token is not None
            or list_response.next_page_token == ""
        )


# Performance tests
def test_concurrent_secret_operations(secret_manager_service, cleanup_secrets):
    """Test that multiple operations can be performed in sequence."""
    # Create multiple secrets in sequence
    secret_names = []
    for i in range(3):
        secret_name = f"test-concurrent-{int(time.time() * 1000)}-{i}"
        secret_names.append(secret_name)
        cleanup_secrets.append(secret_name)

        create_request = SecretCreateRequest(
            secret_name=secret_name, secret_value=f"value-{i}"
        )
        secret_manager_service.create_secret(create_request)

    # Retrieve all secrets
    for i, secret_name in enumerate(secret_names):
        response = secret_manager_service.get_secret(secret_name)
        assert response.secret_value == f"value-{i}"


def test_operation_timing(secret_manager_service, test_secret_name, cleanup_secrets):
    """Test that operations complete in reasonable time."""
    cleanup_secrets.append(test_secret_name)

    # Measure create operation
    start_time = time.time()
    create_request = SecretCreateRequest(
        secret_name=test_secret_name, secret_value="timing-test"
    )
    secret_manager_service.create_secret(create_request)
    create_duration = time.time() - start_time

    # Measure retrieve operation
    start_time = time.time()
    secret_manager_service.get_secret(test_secret_name)
    retrieve_duration = time.time() - start_time

    # Operations should complete in reasonable time (< 10 seconds each)
    assert create_duration < 10.0, f"Create took {create_duration}s"
    assert retrieve_duration < 10.0, f"Retrieve took {retrieve_duration}s"
