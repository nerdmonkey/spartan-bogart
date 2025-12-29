"""
Unit tests for Parameter Manager service - Utility Methods.

Tests the utility methods of the ParameterManagerService class following
the Spartan Framework testing patterns. Focuses on parameter existence checking,
cache management, format conversion helpers, and secret reference parsing.
"""

import json
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pytest
import yaml

from app.exceptions.parameter_manager import (
    InvalidParameterValueException,
    ParameterManagerException,
    ParameterNotFoundException,
)
from app.responses.parameter_manager import ParameterMetadataResponse, ParameterResponse
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


# Parameter Existence Checking Tests
def test_parameter_exists_returns_true_when_parameter_found(mock_service):
    """Test parameter_exists returns True when parameter exists."""
    # Mock get_parameter_metadata to return a valid response
    mock_metadata = ParameterMetadataResponse(
        parameter_name="existing-param",
        format_type="UNFORMATTED",
        created_time=datetime.now(),
        updated_time=datetime.now(),
        version_count=1,
    )

    with patch.object(
        mock_service, "get_parameter_metadata", return_value=mock_metadata
    ):
        result = mock_service.parameter_exists("existing-param")

    assert result is True


def test_parameter_exists_returns_false_when_parameter_not_found(mock_service):
    """Test parameter_exists returns False when parameter does not exist."""
    # Mock get_parameter_metadata to raise ParameterNotFoundException
    with patch.object(
        mock_service,
        "get_parameter_metadata",
        side_effect=ParameterNotFoundException("Not found"),
    ):
        result = mock_service.parameter_exists("non-existent-param")

    assert result is False


def test_parameter_exists_raises_exception_for_other_errors(mock_service):
    """Test parameter_exists re-raises exceptions other than ParameterNotFoundException."""
    # Mock get_parameter_metadata to raise a different exception
    with patch.object(
        mock_service,
        "get_parameter_metadata",
        side_effect=ParameterManagerException("Access denied"),
    ):
        with pytest.raises(ParameterManagerException, match="Access denied"):
            mock_service.parameter_exists("test-param")


# Cache Management Tests
def test_clear_cache_removes_all_entries(mock_service_with_cache):
    """Test clear_cache removes all cached entries."""
    # Add some entries to the cache
    mock_service_with_cache._cache = {
        "param1:latest": ("value1", datetime.now() + timedelta(seconds=300)),
        "param2:v1": ("value2", datetime.now() + timedelta(seconds=300)),
        "param3:latest": ("value3", datetime.now() + timedelta(seconds=300)),
    }

    assert len(mock_service_with_cache._cache) == 3

    mock_service_with_cache.clear_cache()

    assert len(mock_service_with_cache._cache) == 0


def test_clear_cache_does_nothing_when_caching_disabled(mock_service):
    """Test clear_cache does nothing when caching is disabled."""
    # Manually add entries to cache (even though caching is disabled)
    mock_service._cache = {
        "param1:latest": ("value1", datetime.now() + timedelta(seconds=300))
    }

    # clear_cache should return early when caching is disabled
    mock_service.clear_cache()

    # Cache should still have the entry (not cleared)
    assert len(mock_service._cache) == 1


def test_get_cache_stats_returns_correct_stats_when_enabled(mock_service_with_cache):
    """Test get_cache_stats returns correct statistics when caching is enabled."""
    # Add some entries to the cache (some expired, some active)
    now = datetime.now()
    mock_service_with_cache._cache = {
        "param1:latest": ("value1", now + timedelta(seconds=300)),  # Active
        "param2:v1": ("value2", now + timedelta(seconds=300)),  # Active
        "param3:latest": ("value3", now - timedelta(seconds=10)),  # Expired
    }

    stats = mock_service_with_cache.get_cache_stats()

    assert stats["enabled"] is True
    assert stats["size"] == 3
    assert stats["expired_entries"] == 1
    assert stats["active_entries"] == 2
    assert stats["ttl_seconds"] == 300
    assert "batch_stats" in stats


def test_get_cache_stats_returns_minimal_stats_when_disabled(mock_service):
    """Test get_cache_stats returns minimal statistics when caching is disabled."""
    stats = mock_service.get_cache_stats()

    assert stats["enabled"] is False
    assert stats["size"] == 0
    assert stats["ttl_seconds"] == 300  # Default value
    assert "batch_stats" in stats


def test_get_cache_stats_includes_batch_stats(mock_service_with_cache):
    """Test get_cache_stats includes batch operation statistics."""
    # Set some batch stats
    mock_service_with_cache._batch_stats = {
        "total_batch_operations": 5,
        "total_parameters_in_batches": 25,
        "cache_hits_in_batches": 10,
    }

    stats = mock_service_with_cache.get_cache_stats()

    assert stats["batch_stats"]["total_batch_operations"] == 5
    assert stats["batch_stats"]["total_parameters_in_batches"] == 25
    assert stats["batch_stats"]["cache_hits_in_batches"] == 10


# Format Conversion Helper Tests
def test_validate_and_encode_data_json_dict(mock_service):
    """Test _validate_and_encode_data with JSON format and dict data."""
    data = {"key": "value", "number": 42}

    result = mock_service._validate_and_encode_data(data, "JSON")

    assert isinstance(result, bytes)
    decoded = json.loads(result.decode("utf-8"))
    assert decoded == data


def test_validate_and_encode_data_json_string(mock_service):
    """Test _validate_and_encode_data with JSON format and string data."""
    data = '{"key": "value", "number": 42}'

    result = mock_service._validate_and_encode_data(data, "JSON")

    assert isinstance(result, bytes)
    decoded = json.loads(result.decode("utf-8"))
    assert decoded == {"key": "value", "number": 42}


def test_validate_and_encode_data_json_invalid_string(mock_service):
    """Test _validate_and_encode_data raises error for invalid JSON string."""
    data = '{"key": "value", invalid}'

    with pytest.raises(InvalidParameterValueException, match="Invalid JSON format"):
        mock_service._validate_and_encode_data(data, "JSON")


def test_validate_and_encode_data_json_invalid_type(mock_service):
    """Test _validate_and_encode_data raises error for invalid JSON data type."""
    data = 12345  # Not a dict or string

    with pytest.raises(
        InvalidParameterValueException, match="Invalid data type for JSON format"
    ):
        mock_service._validate_and_encode_data(data, "JSON")


def test_validate_and_encode_data_yaml_dict(mock_service):
    """Test _validate_and_encode_data with YAML format and dict data."""
    data = {"key": "value", "number": 42}

    result = mock_service._validate_and_encode_data(data, "YAML")

    assert isinstance(result, bytes)
    decoded = yaml.safe_load(result.decode("utf-8"))
    assert decoded == data


def test_validate_and_encode_data_yaml_string(mock_service):
    """Test _validate_and_encode_data with YAML format and string data."""
    data = "key: value\nnumber: 42"

    result = mock_service._validate_and_encode_data(data, "YAML")

    assert isinstance(result, bytes)
    decoded = yaml.safe_load(result.decode("utf-8"))
    assert decoded == {"key": "value", "number": 42}


def test_validate_and_encode_data_yaml_invalid_string(mock_service):
    """Test _validate_and_encode_data raises error for invalid YAML string."""
    data = "key: value\n  invalid: : :"

    with pytest.raises(InvalidParameterValueException, match="Invalid YAML format"):
        mock_service._validate_and_encode_data(data, "YAML")


def test_validate_and_encode_data_yaml_invalid_type(mock_service):
    """Test _validate_and_encode_data raises error for invalid YAML data type."""
    data = [1, 2, 3]  # Not a dict or string

    with pytest.raises(
        InvalidParameterValueException, match="Invalid data type for YAML format"
    ):
        mock_service._validate_and_encode_data(data, "YAML")


def test_validate_and_encode_data_unformatted_string(mock_service):
    """Test _validate_and_encode_data with UNFORMATTED format and string data."""
    data = "plain text value"

    result = mock_service._validate_and_encode_data(data, "UNFORMATTED")

    assert isinstance(result, bytes)
    assert result.decode("utf-8") == data


def test_validate_and_encode_data_unformatted_dict(mock_service):
    """Test _validate_and_encode_data with UNFORMATTED format and dict data."""
    data = {"key": "value"}

    result = mock_service._validate_and_encode_data(data, "UNFORMATTED")

    assert isinstance(result, bytes)
    # Dict should be converted to JSON string for UNFORMATTED
    decoded = json.loads(result.decode("utf-8"))
    assert decoded == data


def test_validate_and_encode_data_size_limit_exceeded(mock_service):
    """Test _validate_and_encode_data raises error when data exceeds 1 MiB limit."""
    # Create data larger than 1 MiB (1,048,576 bytes)
    large_data = "x" * 1_048_577

    with pytest.raises(InvalidParameterValueException, match="exceeds 1 MiB limit"):
        mock_service._validate_and_encode_data(large_data, "UNFORMATTED")


def test_validate_and_encode_data_size_limit_at_boundary(mock_service):
    """Test _validate_and_encode_data succeeds at exactly 1 MiB."""
    # Create data exactly at 1 MiB limit
    data = "x" * 1_048_576

    result = mock_service._validate_and_encode_data(data, "UNFORMATTED")

    assert isinstance(result, bytes)
    assert len(result) == 1_048_576


def test_decode_data_json(mock_service):
    """Test _decode_data with JSON format."""
    data_bytes = b'{"key": "value", "number": 42}'

    result = mock_service._decode_data(data_bytes, "JSON")

    assert isinstance(result, dict)
    assert result == {"key": "value", "number": 42}


def test_decode_data_json_invalid_returns_string(mock_service):
    """Test _decode_data returns string when JSON decoding fails."""
    data_bytes = b"invalid json"

    result = mock_service._decode_data(data_bytes, "JSON")

    # Should return as string when JSON decoding fails
    assert isinstance(result, str)
    assert result == "invalid json"


def test_decode_data_yaml(mock_service):
    """Test _decode_data with YAML format."""
    data_bytes = b"key: value\nnumber: 42"

    result = mock_service._decode_data(data_bytes, "YAML")

    assert isinstance(result, dict)
    assert result == {"key": "value", "number": 42}


def test_decode_data_yaml_invalid_returns_string(mock_service):
    """Test _decode_data returns string when YAML decoding fails."""
    data_bytes = b"invalid: : : yaml"

    result = mock_service._decode_data(data_bytes, "YAML")

    # Should return as string when YAML decoding fails
    assert isinstance(result, str)
    assert result == "invalid: : : yaml"


def test_decode_data_unformatted(mock_service):
    """Test _decode_data with UNFORMATTED format."""
    data_bytes = b"plain text value"

    result = mock_service._decode_data(data_bytes, "UNFORMATTED")

    assert isinstance(result, str)
    assert result == "plain text value"


def test_decode_data_unicode_error(mock_service):
    """Test _decode_data raises error for invalid UTF-8."""
    # Invalid UTF-8 bytes
    data_bytes = b"\xff\xfe"

    with pytest.raises(
        InvalidParameterValueException, match="Failed to decode data from UTF-8"
    ):
        mock_service._decode_data(data_bytes, "UNFORMATTED")


# Secret Reference Parsing Tests (via render_parameter)
def test_render_parameter_no_secret_references(mock_service):
    """Test render_parameter returns value unchanged when no secret references."""
    # Mock get_parameter to return a parameter without secret references
    mock_response = ParameterResponse(
        parameter_name="test-param",
        data="plain value without secrets",
        format_type="UNFORMATTED",
        version="latest",
        created_time=datetime.now(),
        updated_time=datetime.now(),
    )

    with patch.object(mock_service, "get_parameter", return_value=mock_response):
        result = mock_service.render_parameter("test-param")

    assert result == "plain value without secrets"


def test_render_parameter_with_single_secret_reference(mock_service):
    """Test render_parameter resolves a single secret reference."""
    # Mock get_parameter to return a parameter with a secret reference
    mock_response = ParameterResponse(
        parameter_name="test-param",
        data="password=${secret.projects/test-project/secrets/db-password/versions/latest}",
        format_type="UNFORMATTED",
        version="latest",
        created_time=datetime.now(),
        updated_time=datetime.now(),
    )

    # Mock SecretManagerService
    mock_secret_response = Mock()
    mock_secret_response.secret_value = "actual-secret-value"

    with patch.object(mock_service, "get_parameter", return_value=mock_response):
        with patch(
            "app.services.secret_manager.SecretManagerService"
        ) as MockSecretService:
            # Mock the constructor to return a mock instance
            mock_secret_instance = Mock()
            mock_secret_instance.get_secret.return_value = mock_secret_response
            MockSecretService.return_value = mock_secret_instance

            result = mock_service.render_parameter("test-param")

    assert result == "password=actual-secret-value"
    # Verify SecretManagerService was called with correct parameters
    MockSecretService.assert_called_once_with(
        project_id="test-project", credentials=mock_service.credentials
    )


def test_render_parameter_with_multiple_secret_references(mock_service):
    """Test render_parameter resolves multiple secret references."""
    # Mock get_parameter to return a parameter with multiple secret references
    mock_response = ParameterResponse(
        parameter_name="test-param",
        data="user=${secret.projects/test-project/secrets/db-user/versions/1}&pass=${secret.projects/test-project/secrets/db-pass/versions/latest}",
        format_type="UNFORMATTED",
        version="latest",
        created_time=datetime.now(),
        updated_time=datetime.now(),
    )

    # Mock SecretManagerService
    def mock_get_secret(secret_name, version):
        if secret_name == "db-user":
            mock_resp = Mock()
            mock_resp.secret_value = "admin"
            return mock_resp
        elif secret_name == "db-pass":
            mock_resp = Mock()
            mock_resp.secret_value = "secret123"
            return mock_resp

    with patch.object(mock_service, "get_parameter", return_value=mock_response):
        with patch(
            "app.services.secret_manager.SecretManagerService"
        ) as MockSecretService:
            # Mock the constructor to return a mock instance
            mock_secret_instance = Mock()
            mock_secret_instance.get_secret.side_effect = mock_get_secret
            MockSecretService.return_value = mock_secret_instance

            result = mock_service.render_parameter("test-param")

    assert result == "user=admin&pass=secret123"


def test_render_parameter_with_invalid_secret_reference_format(mock_service):
    """Test render_parameter raises error for invalid secret reference format."""
    # Mock get_parameter to return a parameter with a secret reference that matches the regex
    # but has invalid path structure when parsed
    mock_response = ParameterResponse(
        parameter_name="test-param",
        data="password=${secret.projects/test-project/secrets/db-password/versions/latest/extra}",  # Too many parts
        format_type="UNFORMATTED",
        version="latest",
        created_time=datetime.now(),
        updated_time=datetime.now(),
    )

    with patch.object(mock_service, "get_parameter", return_value=mock_response):
        with patch(
            "app.services.secret_manager.SecretManagerService"
        ) as MockSecretService:
            # Mock the constructor to return a mock instance
            mock_secret_instance = Mock()
            MockSecretService.return_value = mock_secret_instance

            # The InvalidParameterValueException is caught and wrapped in ParameterManagerException
            with pytest.raises(
                ParameterManagerException, match="Invalid secret reference format"
            ):
                mock_service.render_parameter("test-param")


def test_render_parameter_with_nonexistent_secret(mock_service):
    """Test render_parameter raises error when secret does not exist."""
    from app.exceptions.secret_manager import SecretNotFoundException

    # Mock get_parameter to return a parameter with a secret reference
    mock_response = ParameterResponse(
        parameter_name="test-param",
        data="password=${secret.projects/test-project/secrets/missing-secret/versions/latest}",
        format_type="UNFORMATTED",
        version="latest",
        created_time=datetime.now(),
        updated_time=datetime.now(),
    )

    with patch.object(mock_service, "get_parameter", return_value=mock_response):
        with patch(
            "app.services.secret_manager.SecretManagerService"
        ) as MockSecretService:
            # Mock the constructor to return a mock instance
            mock_secret_instance = Mock()
            mock_secret_instance.get_secret.side_effect = SecretNotFoundException(
                "Secret not found"
            )
            MockSecretService.return_value = mock_secret_instance

            with pytest.raises(ParameterManagerException, match="non-existent secret"):
                mock_service.render_parameter("test-param")


def test_render_parameter_with_dict_data(mock_service):
    """Test render_parameter converts dict data to JSON string before processing."""
    # Mock get_parameter to return a parameter with dict data
    mock_response = ParameterResponse(
        parameter_name="test-param",
        data={
            "password": "${secret.projects/test-project/secrets/db-password/versions/latest}"
        },
        format_type="JSON",
        version="latest",
        created_time=datetime.now(),
        updated_time=datetime.now(),
    )

    # Mock SecretManagerService
    mock_secret_response = Mock()
    mock_secret_response.secret_value = "actual-secret"

    with patch.object(mock_service, "get_parameter", return_value=mock_response):
        with patch(
            "app.services.secret_manager.SecretManagerService"
        ) as MockSecretService:
            # Mock the constructor to return a mock instance
            mock_secret_instance = Mock()
            mock_secret_instance.get_secret.return_value = mock_secret_response
            MockSecretService.return_value = mock_secret_instance

            result = mock_service.render_parameter("test-param")

    # Result should be JSON string with secret resolved
    assert "actual-secret" in result
    assert "${secret." not in result


def test_render_parameter_with_specific_version(mock_service):
    """Test render_parameter with specific version parameter."""
    # Mock get_parameter to return a specific version
    mock_response = ParameterResponse(
        parameter_name="test-param",
        data="value without secrets",
        format_type="UNFORMATTED",
        version="v1",
        created_time=datetime.now(),
        updated_time=datetime.now(),
    )

    with patch.object(
        mock_service, "get_parameter", return_value=mock_response
    ) as mock_get:
        result = mock_service.render_parameter("test-param", version="v1")

    # Verify get_parameter was called with the correct version
    mock_get.assert_called_once_with("test-param", version="v1")
    assert result == "value without secrets"
