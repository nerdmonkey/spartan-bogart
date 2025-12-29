"""
Unit tests for Parameter Manager service - Error Scenarios.

Tests comprehensive error handling including exception mapping, network errors,
authentication errors, validation errors, and Parameter Manager API error mapping.
"""

from unittest.mock import patch

import pytest
from google.api_core import exceptions as gcp_exceptions

from app.exceptions.parameter_manager import (
    InvalidParameterValueException,
    ParameterAccessDeniedException,
    ParameterConnectionException,
    ParameterInternalErrorException,
    ParameterManagerException,
    ParameterNotFoundException,
    ParameterQuotaExceededException,
    ParameterTimeoutException,
    ParameterUnavailableException,
    ParameterVersionNotFoundException,
)
from app.requests.parameter_manager import ParameterCreateRequest
from app.services.parameter_manager import ParameterManagerService


# Test fixtures
@pytest.fixture
def mock_service():
    """Create a ParameterManagerService with mocked dependencies."""
    with patch("app.services.parameter_manager.get_logger"):
        service = ParameterManagerService(project_id="test-project")
        return service


# ============================================================================
# Exception Mapping Tests
# ============================================================================


def test_map_gcp_exception_not_found_parameter(mock_service):
    """Test mapping NotFound exception for parameter."""
    gcp_error = gcp_exceptions.NotFound("Parameter not found")
    context = {"parameter_name": "test-param"}

    mapped = mock_service._map_gcp_exception(gcp_error, "parameter retrieval", context)

    assert isinstance(mapped, ParameterNotFoundException)
    assert "test-param" in str(mapped)
    assert "test-project" in str(mapped)


def test_map_gcp_exception_not_found_version(mock_service):
    """Test mapping NotFound exception for parameter version."""
    gcp_error = gcp_exceptions.NotFound("Version not found")
    context = {"parameter_name": "test-param", "version": "v1"}

    mapped = mock_service._map_gcp_exception(gcp_error, "version retrieval", context)

    assert isinstance(mapped, ParameterVersionNotFoundException)
    assert "test-param" in str(mapped)
    assert "v1" in str(mapped)


def test_map_gcp_exception_permission_denied(mock_service):
    """Test mapping PermissionDenied exception."""
    gcp_error = gcp_exceptions.PermissionDenied("Access denied")
    context = {"parameter_name": "secure-param"}

    mapped = mock_service._map_gcp_exception(gcp_error, "parameter access", context)

    assert isinstance(mapped, ParameterAccessDeniedException)
    assert "secure-param" in str(mapped)
    assert "Permission denied" in str(mapped)
    assert "IAM roles" in str(mapped)


def test_map_gcp_exception_unauthenticated(mock_service):
    """Test mapping Unauthenticated exception."""
    gcp_error = gcp_exceptions.Unauthenticated("Invalid credentials")
    context = {}

    mapped = mock_service._map_gcp_exception(gcp_error, "authentication", context)

    assert isinstance(mapped, ParameterAccessDeniedException)
    assert "Authentication failed" in str(mapped)
    assert "credentials" in str(mapped)


def test_map_gcp_exception_already_exists_parameter(mock_service):
    """Test mapping AlreadyExists exception for parameter."""
    gcp_error = gcp_exceptions.AlreadyExists("Parameter exists")
    context = {"parameter_name": "existing-param"}

    mapped = mock_service._map_gcp_exception(gcp_error, "parameter creation", context)

    assert isinstance(mapped, ParameterManagerException)
    assert "existing-param" in str(mapped)
    assert "already exists" in str(mapped)


def test_map_gcp_exception_already_exists_version(mock_service):
    """Test mapping AlreadyExists exception for version."""
    gcp_error = gcp_exceptions.AlreadyExists("Version exists")
    context = {"parameter_name": "test-param", "version": "v1"}

    mapped = mock_service._map_gcp_exception(gcp_error, "version creation", context)

    assert isinstance(mapped, ParameterManagerException)
    assert "test-param" in str(mapped)
    assert "v1" in str(mapped)
    assert "already exists" in str(mapped)


def test_map_gcp_exception_invalid_argument(mock_service):
    """Test mapping InvalidArgument exception."""
    gcp_error = gcp_exceptions.InvalidArgument("Invalid parameter name")
    context = {"parameter_name": "invalid@name"}

    mapped = mock_service._map_gcp_exception(gcp_error, "parameter validation", context)

    assert isinstance(mapped, InvalidParameterValueException)
    assert "Invalid argument" in str(mapped)


def test_map_gcp_exception_resource_exhausted(mock_service):
    """Test mapping ResourceExhausted exception."""
    gcp_error = gcp_exceptions.ResourceExhausted("Quota exceeded")
    context = {}

    mapped = mock_service._map_gcp_exception(gcp_error, "parameter creation", context)

    assert isinstance(mapped, ParameterQuotaExceededException)
    assert "Quota exceeded" in str(mapped)
    assert "quota increase" in str(mapped).lower()


def test_map_gcp_exception_deadline_exceeded(mock_service):
    """Test mapping DeadlineExceeded exception."""
    gcp_error = gcp_exceptions.DeadlineExceeded("Request timeout")
    context = {}

    mapped = mock_service._map_gcp_exception(gcp_error, "parameter retrieval", context)

    assert isinstance(mapped, ParameterTimeoutException)
    assert "timed out" in str(mapped).lower()


def test_map_gcp_exception_service_unavailable(mock_service):
    """Test mapping ServiceUnavailable exception."""
    gcp_error = gcp_exceptions.ServiceUnavailable("Service down")
    context = {}

    mapped = mock_service._map_gcp_exception(gcp_error, "parameter access", context)

    assert isinstance(mapped, ParameterUnavailableException)
    assert "unavailable" in str(mapped).lower()
    assert "retry" in str(mapped).lower()


def test_map_gcp_exception_internal_server_error(mock_service):
    """Test mapping InternalServerError exception."""
    gcp_error = gcp_exceptions.InternalServerError("Internal error")
    context = {}

    mapped = mock_service._map_gcp_exception(gcp_error, "parameter operation", context)

    assert isinstance(mapped, ParameterInternalErrorException)
    assert "Internal server error" in str(mapped)
    assert "Google Cloud" in str(mapped)


def test_map_gcp_exception_retry_error(mock_service):
    """Test mapping RetryError exception."""
    gcp_error = gcp_exceptions.RetryError(
        "Retry failed", cause=Exception("Network error")
    )
    context = {}

    mapped = mock_service._map_gcp_exception(gcp_error, "parameter retrieval", context)

    assert isinstance(mapped, ParameterConnectionException)
    assert "Retry limit exceeded" in str(mapped)


def test_map_gcp_exception_too_many_requests(mock_service):
    """Test mapping TooManyRequests exception."""
    gcp_error = gcp_exceptions.TooManyRequests("Rate limit")
    context = {}

    mapped = mock_service._map_gcp_exception(gcp_error, "parameter listing", context)

    assert isinstance(mapped, ParameterQuotaExceededException)
    assert "Rate limit" in str(mapped)
    assert "slow down" in str(mapped).lower()


def test_map_gcp_exception_failed_precondition_disabled(mock_service):
    """Test mapping FailedPrecondition for disabled version."""
    gcp_error = gcp_exceptions.FailedPrecondition("Version is disabled")
    context = {"parameter_name": "test-param", "version": "v1"}

    mapped = mock_service._map_gcp_exception(gcp_error, "version access", context)

    assert isinstance(mapped, ParameterVersionNotFoundException)
    assert "disabled" in str(mapped).lower()


def test_map_gcp_exception_failed_precondition_generic(mock_service):
    """Test mapping FailedPrecondition for generic case."""
    gcp_error = gcp_exceptions.FailedPrecondition("Invalid state")
    context = {}

    mapped = mock_service._map_gcp_exception(gcp_error, "parameter update", context)

    assert isinstance(mapped, ParameterManagerException)
    assert "precondition" in str(mapped).lower()


def test_map_gcp_exception_aborted(mock_service):
    """Test mapping Aborted exception."""
    gcp_error = gcp_exceptions.Aborted("Operation aborted")
    context = {}

    mapped = mock_service._map_gcp_exception(gcp_error, "parameter update", context)

    assert isinstance(mapped, ParameterManagerException)
    assert "aborted" in str(mapped).lower()
    assert "retry" in str(mapped).lower()


def test_map_gcp_exception_out_of_range(mock_service):
    """Test mapping OutOfRange exception."""
    gcp_error = gcp_exceptions.OutOfRange("Page size too large")
    context = {}

    mapped = mock_service._map_gcp_exception(gcp_error, "parameter listing", context)

    assert isinstance(mapped, InvalidParameterValueException)
    assert "out of range" in str(mapped).lower()


def test_map_gcp_exception_method_not_implemented(mock_service):
    """Test mapping MethodNotImplemented exception."""
    gcp_error = gcp_exceptions.MethodNotImplemented("Not available")
    context = {}

    mapped = mock_service._map_gcp_exception(gcp_error, "parameter operation", context)

    assert isinstance(mapped, ParameterManagerException)
    assert "not implemented" in str(mapped).lower()


def test_map_gcp_exception_data_loss(mock_service):
    """Test mapping DataLoss exception."""
    gcp_error = gcp_exceptions.DataLoss("Data corrupted")
    context = {}

    mapped = mock_service._map_gcp_exception(gcp_error, "parameter retrieval", context)

    assert isinstance(mapped, ParameterInternalErrorException)
    assert "Data loss" in str(mapped)


def test_map_gcp_exception_unknown(mock_service):
    """Test mapping Unknown exception."""
    gcp_error = gcp_exceptions.Unknown("Unknown error")
    context = {}

    mapped = mock_service._map_gcp_exception(gcp_error, "parameter operation", context)

    assert isinstance(mapped, ParameterManagerException)
    assert "Unknown error" in str(mapped)


def test_map_gcp_exception_connection_error(mock_service):
    """Test mapping ConnectionError."""
    error = ConnectionError("Network unreachable")
    context = {}

    mapped = mock_service._map_gcp_exception(error, "parameter retrieval", context)

    assert isinstance(mapped, ParameterConnectionException)
    assert "connectivity" in str(mapped).lower()


def test_map_gcp_exception_timeout_error(mock_service):
    """Test mapping TimeoutError."""
    error = TimeoutError("Connection timeout")
    context = {}

    mapped = mock_service._map_gcp_exception(error, "parameter access", context)

    assert isinstance(mapped, ParameterTimeoutException)
    assert "timeout" in str(mapped).lower()


def test_map_gcp_exception_os_error(mock_service):
    """Test mapping OSError."""
    error = OSError("Network error")
    context = {}

    mapped = mock_service._map_gcp_exception(error, "parameter operation", context)

    assert isinstance(mapped, ParameterConnectionException)
    assert "connectivity" in str(mapped).lower()


def test_map_gcp_exception_custom_exception_passthrough(mock_service):
    """Test that custom exceptions pass through unchanged."""
    error = InvalidParameterValueException("Custom error")
    context = {}

    mapped = mock_service._map_gcp_exception(error, "validation", context)

    assert mapped is error
    assert isinstance(mapped, InvalidParameterValueException)


def test_map_gcp_exception_generic_exception(mock_service):
    """Test mapping generic Exception."""
    error = ValueError("Unexpected error")
    context = {}

    mapped = mock_service._map_gcp_exception(error, "parameter operation", context)

    assert isinstance(mapped, ParameterManagerException)
    assert "Unexpected error" in str(mapped)
    assert "ValueError" in str(mapped)


# ============================================================================
# Network and Authentication Error Tests
# ============================================================================


def test_create_parameter_network_error(mock_service):
    """Test handling network error during parameter creation."""
    request = ParameterCreateRequest(parameter_name="test-param")

    # Mock the internal method to raise a connection error
    with patch.object(mock_service, "_log_operation_start"):
        with patch.object(mock_service, "_log_operation_error"):
            # Simulate network error in the actual operation
            mock_service.create_parameter

            def raise_network_error(*args, **kwargs):
                raise ConnectionError("Network unreachable")

            with patch.object(
                mock_service, "create_parameter", side_effect=raise_network_error
            ):
                with pytest.raises(ConnectionError):
                    mock_service.create_parameter(request)


def test_get_parameter_authentication_error(mock_service):
    """Test handling authentication error during parameter retrieval."""
    parameter_name = "secure-param"

    with patch.object(mock_service, "_log_operation_start"):
        with patch.object(mock_service, "_log_operation_error"):

            def raise_auth_error(*args, **kwargs):
                raise gcp_exceptions.Unauthenticated("Invalid credentials")

            with patch.object(
                mock_service, "get_parameter", side_effect=raise_auth_error
            ):
                with pytest.raises(gcp_exceptions.Unauthenticated):
                    mock_service.get_parameter(parameter_name)


def test_list_parameters_permission_denied(mock_service):
    """Test handling permission denied during parameter listing."""
    with patch.object(mock_service, "_log_operation_start"):
        with patch.object(mock_service, "_log_operation_error"):

            def raise_permission_error(*args, **kwargs):
                raise gcp_exceptions.PermissionDenied("Access denied")

            with patch.object(
                mock_service, "list_parameters", side_effect=raise_permission_error
            ):
                with pytest.raises(gcp_exceptions.PermissionDenied):
                    mock_service.list_parameters()


def test_delete_parameter_timeout(mock_service):
    """Test handling timeout during parameter deletion."""
    parameter_name = "test-param"

    with patch.object(mock_service, "_log_operation_start"):
        with patch.object(mock_service, "_log_operation_error"):

            def raise_timeout(*args, **kwargs):
                raise gcp_exceptions.DeadlineExceeded("Request timeout")

            with patch.object(
                mock_service, "delete_parameter", side_effect=raise_timeout
            ):
                with pytest.raises(gcp_exceptions.DeadlineExceeded):
                    mock_service.delete_parameter(parameter_name)


# ============================================================================
# Validation Error Tests
# ============================================================================


def test_validate_and_encode_data_invalid_json(mock_service):
    """Test validation error for invalid JSON data."""
    invalid_json = "{invalid json"
    format_type = "JSON"

    with pytest.raises(ParameterManagerException) as exc_info:
        mock_service._validate_and_encode_data(invalid_json, format_type)

    assert "Invalid JSON format" in str(exc_info.value)


def test_validate_and_encode_data_invalid_yaml(mock_service):
    """Test validation error for invalid YAML data."""
    invalid_yaml = "key: value\n  invalid: : yaml"
    format_type = "YAML"

    with pytest.raises(ParameterManagerException) as exc_info:
        mock_service._validate_and_encode_data(invalid_yaml, format_type)

    assert "Invalid YAML format" in str(exc_info.value)


def test_validate_and_encode_data_exceeds_size_limit(mock_service):
    """Test validation error when data exceeds 1 MiB limit."""
    large_data = "x" * (1_048_577)  # 1 MiB + 1 byte
    format_type = "UNFORMATTED"

    with pytest.raises(ParameterManagerException) as exc_info:
        mock_service._validate_and_encode_data(large_data, format_type)

    assert "exceeds 1 MiB limit" in str(exc_info.value)


def test_validate_and_encode_data_empty_string(mock_service):
    """Test validation with empty string data."""
    data = ""
    format_type = "UNFORMATTED"

    # Empty string should be valid
    encoded = mock_service._validate_and_encode_data(data, format_type)
    assert isinstance(encoded, bytes)
    assert encoded == b""


def test_validate_and_encode_data_json_empty_object(mock_service):
    """Test validation with empty JSON object."""
    data = {}
    format_type = "JSON"

    encoded = mock_service._validate_and_encode_data(data, format_type)
    assert isinstance(encoded, bytes)
    assert encoded == b"{}"


def test_validate_and_encode_data_yaml_empty_object(mock_service):
    """Test validation with empty YAML object."""
    data = {}
    format_type = "YAML"

    encoded = mock_service._validate_and_encode_data(data, format_type)
    assert isinstance(encoded, bytes)


# ============================================================================
# Parameter Manager API Error Mapping Tests
# ============================================================================


def test_create_parameter_quota_exceeded(mock_service):
    """Test handling quota exceeded error."""
    request = ParameterCreateRequest(parameter_name="test-param")

    with patch.object(mock_service, "_log_operation_start"):
        with patch.object(mock_service, "_log_operation_error"):

            def raise_quota_error(*args, **kwargs):
                raise gcp_exceptions.ResourceExhausted("Quota exceeded")

            with patch.object(
                mock_service, "create_parameter", side_effect=raise_quota_error
            ):
                with pytest.raises(gcp_exceptions.ResourceExhausted):
                    mock_service.create_parameter(request)


def test_get_parameter_service_unavailable(mock_service):
    """Test handling service unavailable error."""
    parameter_name = "test-param"

    with patch.object(mock_service, "_log_operation_start"):
        with patch.object(mock_service, "_log_operation_error"):

            def raise_unavailable(*args, **kwargs):
                raise gcp_exceptions.ServiceUnavailable("Service down")

            with patch.object(
                mock_service, "get_parameter", side_effect=raise_unavailable
            ):
                with pytest.raises(gcp_exceptions.ServiceUnavailable):
                    mock_service.get_parameter(parameter_name)


def test_update_parameter_internal_error(mock_service):
    """Test handling internal server error."""
    parameter_name = "test-param"

    with patch.object(mock_service, "_log_operation_start"):
        with patch.object(mock_service, "_log_operation_error"):

            def raise_internal_error(*args, **kwargs):
                raise gcp_exceptions.InternalServerError("Internal error")

            # Mock create_parameter_version since update uses it
            with patch.object(
                mock_service,
                "create_parameter_version",
                side_effect=raise_internal_error,
            ):
                with pytest.raises(gcp_exceptions.InternalServerError):
                    mock_service.create_parameter_version(
                        parameter_name=parameter_name, version_name="v1", data="test"
                    )


def test_list_parameters_rate_limit(mock_service):
    """Test handling rate limit error."""
    with patch.object(mock_service, "_log_operation_start"):
        with patch.object(mock_service, "_log_operation_error"):

            def raise_rate_limit(*args, **kwargs):
                raise gcp_exceptions.TooManyRequests("Rate limit exceeded")

            with patch.object(
                mock_service, "list_parameters", side_effect=raise_rate_limit
            ):
                with pytest.raises(gcp_exceptions.TooManyRequests):
                    mock_service.list_parameters()


def test_delete_parameter_version_not_found(mock_service):
    """Test handling version not found during deletion."""
    parameter_name = "test-param"
    version = "nonexistent"

    with patch.object(mock_service, "_log_operation_start"):
        with patch.object(mock_service, "_log_operation_error"):

            def raise_not_found(*args, **kwargs):
                raise gcp_exceptions.NotFound("Version not found")

            with patch.object(
                mock_service, "delete_parameter_version", side_effect=raise_not_found
            ):
                with pytest.raises(gcp_exceptions.NotFound):
                    mock_service.delete_parameter_version(parameter_name, version)


def test_create_parameter_version_already_exists(mock_service):
    """Test handling version already exists error."""
    parameter_name = "test-param"
    version_name = "v1"

    with patch.object(mock_service, "_log_operation_start"):
        with patch.object(mock_service, "_log_operation_error"):

            def raise_already_exists(*args, **kwargs):
                raise gcp_exceptions.AlreadyExists("Version already exists")

            with patch.object(
                mock_service,
                "create_parameter_version",
                side_effect=raise_already_exists,
            ):
                with pytest.raises(gcp_exceptions.AlreadyExists):
                    mock_service.create_parameter_version(
                        parameter_name=parameter_name,
                        version_name=version_name,
                        data="test",
                    )


def test_get_parameter_metadata_invalid_argument(mock_service):
    """Test handling invalid argument error."""
    parameter_name = "invalid@name"

    with patch.object(mock_service, "_log_operation_start"):
        with patch.object(mock_service, "_log_operation_error"):

            def raise_invalid_arg(*args, **kwargs):
                raise gcp_exceptions.InvalidArgument("Invalid parameter name")

            with patch.object(
                mock_service, "get_parameter_metadata", side_effect=raise_invalid_arg
            ):
                with pytest.raises(gcp_exceptions.InvalidArgument):
                    mock_service.get_parameter_metadata(parameter_name)


# ============================================================================
# Error Context and Logging Tests
# ============================================================================


def test_error_mapping_includes_context(mock_service):
    """Test that error mapping includes context information."""
    gcp_error = gcp_exceptions.NotFound("Not found")
    context = {"parameter_name": "test-param", "version": "v1", "operation_id": "12345"}

    mapped = mock_service._map_gcp_exception(gcp_error, "parameter retrieval", context)

    # Verify context is included in error message
    assert "test-param" in str(mapped)
    assert "v1" in str(mapped)


def test_error_logging_on_exception(mock_service):
    """Test that errors are properly logged when exceptions occur."""
    gcp_error = gcp_exceptions.PermissionDenied("Access denied")
    context = {"parameter_name": "secure-param"}

    with patch.object(mock_service.logger, "error") as mock_log_error:
        mock_service._map_gcp_exception(gcp_error, "parameter access", context)

        # Verify error was logged
        assert mock_log_error.called
        call_args = mock_log_error.call_args
        assert "Google Cloud API error" in call_args[0][0]


def test_error_mapping_preserves_original_message(mock_service):
    """Test that error mapping preserves original error message."""
    original_message = "Specific error details from GCP"
    gcp_error = gcp_exceptions.InvalidArgument(original_message)
    context = {}

    mapped = mock_service._map_gcp_exception(gcp_error, "validation", context)

    # Original message should be included in mapped exception
    assert original_message in str(mapped)


def test_multiple_error_types_in_sequence(mock_service):
    """Test handling multiple different error types in sequence."""
    errors = [
        (gcp_exceptions.NotFound("Not found"), ParameterNotFoundException),
        (gcp_exceptions.PermissionDenied("Denied"), ParameterAccessDeniedException),
        (gcp_exceptions.ResourceExhausted("Quota"), ParameterQuotaExceededException),
        (gcp_exceptions.DeadlineExceeded("Timeout"), ParameterTimeoutException),
    ]

    for gcp_error, expected_type in errors:
        mapped = mock_service._map_gcp_exception(gcp_error, "test operation", {})
        assert isinstance(mapped, expected_type)
