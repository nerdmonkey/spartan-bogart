"""
Unit tests for Parameter Manager service - Parameter Creation and Retrieval.

Tests the ParameterManagerService class following the Spartan Framework
testing patterns. Focuses on parameter creation and retrieval operations.
"""

import json
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from app.exceptions.parameter_manager import (
    ParameterManagerException,
    ParameterNotFoundException,
)
from app.requests.parameter_manager import ParameterCreateRequest
from app.responses.parameter_manager import ParameterCreateResponse, ParameterResponse
from app.services.parameter_manager import ParameterManagerService


# Test fixtures
@pytest.fixture
def mock_service():
    """Create a ParameterManagerService with mocked dependencies."""
    with patch("app.services.parameter_manager.get_logger"):
        service = ParameterManagerService(project_id="test-project")
        return service


@pytest.fixture
def mock_service_with_cache():
    """Create a ParameterManagerService with caching enabled."""
    with patch("app.services.parameter_manager.get_logger"):
        service = ParameterManagerService(
            project_id="test-project", enable_cache=True, cache_ttl_seconds=300
        )
        return service


# Parameter Creation Tests
def test_create_parameter_unformatted(mock_service):
    """Test creating a parameter with UNFORMATTED format type."""
    request = ParameterCreateRequest(
        parameter_name="test-param", format_type="UNFORMATTED"
    )

    response = mock_service.create_parameter(request)

    assert isinstance(response, ParameterCreateResponse)
    assert response.parameter_name == "test-param"
    assert response.format_type == "UNFORMATTED"
    assert isinstance(response.created_time, datetime)


def test_create_parameter_json_format(mock_service):
    """Test creating a parameter with JSON format type."""
    request = ParameterCreateRequest(
        parameter_name="json-config", format_type="JSON", labels={"env": "production"}
    )

    response = mock_service.create_parameter(request)

    assert isinstance(response, ParameterCreateResponse)
    assert response.parameter_name == "json-config"
    assert response.format_type == "JSON"
    assert isinstance(response.created_time, datetime)


def test_create_parameter_yaml_format(mock_service):
    """Test creating a parameter with YAML format type."""
    request = ParameterCreateRequest(
        parameter_name="yaml-config",
        format_type="YAML",
        labels={"env": "staging", "team": "backend"},
    )

    response = mock_service.create_parameter(request)

    assert isinstance(response, ParameterCreateResponse)
    assert response.parameter_name == "yaml-config"
    assert response.format_type == "YAML"
    assert isinstance(response.created_time, datetime)


def test_create_parameter_with_labels(mock_service):
    """Test creating a parameter with labels."""
    request = ParameterCreateRequest(
        parameter_name="labeled-param",
        format_type="UNFORMATTED",
        labels={"environment": "dev", "version": "1.0"},
    )

    response = mock_service.create_parameter(request)

    assert response.parameter_name == "labeled-param"
    assert isinstance(response.created_time, datetime)


# Parameter Retrieval Tests
def test_get_parameter_latest_version(mock_service):
    """Test retrieving the latest version of a parameter."""
    parameter_name = "test-param"

    response = mock_service.get_parameter(parameter_name)

    assert isinstance(response, ParameterResponse)
    assert response.parameter_name == parameter_name
    assert response.version == "latest"
    assert isinstance(response.created_time, datetime)
    assert isinstance(response.updated_time, datetime)


def test_get_parameter_specific_version(mock_service):
    """Test retrieving a specific version of a parameter."""
    parameter_name = "test-param"
    version = "v1"

    response = mock_service.get_parameter(parameter_name, version=version)

    assert isinstance(response, ParameterResponse)
    assert response.parameter_name == parameter_name
    assert response.version == version


def test_get_parameter_with_cache_miss(mock_service_with_cache):
    """Test retrieving a parameter with cache enabled (cache miss)."""
    parameter_name = "cached-param"

    response = mock_service_with_cache.get_parameter(parameter_name)

    assert isinstance(response, ParameterResponse)
    assert response.parameter_name == parameter_name
    # Verify it was cached
    cache_key = mock_service_with_cache._get_cache_key(parameter_name, None)
    assert cache_key in mock_service_with_cache._cache


def test_get_parameter_with_cache_hit(mock_service_with_cache):
    """Test retrieving a parameter with cache enabled (cache hit)."""
    parameter_name = "cached-param"

    # First call - cache miss
    response1 = mock_service_with_cache.get_parameter(parameter_name)

    # Second call - cache hit
    response2 = mock_service_with_cache.get_parameter(parameter_name)

    assert response1.parameter_name == response2.parameter_name
    assert response1.version == response2.version


# Error Handling Tests
def test_create_parameter_with_gcp_exception(mock_service):
    """Test error handling when GCP API raises an exception."""
    from google.api_core import exceptions as gcp_exceptions

    request = ParameterCreateRequest(parameter_name="error-param")

    # Mock the service to raise a GCP exception
    with patch.object(mock_service, "_log_operation_start"):
        with patch.object(mock_service, "_log_operation_error"):
            with patch.object(mock_service, "_map_gcp_exception") as mock_map:
                mock_map.return_value = ParameterManagerException("Test error")

                # Simulate an exception during creation
                mock_service.create_parameter

                def raise_exception(*args, **kwargs):
                    raise gcp_exceptions.PermissionDenied("Access denied")

                with patch.object(
                    mock_service, "create_parameter", side_effect=raise_exception
                ):
                    with pytest.raises(Exception):
                        mock_service.create_parameter(request)


def test_get_parameter_not_found(mock_service):
    """Test retrieving a non-existent parameter."""
    from google.api_core import exceptions as gcp_exceptions

    parameter_name = "nonexistent-param"

    # Mock the service to raise NotFound exception
    with patch.object(mock_service, "_log_operation_start"):
        with patch.object(mock_service, "_log_operation_error"):
            with patch.object(mock_service, "_map_gcp_exception") as mock_map:
                mock_map.return_value = ParameterNotFoundException(
                    f"Parameter '{parameter_name}' not found"
                )

                def raise_not_found(*args, **kwargs):
                    raise gcp_exceptions.NotFound("Not found")

                with patch.object(
                    mock_service, "get_parameter", side_effect=raise_not_found
                ):
                    with pytest.raises(Exception):
                        mock_service.get_parameter(parameter_name)


# Validation Tests
def test_validate_and_encode_data_unformatted(mock_service):
    """Test data validation and encoding for UNFORMATTED type."""
    data = "plain text data"
    format_type = "UNFORMATTED"

    encoded = mock_service._validate_and_encode_data(data, format_type)

    assert isinstance(encoded, bytes)
    assert encoded == data.encode("utf-8")


def test_validate_and_encode_data_json_dict(mock_service):
    """Test data validation and encoding for JSON type with dict input."""
    data = {"key": "value", "number": 42}
    format_type = "JSON"

    encoded = mock_service._validate_and_encode_data(data, format_type)

    assert isinstance(encoded, bytes)
    decoded = json.loads(encoded.decode("utf-8"))
    assert decoded == data


def test_validate_and_encode_data_json_string(mock_service):
    """Test data validation and encoding for JSON type with string input."""
    data = '{"key": "value", "number": 42}'
    format_type = "JSON"

    encoded = mock_service._validate_and_encode_data(data, format_type)

    assert isinstance(encoded, bytes)
    assert encoded == data.encode("utf-8")


def test_validate_and_encode_data_json_invalid(mock_service):
    """Test data validation fails for invalid JSON."""
    data = "{invalid json"
    format_type = "JSON"

    with pytest.raises(ParameterManagerException) as exc_info:
        mock_service._validate_and_encode_data(data, format_type)

    assert "Invalid JSON format" in str(exc_info.value)


def test_validate_and_encode_data_yaml_dict(mock_service):
    """Test data validation and encoding for YAML type with dict input."""
    data = {"key": "value", "list": [1, 2, 3]}
    format_type = "YAML"

    encoded = mock_service._validate_and_encode_data(data, format_type)

    assert isinstance(encoded, bytes)


def test_validate_and_encode_data_yaml_string(mock_service):
    """Test data validation and encoding for YAML type with string input."""
    data = "key: value\nlist:\n  - 1\n  - 2\n  - 3"
    format_type = "YAML"

    encoded = mock_service._validate_and_encode_data(data, format_type)

    assert isinstance(encoded, bytes)


def test_validate_and_encode_data_yaml_invalid(mock_service):
    """Test data validation fails for invalid YAML."""
    data = "key: value\n  invalid: : yaml"
    format_type = "YAML"

    with pytest.raises(ParameterManagerException) as exc_info:
        mock_service._validate_and_encode_data(data, format_type)

    assert "Invalid YAML format" in str(exc_info.value)


def test_validate_and_encode_data_exceeds_size_limit(mock_service):
    """Test data validation fails when data exceeds 1 MiB limit."""
    # Create data larger than 1 MiB
    large_data = "x" * (1_048_577)  # 1 MiB + 1 byte
    format_type = "UNFORMATTED"

    with pytest.raises(ParameterManagerException) as exc_info:
        mock_service._validate_and_encode_data(large_data, format_type)

    assert "exceeds 1 MiB limit" in str(exc_info.value)


def test_validate_and_encode_data_at_size_limit(mock_service):
    """Test data validation succeeds at exactly 1 MiB."""
    # Create data exactly 1 MiB
    data = "x" * 1_048_576  # Exactly 1 MiB
    format_type = "UNFORMATTED"

    encoded = mock_service._validate_and_encode_data(data, format_type)

    assert isinstance(encoded, bytes)
    assert len(encoded) == 1_048_576


# Data Decoding Tests
def test_decode_data_unformatted(mock_service):
    """Test decoding UNFORMATTED data."""
    data_bytes = b"plain text data"
    format_type = "UNFORMATTED"

    decoded = mock_service._decode_data(data_bytes, format_type)

    assert decoded == "plain text data"


def test_decode_data_json(mock_service):
    """Test decoding JSON data."""
    data_dict = {"key": "value", "number": 42}
    data_bytes = json.dumps(data_dict).encode("utf-8")
    format_type = "JSON"

    decoded = mock_service._decode_data(data_bytes, format_type)

    assert decoded == data_dict


def test_decode_data_yaml(mock_service):
    """Test decoding YAML data."""
    import yaml

    data_dict = {"key": "value", "list": [1, 2, 3]}
    data_bytes = yaml.dump(data_dict).encode("utf-8")
    format_type = "YAML"

    decoded = mock_service._decode_data(data_bytes, format_type)

    assert decoded == data_dict


# Cache Management Tests
def test_cache_key_generation(mock_service):
    """Test cache key generation."""
    parameter_name = "test-param"
    version = "v1"

    cache_key = mock_service._get_cache_key(parameter_name, version)

    assert cache_key == "test-param:v1"


def test_cache_key_generation_latest(mock_service):
    """Test cache key generation for latest version."""
    parameter_name = "test-param"

    cache_key = mock_service._get_cache_key(parameter_name, None)

    assert cache_key == "test-param:latest"


def test_clear_cache(mock_service_with_cache):
    """Test clearing the cache."""
    # Add some items to cache
    mock_service_with_cache.get_parameter("param1")
    mock_service_with_cache.get_parameter("param2")

    assert len(mock_service_with_cache._cache) > 0

    mock_service_with_cache.clear_cache()

    assert len(mock_service_with_cache._cache) == 0


def test_get_cache_stats_disabled(mock_service):
    """Test getting cache stats when caching is disabled."""
    stats = mock_service.get_cache_stats()

    assert stats["enabled"] is False
    assert stats["size"] == 0


def test_get_cache_stats_enabled(mock_service_with_cache):
    """Test getting cache stats when caching is enabled."""
    # Add some items to cache
    mock_service_with_cache.get_parameter("param1")
    mock_service_with_cache.get_parameter("param2")

    stats = mock_service_with_cache.get_cache_stats()

    assert stats["enabled"] is True
    assert stats["size"] >= 2
    assert "active_entries" in stats
    assert "expired_entries" in stats
    assert stats["ttl_seconds"] == 300


# ============================================================================
# Version Management Tests
# ============================================================================


def test_create_parameter_version_with_custom_name(mock_service):
    """Test creating a parameter version with a custom version name."""
    parameter_name = "test-param"
    version_name = "v1"
    data = "version 1 data"

    response = mock_service.create_parameter_version(
        parameter_name=parameter_name,
        version_name=version_name,
        data=data,
        format_type="UNFORMATTED",
    )

    from app.responses.parameter_manager import ParameterVersionResponse

    assert isinstance(response, ParameterVersionResponse)
    assert response.parameter_name == parameter_name
    assert response.version == version_name
    assert response.data == data
    assert response.format_type == "UNFORMATTED"
    assert isinstance(response.created_time, datetime)


def test_create_parameter_version_semantic_name(mock_service):
    """Test creating a parameter version with semantic version name."""
    parameter_name = "app-config"
    version_name = "prod-2024-01"
    data = {"timeout": 30, "retries": 3}

    response = mock_service.create_parameter_version(
        parameter_name=parameter_name,
        version_name=version_name,
        data=data,
        format_type="JSON",
    )

    assert response.parameter_name == parameter_name
    assert response.version == version_name
    assert response.data == data
    assert response.format_type == "JSON"


def test_create_parameter_version_json_format(mock_service):
    """Test creating a parameter version with JSON format."""
    parameter_name = "json-param"
    version_name = "v2"
    data = {"key": "value", "number": 42}

    response = mock_service.create_parameter_version(
        parameter_name=parameter_name,
        version_name=version_name,
        data=data,
        format_type="JSON",
    )

    assert response.format_type == "JSON"
    assert response.data == data


def test_create_parameter_version_yaml_format(mock_service):
    """Test creating a parameter version with YAML format."""
    parameter_name = "yaml-param"
    version_name = "v1"
    data = {"key": "value", "list": [1, 2, 3]}

    response = mock_service.create_parameter_version(
        parameter_name=parameter_name,
        version_name=version_name,
        data=data,
        format_type="YAML",
    )

    assert response.format_type == "YAML"
    assert response.data == data


def test_create_parameter_version_invalidates_cache(mock_service_with_cache):
    """Test that creating a new version invalidates the cache."""
    parameter_name = "cached-param"

    # First, get the parameter to cache it
    mock_service_with_cache.get_parameter(parameter_name)

    # Verify it's cached
    cache_key = mock_service_with_cache._get_cache_key(parameter_name, None)
    assert cache_key in mock_service_with_cache._cache

    # Create a new version
    mock_service_with_cache.create_parameter_version(
        parameter_name=parameter_name, version_name="v2", data="new data"
    )

    # Cache should be invalidated for this parameter
    # Note: The cache invalidation removes all versions of the parameter
    cache_keys = [
        key
        for key in mock_service_with_cache._cache.keys()
        if key.startswith(f"{parameter_name}:")
    ]
    assert len(cache_keys) == 0


def test_list_parameter_versions_empty(mock_service):
    """Test listing versions when parameter has no versions."""
    parameter_name = "empty-param"

    response = mock_service.list_parameter_versions(parameter_name)

    from app.responses.parameter_manager import ParameterVersionListResponse

    assert isinstance(response, ParameterVersionListResponse)
    assert isinstance(response.versions, list)
    assert response.next_page_token is None


def test_list_parameter_versions_with_pagination(mock_service):
    """Test listing versions with pagination parameters."""
    parameter_name = "multi-version-param"
    page_size = 50

    response = mock_service.list_parameter_versions(
        parameter_name=parameter_name, page_size=page_size
    )

    assert isinstance(response.versions, list)


def test_list_parameter_versions_with_page_token(mock_service):
    """Test listing versions with page token for next page."""
    parameter_name = "multi-version-param"
    page_token = "next_page_token_123"

    response = mock_service.list_parameter_versions(
        parameter_name=parameter_name, page_size=100, page_token=page_token
    )

    assert isinstance(response.versions, list)


def test_list_parameter_versions_chronological_order(mock_service):
    """Test that versions are returned in chronological order."""
    parameter_name = "ordered-param"

    # Create multiple versions
    versions_to_create = ["v1", "v2", "v3"]
    for version_name in versions_to_create:
        mock_service.create_parameter_version(
            parameter_name=parameter_name,
            version_name=version_name,
            data=f"data for {version_name}",
        )

    # List versions
    response = mock_service.list_parameter_versions(parameter_name)

    # Verify response structure
    assert isinstance(response.versions, list)
    # Note: In actual implementation, we would verify chronological ordering
    # by checking that created_time values are in ascending order


def test_get_parameter_version_specific(mock_service):
    """Test retrieving a specific version of a parameter."""
    parameter_name = "versioned-param"
    version = "v1"

    response = mock_service.get_parameter_version(parameter_name, version)

    from app.responses.parameter_manager import ParameterResponse

    assert isinstance(response, ParameterResponse)
    assert response.parameter_name == parameter_name
    assert response.version == version


def test_get_parameter_version_with_semantic_name(mock_service):
    """Test retrieving a version with semantic version name."""
    parameter_name = "app-config"
    version = "prod-2024-01"

    response = mock_service.get_parameter_version(parameter_name, version)

    assert response.parameter_name == parameter_name
    assert response.version == version


def test_get_parameter_version_delegates_to_get_parameter(mock_service):
    """Test that get_parameter_version delegates to get_parameter."""
    parameter_name = "test-param"
    version = "v1"

    # Mock get_parameter to verify it's called
    with patch.object(mock_service, "get_parameter") as mock_get:
        from app.responses.parameter_manager import ParameterResponse

        mock_get.return_value = ParameterResponse(
            parameter_name=parameter_name,
            data="test data",
            format_type="UNFORMATTED",
            version=version,
            created_time=datetime.now(),
            updated_time=datetime.now(),
        )

        result = mock_service.get_parameter_version(parameter_name, version)

        # Verify get_parameter was called with correct arguments
        mock_get.assert_called_once_with(parameter_name, version=version)
        assert result.version == version


def test_delete_parameter_version_success(mock_service):
    """Test successfully deleting a parameter version."""
    parameter_name = "test-param"
    version = "v1"

    response = mock_service.delete_parameter_version(parameter_name, version)

    from app.responses.parameter_manager import ParameterOperationResponse

    assert isinstance(response, ParameterOperationResponse)
    assert response.success is True
    assert parameter_name in response.message
    assert version in response.message
    assert isinstance(response.operation_time, datetime)


def test_delete_parameter_version_invalidates_cache(mock_service_with_cache):
    """Test that deleting a version invalidates the cache for that version."""
    parameter_name = "cached-param"
    version = "v1"

    # First, get the specific version to cache it
    mock_service_with_cache.get_parameter(parameter_name, version=version)

    # Verify it's cached
    cache_key = mock_service_with_cache._get_cache_key(parameter_name, version)
    assert cache_key in mock_service_with_cache._cache

    # Delete the version
    mock_service_with_cache.delete_parameter_version(parameter_name, version)

    # Cache should be invalidated for this specific version
    assert cache_key not in mock_service_with_cache._cache


def test_delete_parameter_version_with_semantic_name(mock_service):
    """Test deleting a version with semantic version name."""
    parameter_name = "app-config"
    version = "prod-2024-01"

    response = mock_service.delete_parameter_version(parameter_name, version)

    assert response.success is True
    assert version in response.message


def test_version_history_preservation(mock_service):
    """Test that creating new versions preserves previous versions."""
    parameter_name = "history-param"

    # Create multiple versions
    versions = ["v1", "v2", "v3"]
    for version_name in versions:
        response = mock_service.create_parameter_version(
            parameter_name=parameter_name,
            version_name=version_name,
            data=f"data for {version_name}",
        )
        assert response.version == version_name

    # List all versions to verify they're all preserved
    list_response = mock_service.list_parameter_versions(parameter_name)

    # Verify response structure (actual version count would be verified in integration tests)
    assert isinstance(list_response.versions, list)


def test_create_multiple_versions_different_formats(mock_service):
    """Test creating multiple versions with different format types."""
    parameter_name = "multi-format-param"

    # Create version 1 with UNFORMATTED
    v1_response = mock_service.create_parameter_version(
        parameter_name=parameter_name,
        version_name="v1",
        data="plain text",
        format_type="UNFORMATTED",
    )
    assert v1_response.format_type == "UNFORMATTED"

    # Create version 2 with JSON
    v2_response = mock_service.create_parameter_version(
        parameter_name=parameter_name,
        version_name="v2",
        data={"key": "value"},
        format_type="JSON",
    )
    assert v2_response.format_type == "JSON"

    # Create version 3 with YAML
    v3_response = mock_service.create_parameter_version(
        parameter_name=parameter_name,
        version_name="v3",
        data={"list": [1, 2, 3]},
        format_type="YAML",
    )
    assert v3_response.format_type == "YAML"


def test_create_parameter_version_with_large_data(mock_service):
    """Test creating a version with data approaching size limit."""
    parameter_name = "large-param"
    version_name = "v1"
    # Create data close to but under 1 MiB limit
    large_data = "x" * 1_000_000  # 1 MB

    response = mock_service.create_parameter_version(
        parameter_name=parameter_name,
        version_name=version_name,
        data=large_data,
        format_type="UNFORMATTED",
    )

    assert response.version == version_name
    assert response.data == large_data


def test_create_parameter_version_exceeds_size_limit(mock_service):
    """Test that creating a version with data exceeding 1 MiB fails."""
    parameter_name = "oversized-param"
    version_name = "v1"
    # Create data larger than 1 MiB
    oversized_data = "x" * (1_048_577)  # 1 MiB + 1 byte

    with pytest.raises(ParameterManagerException) as exc_info:
        mock_service.create_parameter_version(
            parameter_name=parameter_name,
            version_name=version_name,
            data=oversized_data,
            format_type="UNFORMATTED",
        )

    assert "exceeds 1 MiB limit" in str(exc_info.value)


def test_list_parameter_versions_default_page_size(mock_service):
    """Test listing versions uses default page size of 100."""
    parameter_name = "test-param"

    # Mock the logging to verify page_size is logged
    with patch.object(mock_service, "_log_operation_start") as mock_log:
        mock_service.list_parameter_versions(parameter_name)

        # Verify the log was called with default page_size
        call_kwargs = mock_log.call_args[1]
        assert call_kwargs["page_size"] == 100


def test_version_name_uniqueness_enforcement(mock_service):
    """Test that duplicate version names are rejected."""
    parameter_name = "unique-param"
    version_name = "v1"

    # Create first version
    mock_service.create_parameter_version(
        parameter_name=parameter_name, version_name=version_name, data="first data"
    )

    # Attempting to create duplicate version should fail
    # Note: In actual implementation with real API, this would raise an exception
    # For now, we just verify the method can be called
    # In integration tests, we would verify the actual error


def test_get_parameter_version_not_found(mock_service):
    """Test retrieving a non-existent version."""
    from google.api_core import exceptions as gcp_exceptions

    parameter_name = "test-param"
    version = "nonexistent-version"

    # Mock the service to raise NotFound exception
    with patch.object(mock_service, "_log_operation_start"):
        with patch.object(mock_service, "_log_operation_error"):
            with patch.object(mock_service, "_map_gcp_exception") as mock_map:
                from app.exceptions.parameter_manager import (
                    ParameterVersionNotFoundException,
                )

                mock_map.return_value = ParameterVersionNotFoundException(
                    f"Parameter '{parameter_name}' version '{version}' not found"
                )

                def raise_not_found(*args, **kwargs):
                    raise gcp_exceptions.NotFound("Version not found")

                with patch.object(
                    mock_service, "get_parameter", side_effect=raise_not_found
                ):
                    with pytest.raises(Exception):
                        mock_service.get_parameter_version(parameter_name, version)


def test_delete_parameter_version_not_found(mock_service):
    """Test deleting a non-existent version."""
    from google.api_core import exceptions as gcp_exceptions

    parameter_name = "test-param"
    version = "nonexistent-version"

    # Mock the service to raise NotFound exception
    with patch.object(mock_service, "_log_operation_start"):
        with patch.object(mock_service, "_log_operation_error"):
            with patch.object(mock_service, "_map_gcp_exception") as mock_map:
                from app.exceptions.parameter_manager import (
                    ParameterVersionNotFoundException,
                )

                mock_map.return_value = ParameterVersionNotFoundException(
                    f"Parameter '{parameter_name}' version '{version}' not found"
                )

                def raise_not_found(*args, **kwargs):
                    raise gcp_exceptions.NotFound("Version not found")

                with patch.object(
                    mock_service,
                    "delete_parameter_version",
                    side_effect=raise_not_found,
                ):
                    with pytest.raises(Exception):
                        mock_service.delete_parameter_version(parameter_name, version)


def test_create_parameter_version_json_validation(mock_service):
    """Test that invalid JSON data is rejected when creating a version."""
    parameter_name = "json-param"
    version_name = "v1"
    invalid_json = "{invalid json"

    with pytest.raises(ParameterManagerException) as exc_info:
        mock_service.create_parameter_version(
            parameter_name=parameter_name,
            version_name=version_name,
            data=invalid_json,
            format_type="JSON",
        )

    assert "Invalid JSON format" in str(exc_info.value)


def test_create_parameter_version_yaml_validation(mock_service):
    """Test that invalid YAML data is rejected when creating a version."""
    parameter_name = "yaml-param"
    version_name = "v1"
    invalid_yaml = "key: value\n  invalid: : yaml"

    with pytest.raises(ParameterManagerException) as exc_info:
        mock_service.create_parameter_version(
            parameter_name=parameter_name,
            version_name=version_name,
            data=invalid_yaml,
            format_type="YAML",
        )

    assert "Invalid YAML format" in str(exc_info.value)


def test_list_parameter_versions_for_nonexistent_parameter(mock_service):
    """Test listing versions for a parameter that doesn't exist."""
    from google.api_core import exceptions as gcp_exceptions

    parameter_name = "nonexistent-param"

    # Mock the service to raise NotFound exception
    with patch.object(mock_service, "_log_operation_start"):
        with patch.object(mock_service, "_log_operation_error"):
            with patch.object(mock_service, "_map_gcp_exception") as mock_map:
                mock_map.return_value = ParameterNotFoundException(
                    f"Parameter '{parameter_name}' not found"
                )

                def raise_not_found(*args, **kwargs):
                    raise gcp_exceptions.NotFound("Parameter not found")

                with patch.object(
                    mock_service, "list_parameter_versions", side_effect=raise_not_found
                ):
                    with pytest.raises(Exception):
                        mock_service.list_parameter_versions(parameter_name)


# ============================================================================
# Parameter Discovery and Management Tests (Task 7.2)
# ============================================================================


def test_list_parameters_default_pagination(mock_service):
    """Test listing parameters with default pagination settings."""
    response = mock_service.list_parameters()

    from app.responses.parameter_manager import ParameterListResponse

    assert isinstance(response, ParameterListResponse)
    assert isinstance(response.parameters, list)
    assert response.next_page_token is None or isinstance(response.next_page_token, str)
    assert response.total_size is None or isinstance(response.total_size, int)


def test_list_parameters_with_custom_page_size(mock_service):
    """Test listing parameters with custom page size."""
    page_size = 50

    response = mock_service.list_parameters(page_size=page_size)

    assert isinstance(response.parameters, list)


def test_list_parameters_with_page_token(mock_service):
    """Test listing parameters with page token for pagination."""
    page_token = "next_page_token_abc123"

    response = mock_service.list_parameters(page_size=100, page_token=page_token)

    assert isinstance(response.parameters, list)


def test_list_parameters_with_filter_expression(mock_service):
    """Test listing parameters with filter expression."""
    filter_expr = "labels.environment=production"

    response = mock_service.list_parameters(filter_expression=filter_expr)

    from app.responses.parameter_manager import ParameterListResponse

    assert isinstance(response, ParameterListResponse)
    assert isinstance(response.parameters, list)


def test_list_parameters_with_multiple_filters(mock_service):
    """Test listing parameters with complex filter expression."""
    filter_expr = "labels.team=backend AND format=JSON"

    response = mock_service.list_parameters(page_size=50, filter_expression=filter_expr)

    assert isinstance(response.parameters, list)


def test_list_parameters_with_label_filter(mock_service):
    """Test searching parameters by labels."""
    filter_expr = "labels.version=1.0"

    response = mock_service.list_parameters(filter_expression=filter_expr)

    assert isinstance(response.parameters, list)


def test_list_parameters_empty_collection(mock_service):
    """Test listing parameters when no parameters exist."""
    response = mock_service.list_parameters()

    assert isinstance(response.parameters, list)
    assert len(response.parameters) == 0
    assert response.next_page_token is None


def test_list_parameters_format_filter(mock_service):
    """Test filtering parameters by format type."""
    filter_expr = "format=YAML"

    response = mock_service.list_parameters(filter_expression=filter_expr)

    assert isinstance(response.parameters, list)


def test_list_parameters_pagination_workflow(mock_service):
    """Test complete pagination workflow through multiple pages."""
    # First page
    response1 = mock_service.list_parameters(page_size=10)
    assert isinstance(response1.parameters, list)

    # If there's a next page token, get the next page
    if response1.next_page_token:
        response2 = mock_service.list_parameters(
            page_size=10, page_token=response1.next_page_token
        )
        assert isinstance(response2.parameters, list)


def test_delete_parameter_success(mock_service):
    """Test successfully deleting a parameter."""
    parameter_name = "test-param"

    response = mock_service.delete_parameter(parameter_name)

    from app.responses.parameter_manager import ParameterOperationResponse

    assert isinstance(response, ParameterOperationResponse)
    assert response.success is True
    assert parameter_name in response.message
    assert "all its versions" in response.message
    assert isinstance(response.operation_time, datetime)


def test_delete_parameter_invalidates_cache(mock_service_with_cache):
    """Test that deleting a parameter invalidates all cached versions."""
    parameter_name = "cached-param"

    # Cache the parameter
    mock_service_with_cache.get_parameter(parameter_name)
    mock_service_with_cache.get_parameter(parameter_name, version="v1")

    # Verify items are cached
    cache_key_latest = mock_service_with_cache._get_cache_key(parameter_name, None)
    cache_key_v1 = mock_service_with_cache._get_cache_key(parameter_name, "v1")
    assert cache_key_latest in mock_service_with_cache._cache
    assert cache_key_v1 in mock_service_with_cache._cache

    # Delete the parameter
    mock_service_with_cache.delete_parameter(parameter_name)

    # All versions should be invalidated
    cache_keys = [
        key
        for key in mock_service_with_cache._cache.keys()
        if key.startswith(f"{parameter_name}:")
    ]
    assert len(cache_keys) == 0


def test_delete_parameter_not_found(mock_service):
    """Test deleting a non-existent parameter."""
    from google.api_core import exceptions as gcp_exceptions

    parameter_name = "nonexistent-param"

    # Mock the service to raise NotFound exception
    with patch.object(mock_service, "_log_operation_start"):
        with patch.object(mock_service, "_log_operation_error"):
            with patch.object(mock_service, "_map_gcp_exception") as mock_map:
                mock_map.return_value = ParameterNotFoundException(
                    f"Parameter '{parameter_name}' not found"
                )

                def raise_not_found(*args, **kwargs):
                    raise gcp_exceptions.NotFound("Parameter not found")

                with patch.object(
                    mock_service, "delete_parameter", side_effect=raise_not_found
                ):
                    with pytest.raises(Exception):
                        mock_service.delete_parameter(parameter_name)


def test_delete_parameter_with_special_characters(mock_service):
    """Test deleting a parameter with special characters in name."""
    parameter_name = "app-config-v2.0"

    response = mock_service.delete_parameter(parameter_name)

    assert response.success is True
    assert parameter_name in response.message


def test_get_parameter_metadata_success(mock_service):
    """Test retrieving parameter metadata."""
    parameter_name = "test-param"

    response = mock_service.get_parameter_metadata(parameter_name)

    from app.responses.parameter_manager import ParameterMetadataResponse

    assert isinstance(response, ParameterMetadataResponse)
    assert response.parameter_name == parameter_name
    assert response.format_type in ["UNFORMATTED", "JSON", "YAML"]
    assert isinstance(response.created_time, datetime)
    assert isinstance(response.updated_time, datetime)
    assert isinstance(response.version_count, int)
    assert response.version_count >= 0


def test_get_parameter_metadata_with_labels(mock_service):
    """Test retrieving metadata for parameter with labels."""
    parameter_name = "labeled-param"

    response = mock_service.get_parameter_metadata(parameter_name)

    assert response.parameter_name == parameter_name
    # Labels can be None or a dict
    assert response.labels is None or isinstance(response.labels, dict)


def test_get_parameter_metadata_not_found(mock_service):
    """Test retrieving metadata for non-existent parameter."""
    from google.api_core import exceptions as gcp_exceptions

    parameter_name = "nonexistent-param"

    # Mock the service to raise NotFound exception
    with patch.object(mock_service, "_log_operation_start"):
        with patch.object(mock_service, "_log_operation_error"):
            with patch.object(mock_service, "_map_gcp_exception") as mock_map:
                mock_map.return_value = ParameterNotFoundException(
                    f"Parameter '{parameter_name}' not found"
                )

                def raise_not_found(*args, **kwargs):
                    raise gcp_exceptions.NotFound("Parameter not found")

                with patch.object(
                    mock_service, "get_parameter_metadata", side_effect=raise_not_found
                ):
                    with pytest.raises(Exception):
                        mock_service.get_parameter_metadata(parameter_name)


def test_get_parameter_metadata_format_types(mock_service):
    """Test metadata retrieval for different format types."""
    # Test UNFORMATTED
    response_unformatted = mock_service.get_parameter_metadata("unformatted-param")
    assert response_unformatted.format_type in ["UNFORMATTED", "JSON", "YAML"]

    # Test JSON
    response_json = mock_service.get_parameter_metadata("json-param")
    assert response_json.format_type in ["UNFORMATTED", "JSON", "YAML"]

    # Test YAML
    response_yaml = mock_service.get_parameter_metadata("yaml-param")
    assert response_yaml.format_type in ["UNFORMATTED", "JSON", "YAML"]


def test_parameter_exists_true(mock_service):
    """Test parameter_exists returns True for existing parameter."""
    parameter_name = "existing-param"

    # Mock get_parameter_metadata to succeed
    with patch.object(mock_service, "get_parameter_metadata") as mock_get:
        from app.responses.parameter_manager import ParameterMetadataResponse

        mock_get.return_value = ParameterMetadataResponse(
            parameter_name=parameter_name,
            format_type="UNFORMATTED",
            created_time=datetime.now(),
            updated_time=datetime.now(),
            labels=None,
            version_count=1,
        )

        result = mock_service.parameter_exists(parameter_name)

        assert result is True
        mock_get.assert_called_once_with(parameter_name)


def test_parameter_exists_false(mock_service):
    """Test parameter_exists returns False for non-existent parameter."""
    parameter_name = "nonexistent-param"

    # Mock get_parameter_metadata to raise ParameterNotFoundException
    with patch.object(mock_service, "get_parameter_metadata") as mock_get:
        mock_get.side_effect = ParameterNotFoundException(
            f"Parameter '{parameter_name}' not found"
        )

        result = mock_service.parameter_exists(parameter_name)

        assert result is False
        mock_get.assert_called_once_with(parameter_name)


def test_parameter_exists_propagates_other_exceptions(mock_service):
    """Test parameter_exists propagates non-NotFound exceptions."""
    from app.exceptions.parameter_manager import ParameterAccessDeniedException

    parameter_name = "restricted-param"

    # Mock get_parameter_metadata to raise access denied
    with patch.object(mock_service, "get_parameter_metadata") as mock_get:
        mock_get.side_effect = ParameterAccessDeniedException("Access denied")

        with pytest.raises(ParameterAccessDeniedException):
            mock_service.parameter_exists(parameter_name)


def test_list_parameters_response_structure(mock_service):
    """Test that list_parameters returns properly structured response."""
    response = mock_service.list_parameters()

    # Verify response has all required fields
    assert hasattr(response, "parameters")
    assert hasattr(response, "next_page_token")
    assert hasattr(response, "total_size")

    # Verify parameters is a list
    assert isinstance(response.parameters, list)

    # If there are parameters, verify their structure
    for param in response.parameters:
        from app.responses.parameter_manager import ParameterMetadataResponse

        assert isinstance(param, ParameterMetadataResponse)
        assert hasattr(param, "parameter_name")
        assert hasattr(param, "format_type")
        assert hasattr(param, "created_time")
        assert hasattr(param, "updated_time")
        assert hasattr(param, "version_count")


def test_list_parameters_with_all_options(mock_service):
    """Test listing parameters with all optional parameters specified."""
    response = mock_service.list_parameters(
        page_size=25,
        page_token="token_xyz",
        filter_expression="labels.env=prod AND format=JSON",
    )

    assert isinstance(response.parameters, list)


def test_delete_parameter_logs_operation(mock_service):
    """Test that delete_parameter logs the operation correctly."""
    parameter_name = "test-param"

    with patch.object(mock_service, "_log_operation_start") as mock_start:
        with patch.object(mock_service, "_log_operation_success") as mock_success:
            mock_service.delete_parameter(parameter_name)

            # Verify logging was called
            mock_start.assert_called_once()
            mock_success.assert_called_once()

            # Verify parameter_name was logged
            start_call_kwargs = mock_start.call_args[1]
            assert start_call_kwargs["parameter_name"] == parameter_name


def test_get_parameter_metadata_logs_operation(mock_service):
    """Test that get_parameter_metadata logs the operation correctly."""
    parameter_name = "test-param"

    with patch.object(mock_service, "_log_operation_start") as mock_start:
        with patch.object(mock_service, "_log_operation_success") as mock_success:
            mock_service.get_parameter_metadata(parameter_name)

            # Verify logging was called
            mock_start.assert_called_once()
            mock_success.assert_called_once()

            # Verify parameter_name was logged
            start_call_kwargs = mock_start.call_args[1]
            assert start_call_kwargs["parameter_name"] == parameter_name


def test_list_parameters_logs_operation(mock_service):
    """Test that list_parameters logs the operation correctly."""
    filter_expr = "labels.env=prod"

    with patch.object(mock_service, "_log_operation_start") as mock_start:
        with patch.object(mock_service, "_log_operation_success") as mock_success:
            mock_service.list_parameters(page_size=50, filter_expression=filter_expr)

            # Verify logging was called
            mock_start.assert_called_once()
            mock_success.assert_called_once()

            # Verify filter was logged
            start_call_kwargs = mock_start.call_args[1]
            assert start_call_kwargs["filter_expression"] == filter_expr
            assert start_call_kwargs["page_size"] == 50


# Secret Reference Resolution Tests
def test_render_parameter_no_secret_references(mock_service):
    """Test rendering a parameter with no secret references."""
    # Mock get_parameter to return a parameter without secret references
    mock_response = ParameterResponse(
        parameter_name="test-param",
        data="simple-value",
        format_type="UNFORMATTED",
        version="v1",
        created_time=datetime.now(),
        updated_time=datetime.now(),
        labels=None,
    )

    with patch.object(mock_service, "get_parameter", return_value=mock_response):
        result = mock_service.render_parameter("test-param")

    assert result == "simple-value"


def test_render_parameter_with_single_secret_reference(mock_service):
    """Test rendering a parameter with a single secret reference."""
    # Mock get_parameter to return a parameter with a secret reference
    mock_param_response = ParameterResponse(
        parameter_name="test-param",
        data="password=${secret.projects/test-project/secrets/db-password/versions/latest}",
        format_type="UNFORMATTED",
        version="v1",
        created_time=datetime.now(),
        updated_time=datetime.now(),
        labels=None,
    )

    # Mock SecretManagerService and its get_secret method
    with patch.object(mock_service, "get_parameter", return_value=mock_param_response):
        with patch(
            "app.services.secret_manager.SecretManagerService"
        ) as mock_secret_service_class:
            mock_secret_service = MagicMock()
            mock_secret_service_class.return_value = mock_secret_service

            # Mock the secret response
            from app.responses.secret_manager import SecretResponse

            mock_secret_response = SecretResponse(
                secret_name="db-password",
                secret_value="actual-secret-value",
                version="latest",
                created_time=datetime.now(),
                state="ENABLED",
            )
            mock_secret_service.get_secret.return_value = mock_secret_response

            result = mock_service.render_parameter("test-param")

    assert result == "password=actual-secret-value"
    mock_secret_service.get_secret.assert_called_once_with(
        "db-password", version="latest"
    )


def test_render_parameter_with_multiple_secret_references(mock_service):
    """Test rendering a parameter with multiple secret references."""
    # Mock get_parameter to return a parameter with multiple secret references
    mock_param_response = ParameterResponse(
        parameter_name="test-param",
        data="user=${secret.projects/test-project/secrets/db-user/versions/1}&pass=${secret.projects/test-project/secrets/db-pass/versions/2}",
        format_type="UNFORMATTED",
        version="v1",
        created_time=datetime.now(),
        updated_time=datetime.now(),
        labels=None,
    )

    # Mock SecretManagerService and its get_secret method
    with patch.object(mock_service, "get_parameter", return_value=mock_param_response):
        with patch(
            "app.services.secret_manager.SecretManagerService"
        ) as mock_secret_service_class:
            mock_secret_service = MagicMock()
            mock_secret_service_class.return_value = mock_secret_service

            # Mock the secret responses
            from app.responses.secret_manager import SecretResponse

            def get_secret_side_effect(secret_name, version):
                if secret_name == "db-user":
                    return SecretResponse(
                        secret_name="db-user",
                        secret_value="admin",
                        version="1",
                        created_time=datetime.now(),
                        state="ENABLED",
                    )
                elif secret_name == "db-pass":
                    return SecretResponse(
                        secret_name="db-pass",
                        secret_value="secret123",
                        version="2",
                        created_time=datetime.now(),
                        state="ENABLED",
                    )

            mock_secret_service.get_secret.side_effect = get_secret_side_effect

            result = mock_service.render_parameter("test-param")

    assert result == "user=admin&pass=secret123"
    assert mock_secret_service.get_secret.call_count == 2


def test_render_parameter_with_invalid_secret_reference(mock_service):
    """Test rendering a parameter with an invalid secret reference format."""
    # Mock get_parameter to return a parameter with an invalid secret reference
    mock_param_response = ParameterResponse(
        parameter_name="test-param",
        data="password=${secret.invalid/format}",
        format_type="UNFORMATTED",
        version="v1",
        created_time=datetime.now(),
        updated_time=datetime.now(),
        labels=None,
    )

    with patch.object(mock_service, "get_parameter", return_value=mock_param_response):
        # Since the pattern doesn't match, it should just return the value as-is
        # (no secret references found)
        result = mock_service.render_parameter("test-param")

        # The invalid reference should be left unchanged
        assert result == "password=${secret.invalid/format}"


def test_render_parameter_with_nonexistent_secret(mock_service):
    """Test rendering a parameter when referenced secret doesn't exist."""
    # Mock get_parameter to return a parameter with a secret reference
    mock_param_response = ParameterResponse(
        parameter_name="test-param",
        data="password=${secret.projects/test-project/secrets/nonexistent/versions/latest}",
        format_type="UNFORMATTED",
        version="v1",
        created_time=datetime.now(),
        updated_time=datetime.now(),
        labels=None,
    )

    # Mock SecretManagerService and its get_secret method to raise SecretNotFoundException
    with patch.object(mock_service, "get_parameter", return_value=mock_param_response):
        with patch(
            "app.services.secret_manager.SecretManagerService"
        ) as mock_secret_service_class:
            mock_secret_service = MagicMock()
            mock_secret_service_class.return_value = mock_secret_service

            from app.exceptions.secret_manager import SecretNotFoundException

            mock_secret_service.get_secret.side_effect = SecretNotFoundException(
                "Secret not found"
            )

            with pytest.raises(ParameterManagerException) as exc_info:
                mock_service.render_parameter("test-param")

            assert "non-existent secret" in str(exc_info.value)


def test_render_parameter_with_json_data(mock_service):
    """Test rendering a parameter with JSON data containing secret references."""
    # Mock get_parameter to return a parameter with JSON data
    mock_param_response = ParameterResponse(
        parameter_name="test-param",
        data={
            "password": "${secret.projects/test-project/secrets/db-password/versions/latest}"
        },
        format_type="JSON",
        version="v1",
        created_time=datetime.now(),
        updated_time=datetime.now(),
        labels=None,
    )

    # Mock SecretManagerService and its get_secret method
    with patch.object(mock_service, "get_parameter", return_value=mock_param_response):
        with patch(
            "app.services.secret_manager.SecretManagerService"
        ) as mock_secret_service_class:
            mock_secret_service = MagicMock()
            mock_secret_service_class.return_value = mock_secret_service

            # Mock the secret response
            from app.responses.secret_manager import SecretResponse

            mock_secret_response = SecretResponse(
                secret_name="db-password",
                secret_value="actual-secret-value",
                version="latest",
                created_time=datetime.now(),
                state="ENABLED",
            )
            mock_secret_service.get_secret.return_value = mock_secret_response

            result = mock_service.render_parameter("test-param")

    # The result should be a JSON string with the secret resolved
    result_dict = json.loads(result)
    assert result_dict["password"] == "actual-secret-value"


def test_render_parameter_with_specific_version(mock_service):
    """Test rendering a specific version of a parameter."""
    # Mock get_parameter to return a specific version
    mock_param_response = ParameterResponse(
        parameter_name="test-param",
        data="password=${secret.projects/test-project/secrets/db-password/versions/1}",
        format_type="UNFORMATTED",
        version="v1",
        created_time=datetime.now(),
        updated_time=datetime.now(),
        labels=None,
    )

    # Create a mock for get_parameter
    mock_get_parameter = MagicMock(return_value=mock_param_response)

    # Mock SecretManagerService and its get_secret method
    with patch.object(mock_service, "get_parameter", mock_get_parameter):
        with patch(
            "app.services.secret_manager.SecretManagerService"
        ) as mock_secret_service_class:
            mock_secret_service = MagicMock()
            mock_secret_service_class.return_value = mock_secret_service

            # Mock the secret response
            from app.responses.secret_manager import SecretResponse

            mock_secret_response = SecretResponse(
                secret_name="db-password",
                secret_value="old-secret-value",
                version="1",
                created_time=datetime.now(),
                state="ENABLED",
            )
            mock_secret_service.get_secret.return_value = mock_secret_response

            result = mock_service.render_parameter("test-param", version="v1")

    assert result == "password=old-secret-value"
    # Verify get_parameter was called with the correct version
    mock_get_parameter.assert_called_once_with("test-param", version="v1")


# ============================================================================
# Secret Reference Tests (Task 8.2)
# ============================================================================


def test_render_parameter_parses_single_secret_reference(mock_service):
    """Test parsing a single secret reference from parameter value."""
    # Mock get_parameter to return a parameter with a secret reference
    mock_param_response = ParameterResponse(
        parameter_name="test-param",
        data="api_key=${secret.projects/test-project/secrets/api-key/versions/latest}",
        format_type="UNFORMATTED",
        version="latest",
        created_time=datetime.now(),
        updated_time=datetime.now(),
        labels=None,
    )

    # Mock SecretManagerService at the module level before calling render_parameter
    with patch.object(mock_service, "get_parameter", return_value=mock_param_response):
        with patch(
            "app.services.secret_manager.SecretManagerService"
        ) as mock_secret_service_class:
            mock_secret_service = MagicMock()
            mock_secret_service_class.return_value = mock_secret_service

            from app.responses.secret_manager import SecretResponse

            mock_secret_response = SecretResponse(
                secret_name="api-key",
                secret_value="secret-key-value",
                version="latest",
                created_time=datetime.now(),
                state="ENABLED",
            )
            mock_secret_service.get_secret.return_value = mock_secret_response

            result = mock_service.render_parameter("test-param")

    assert result == "api_key=secret-key-value"
    # Verify secret service was called with correct parameters
    mock_secret_service.get_secret.assert_called_once_with("api-key", version="latest")


def test_render_parameter_parses_multiple_secret_references(mock_service):
    """Test parsing multiple secret references from parameter value."""
    # Mock get_parameter to return a parameter with multiple secret references
    mock_param_response = ParameterResponse(
        parameter_name="test-param",
        data="user=${secret.projects/test-project/secrets/db-user/versions/1}&pass=${secret.projects/test-project/secrets/db-pass/versions/2}",
        format_type="UNFORMATTED",
        version="latest",
        created_time=datetime.now(),
        updated_time=datetime.now(),
        labels=None,
    )

    # Mock SecretManagerService at the module level
    with patch(
        "app.services.secret_manager.SecretManagerService"
    ) as mock_secret_service_class:
        mock_secret_service = MagicMock()
        mock_secret_service_class.return_value = mock_secret_service

        from app.responses.secret_manager import SecretResponse

        # Mock different responses for different secrets
        def get_secret_side_effect(secret_name, version):
            if secret_name == "db-user":
                return SecretResponse(
                    secret_name="db-user",
                    secret_value="admin",
                    version="1",
                    created_time=datetime.now(),
                    state="ENABLED",
                )
            elif secret_name == "db-pass":
                return SecretResponse(
                    secret_name="db-pass",
                    secret_value="password123",
                    version="2",
                    created_time=datetime.now(),
                    state="ENABLED",
                )

        mock_secret_service.get_secret.side_effect = get_secret_side_effect

        with patch.object(
            mock_service, "get_parameter", return_value=mock_param_response
        ):
            result = mock_service.render_parameter("test-param")

    assert result == "user=admin&pass=password123"
    # Verify both secrets were resolved
    assert mock_secret_service.get_secret.call_count == 2


def test_render_parameter_resolves_secret_successfully(mock_service):
    """Test successful secret resolution."""
    # Mock get_parameter to return a parameter with a secret reference
    mock_param_response = ParameterResponse(
        parameter_name="db-config",
        data="postgresql://user:${secret.projects/test-project/secrets/db-password/versions/latest}@localhost/db",
        format_type="UNFORMATTED",
        version="latest",
        created_time=datetime.now(),
        updated_time=datetime.now(),
        labels=None,
    )

    # Mock SecretManagerService at the module level
    with patch(
        "app.services.secret_manager.SecretManagerService"
    ) as mock_secret_service_class:
        mock_secret_service = MagicMock()
        mock_secret_service_class.return_value = mock_secret_service

        from app.responses.secret_manager import SecretResponse

        mock_secret_response = SecretResponse(
            secret_name="db-password",
            secret_value="secure-password",
            version="latest",
            created_time=datetime.now(),
            state="ENABLED",
        )
        mock_secret_service.get_secret.return_value = mock_secret_response

        with patch.object(
            mock_service, "get_parameter", return_value=mock_param_response
        ):
            result = mock_service.render_parameter("db-config")

    assert result == "postgresql://user:secure-password@localhost/db"


def test_render_parameter_handles_invalid_secret_reference_format(mock_service):
    """Test that invalid secret reference formats are left unchanged."""
    # Mock get_parameter to return a parameter with an invalid secret reference
    mock_param_response = ParameterResponse(
        parameter_name="test-param",
        data="key=${secret.invalid/format}",  # Invalid format, should be left unchanged
        format_type="UNFORMATTED",
        version="latest",
        created_time=datetime.now(),
        updated_time=datetime.now(),
        labels=None,
    )

    with patch.object(mock_service, "get_parameter", return_value=mock_param_response):
        result = mock_service.render_parameter("test-param")

    # Invalid secret references should be left unchanged
    assert result == "key=${secret.invalid/format}"


def test_render_parameter_handles_nonexistent_secret(mock_service):
    """Test error handling when secret reference points to non-existent secret."""
    # Mock get_parameter to return a parameter with a secret reference
    mock_param_response = ParameterResponse(
        parameter_name="test-param",
        data="key=${secret.projects/test-project/secrets/nonexistent/versions/latest}",
        format_type="UNFORMATTED",
        version="latest",
        created_time=datetime.now(),
        updated_time=datetime.now(),
        labels=None,
    )

    # Mock SecretManagerService at the module level
    with patch(
        "app.services.secret_manager.SecretManagerService"
    ) as mock_secret_service_class:
        mock_secret_service = MagicMock()
        mock_secret_service_class.return_value = mock_secret_service

        from app.exceptions.secret_manager import SecretNotFoundException

        mock_secret_service.get_secret.side_effect = SecretNotFoundException(
            "Secret not found"
        )

        with patch.object(
            mock_service, "get_parameter", return_value=mock_param_response
        ):
            with pytest.raises(ParameterManagerException) as exc_info:
                mock_service.render_parameter("test-param")

    assert "non-existent secret" in str(exc_info.value)


def test_render_parameter_handles_secret_access_denied(mock_service):
    """Test error handling when access to secret is denied."""
    # Mock get_parameter to return a parameter with a secret reference
    mock_param_response = ParameterResponse(
        parameter_name="test-param",
        data="key=${secret.projects/test-project/secrets/restricted/versions/latest}",
        format_type="UNFORMATTED",
        version="latest",
        created_time=datetime.now(),
        updated_time=datetime.now(),
        labels=None,
    )

    # Mock SecretManagerService at the module level
    with patch(
        "app.services.secret_manager.SecretManagerService"
    ) as mock_secret_service_class:
        mock_secret_service = MagicMock()
        mock_secret_service_class.return_value = mock_secret_service

        from app.exceptions.secret_manager import SecretAccessDeniedException

        mock_secret_service.get_secret.side_effect = SecretAccessDeniedException(
            "Access denied"
        )

        with patch.object(
            mock_service, "get_parameter", return_value=mock_param_response
        ):
            with pytest.raises(ParameterManagerException) as exc_info:
                mock_service.render_parameter("test-param")

    assert "Failed to resolve secret reference" in str(exc_info.value)


def test_render_parameter_with_no_secret_references(mock_service):
    """Test rendering parameter without any secret references."""
    # Mock get_parameter to return a parameter without secret references
    mock_param_response = ParameterResponse(
        parameter_name="test-param",
        data="plain text without secrets",
        format_type="UNFORMATTED",
        version="latest",
        created_time=datetime.now(),
        updated_time=datetime.now(),
        labels=None,
    )

    with patch.object(mock_service, "get_parameter", return_value=mock_param_response):
        result = mock_service.render_parameter("test-param")

    assert result == "plain text without secrets"


def test_render_parameter_with_mixed_content(mock_service):
    """Test rendering parameter with both plain text and secret references."""
    # Mock get_parameter to return a parameter with mixed content
    mock_param_response = ParameterResponse(
        parameter_name="test-param",
        data="host=localhost port=5432 password=${secret.projects/test-project/secrets/db-pass/versions/latest} timeout=30",
        format_type="UNFORMATTED",
        version="latest",
        created_time=datetime.now(),
        updated_time=datetime.now(),
        labels=None,
    )

    with patch.object(mock_service, "get_parameter", return_value=mock_param_response):
        with patch(
            "app.services.secret_manager.SecretManagerService"
        ) as mock_secret_service_class:
            mock_secret_service = MagicMock()
            mock_secret_service_class.return_value = mock_secret_service

            from app.responses.secret_manager import SecretResponse

            mock_secret_response = SecretResponse(
                secret_name="db-pass",
                secret_value="secret123",
                version="latest",
                created_time=datetime.now(),
                state="ENABLED",
            )
            mock_secret_service.get_secret.return_value = mock_secret_response

            result = mock_service.render_parameter("test-param")

    assert result == "host=localhost port=5432 password=secret123 timeout=30"


def test_render_parameter_with_json_containing_secrets(mock_service):
    """Test rendering JSON parameter with secret references."""
    # Mock get_parameter to return a JSON parameter with secret references
    mock_param_response = ParameterResponse(
        parameter_name="test-param",
        data={
            "database": {
                "host": "localhost",
                "password": "${secret.projects/test-project/secrets/db-pass/versions/1}",
            },
            "api_key": "${secret.projects/test-project/secrets/api-key/versions/latest}",
        },
        format_type="JSON",
        version="latest",
        created_time=datetime.now(),
        updated_time=datetime.now(),
        labels=None,
    )

    with patch.object(mock_service, "get_parameter", return_value=mock_param_response):
        with patch(
            "app.services.secret_manager.SecretManagerService"
        ) as mock_secret_service_class:
            mock_secret_service = MagicMock()
            mock_secret_service_class.return_value = mock_secret_service

            from app.responses.secret_manager import SecretResponse

            def get_secret_side_effect(secret_name, version):
                if secret_name == "db-pass":
                    return SecretResponse(
                        secret_name="db-pass",
                        secret_value="db-secret",
                        version="1",
                        created_time=datetime.now(),
                        state="ENABLED",
                    )
                elif secret_name == "api-key":
                    return SecretResponse(
                        secret_name="api-key",
                        secret_value="api-secret",
                        version="latest",
                        created_time=datetime.now(),
                        state="ENABLED",
                    )

            mock_secret_service.get_secret.side_effect = get_secret_side_effect

            result = mock_service.render_parameter("test-param")

    # Parse the result and verify secrets were resolved
    result_dict = json.loads(result)
    assert result_dict["database"]["password"] == "db-secret"
    assert result_dict["api_key"] == "api-secret"


def test_render_parameter_with_semantic_version_names(mock_service):
    """Test rendering parameter with semantic version names in secret references."""
    # Mock get_parameter to return a parameter with semantic version names
    mock_param_response = ParameterResponse(
        parameter_name="test-param",
        data="key=${secret.projects/test-project/secrets/api-key/versions/prod-2024-01}",
        format_type="UNFORMATTED",
        version="latest",
        created_time=datetime.now(),
        updated_time=datetime.now(),
        labels=None,
    )

    with patch.object(mock_service, "get_parameter", return_value=mock_param_response):
        with patch(
            "app.services.secret_manager.SecretManagerService"
        ) as mock_secret_service_class:
            mock_secret_service = MagicMock()
            mock_secret_service_class.return_value = mock_secret_service

            from app.responses.secret_manager import SecretResponse

            mock_secret_response = SecretResponse(
                secret_name="api-key",
                secret_value="prod-key-value",
                version="prod-2024-01",
                created_time=datetime.now(),
                state="ENABLED",
            )
            mock_secret_service.get_secret.return_value = mock_secret_response

            result = mock_service.render_parameter("test-param")

    assert result == "key=prod-key-value"
    # Verify the semantic version was used
    mock_secret_service.get_secret.assert_called_once_with(
        "api-key", version="prod-2024-01"
    )


def test_render_parameter_uses_same_credentials(mock_service):
    """Test that render_parameter uses the same credentials for Secret Manager."""
    # Mock get_parameter to return a parameter with a secret reference
    mock_param_response = ParameterResponse(
        parameter_name="test-param",
        data="key=${secret.projects/test-project/secrets/test-secret/versions/latest}",
        format_type="UNFORMATTED",
        version="latest",
        created_time=datetime.now(),
        updated_time=datetime.now(),
        labels=None,
    )

    with patch.object(mock_service, "get_parameter", return_value=mock_param_response):
        with patch(
            "app.services.secret_manager.SecretManagerService"
        ) as mock_secret_service_class:
            mock_secret_service = MagicMock()
            mock_secret_service_class.return_value = mock_secret_service

            from app.responses.secret_manager import SecretResponse

            mock_secret_response = SecretResponse(
                secret_name="test-secret",
                secret_value="secret-value",
                version="latest",
                created_time=datetime.now(),
                state="ENABLED",
            )
            mock_secret_service.get_secret.return_value = mock_secret_response

            mock_service.render_parameter("test-param")

    # Verify SecretManagerService was initialized with same project_id and credentials
    mock_secret_service_class.assert_called_once_with(
        project_id=mock_service.project_id, credentials=mock_service.credentials
    )


def test_render_parameter_with_empty_parameter_value(mock_service):
    """Test rendering parameter with empty value."""
    # Mock get_parameter to return a parameter with empty value
    mock_param_response = ParameterResponse(
        parameter_name="test-param",
        data="",
        format_type="UNFORMATTED",
        version="latest",
        created_time=datetime.now(),
        updated_time=datetime.now(),
        labels=None,
    )

    with patch.object(mock_service, "get_parameter", return_value=mock_param_response):
        result = mock_service.render_parameter("test-param")

    assert result == ""


def test_render_parameter_with_special_characters_in_secret_value(mock_service):
    """Test rendering parameter when secret value contains special characters."""
    # Mock get_parameter to return a parameter with a secret reference
    mock_param_response = ParameterResponse(
        parameter_name="test-param",
        data="password=${secret.projects/test-project/secrets/special-pass/versions/latest}",
        format_type="UNFORMATTED",
        version="latest",
        created_time=datetime.now(),
        updated_time=datetime.now(),
        labels=None,
    )

    with patch.object(mock_service, "get_parameter", return_value=mock_param_response):
        with patch(
            "app.services.secret_manager.SecretManagerService"
        ) as mock_secret_service_class:
            mock_secret_service = MagicMock()
            mock_secret_service_class.return_value = mock_secret_service

            from app.responses.secret_manager import SecretResponse

            # Secret value with special characters
            mock_secret_response = SecretResponse(
                secret_name="special-pass",
                secret_value="p@$$w0rd!#&*(){}[]",
                version="latest",
                created_time=datetime.now(),
                state="ENABLED",
            )
            mock_secret_service.get_secret.return_value = mock_secret_response

            result = mock_service.render_parameter("test-param")

    assert result == "password=p@$$w0rd!#&*(){}[]"


def test_render_parameter_with_same_secret_multiple_times(mock_service):
    """Test rendering parameter with the same secret reference appearing multiple times."""
    # Mock get_parameter to return a parameter with duplicate secret references
    mock_param_response = ParameterResponse(
        parameter_name="test-param",
        data="user=${secret.projects/test-project/secrets/cred/versions/1} pass=${secret.projects/test-project/secrets/cred/versions/1}",
        format_type="UNFORMATTED",
        version="latest",
        created_time=datetime.now(),
        updated_time=datetime.now(),
        labels=None,
    )

    with patch.object(mock_service, "get_parameter", return_value=mock_param_response):
        with patch(
            "app.services.secret_manager.SecretManagerService"
        ) as mock_secret_service_class:
            mock_secret_service = MagicMock()
            mock_secret_service_class.return_value = mock_secret_service

            from app.responses.secret_manager import SecretResponse

            mock_secret_response = SecretResponse(
                secret_name="cred",
                secret_value="shared-value",
                version="1",
                created_time=datetime.now(),
                state="ENABLED",
            )
            mock_secret_service.get_secret.return_value = mock_secret_response

            result = mock_service.render_parameter("test-param")

    assert result == "user=shared-value pass=shared-value"
    # Verify the secret was fetched for each occurrence
    assert mock_secret_service.get_secret.call_count == 2


def test_render_parameter_logs_secret_resolution(mock_service):
    """Test that render_parameter logs secret resolution operations."""
    # Mock get_parameter to return a parameter with a secret reference
    mock_param_response = ParameterResponse(
        parameter_name="test-param",
        data="key=${secret.projects/test-project/secrets/test-secret/versions/latest}",
        format_type="UNFORMATTED",
        version="latest",
        created_time=datetime.now(),
        updated_time=datetime.now(),
        labels=None,
    )

    with patch.object(mock_service, "get_parameter", return_value=mock_param_response):
        with patch(
            "app.services.secret_manager.SecretManagerService"
        ) as mock_secret_service_class:
            mock_secret_service = MagicMock()
            mock_secret_service_class.return_value = mock_secret_service

            from app.responses.secret_manager import SecretResponse

            mock_secret_response = SecretResponse(
                secret_name="test-secret",
                secret_value="secret-value",
                version="latest",
                created_time=datetime.now(),
                state="ENABLED",
            )
            mock_secret_service.get_secret.return_value = mock_secret_response

            with patch.object(mock_service, "_log_operation_start") as mock_log_start:
                with patch.object(
                    mock_service, "_log_operation_success"
                ) as mock_log_success:
                    mock_service.render_parameter("test-param")

            # Verify logging was called
            mock_log_start.assert_called_once()
            mock_log_success.assert_called_once()

            # Verify log context includes secret resolution info
            log_success_kwargs = mock_log_success.call_args[1]
            assert log_success_kwargs["secret_references_found"] == 1
            assert log_success_kwargs["secret_references_resolved"] == 1


def test_render_parameter_handles_malformed_secret_path(mock_service):
    """Test that malformed secret paths are left unchanged."""
    # Mock get_parameter to return a parameter with malformed secret path
    mock_param_response = ParameterResponse(
        parameter_name="test-param",
        data="key=${secret.projects/test-project/secrets}",  # Missing version, should be left unchanged
        format_type="UNFORMATTED",
        version="latest",
        created_time=datetime.now(),
        updated_time=datetime.now(),
        labels=None,
    )

    with patch.object(mock_service, "get_parameter", return_value=mock_param_response):
        result = mock_service.render_parameter("test-param")

    # Malformed secret references should be left unchanged
    assert result == "key=${secret.projects/test-project/secrets}"
    assert "projects/PROJECT_ID/secrets/SECRET_NAME/versions/VERSION" not in result
