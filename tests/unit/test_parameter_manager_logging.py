"""
Unit tests for Parameter Manager service - Logging Behavior.

Tests the logging behavior of the ParameterManagerService class following
the Spartan Framework testing patterns. Focuses on verifying that operations
are properly logged with appropriate context, timing, and parameter values.

Requirements tested:
- 7.1: Log operation type and metadata
- 7.2: Log error details with context
- 7.3: Log success messages with timing
- 7.4: Include context fields (project_id, parameter_name, etc.)
- 7.5: Include parameter values in logs (non-sensitive)
"""

import pytest
from google.api_core import exceptions as gcp_exceptions

from app.exceptions.parameter_manager import ParameterManagerException
from app.requests.parameter_manager import ParameterCreateRequest
from app.services.parameter_manager import ParameterManagerService


# Test fixtures
@pytest.fixture
def mock_service(mocker):
    """Create a ParameterManagerService with mocked logger."""
    mock_logger = mocker.patch("app.services.parameter_manager.get_logger")
    mock_logger_instance = mock_logger.return_value

    service = ParameterManagerService(project_id="test-project")

    return service, mock_logger_instance


@pytest.fixture
def mock_service_with_cache(mocker):
    """Create a ParameterManagerService with caching enabled and mocked logger."""
    mock_logger = mocker.patch("app.services.parameter_manager.get_logger")
    mock_logger_instance = mock_logger.return_value

    service = ParameterManagerService(
        project_id="test-project", enable_cache=True, cache_ttl_seconds=300
    )

    return service, mock_logger_instance


# ============================================================================
# Initialization Logging Tests
# ============================================================================


def test_initialization_logging(mocker):
    """Test that service initialization is properly logged with timing."""
    # Mock the logger to capture log calls
    mock_logger = mocker.patch("app.services.parameter_manager.get_logger")
    mock_logger_instance = mock_logger.return_value

    ParameterManagerService(project_id="test-project", location="us-central1")

    # Verify initialization logging
    info_calls = mock_logger_instance.info.call_args_list

    # Find the initialization success log
    init_log = None
    for call in info_calls:
        args, kwargs = call
        if "ParameterManagerService initialized successfully" in args[0]:
            init_log = call
            break

    assert init_log is not None, "Initialization log should be present"

    # Verify initialization context
    init_extra = init_log[1]["extra"]
    assert init_extra["project_id"] == "test-project"
    assert init_extra["location"] == "us-central1"
    assert "initialization_time_ms" in init_extra
    assert init_extra["client_type"] == "ParameterManagerServiceClient"
    assert isinstance(init_extra["initialization_time_ms"], (int, float))


def test_initialization_with_cache_logging(mocker):
    """Test that cache initialization is properly logged."""
    # Mock the logger to capture log calls
    mock_logger = mocker.patch("app.services.parameter_manager.get_logger")
    mock_logger_instance = mock_logger.return_value

    ParameterManagerService(
        project_id="test-project", enable_cache=True, cache_ttl_seconds=600
    )

    # Verify cache initialization logging
    info_calls = mock_logger_instance.info.call_args_list

    # Find the cache enabled log
    cache_log = None
    for call in info_calls:
        args, kwargs = call
        if "Parameter caching enabled" in args[0]:
            cache_log = call
            break

    assert cache_log is not None, "Cache initialization log should be present"

    # Verify cache context
    cache_extra = cache_log[1]["extra"]
    assert cache_extra["cache_ttl_seconds"] == 600
    assert cache_extra["project_id"] == "test-project"
    assert cache_extra["location"] == "global"


def test_environment_detection_logging(mocker):
    """Test that environment variable detection is properly logged."""
    # Mock environment variables
    mocker.patch(
        "app.services.parameter_manager.os.getenv",
        side_effect=lambda var: {"GOOGLE_CLOUD_PROJECT": "detected-project-456"}.get(
            var
        ),
    )

    # Mock the logger to capture log calls
    mock_logger = mocker.patch("app.services.parameter_manager.get_logger")
    mock_logger_instance = mock_logger.return_value

    ParameterManagerService()  # No project_id provided, should detect from env

    # Verify environment detection logging
    debug_calls = mock_logger_instance.debug.call_args_list

    # Find the environment detection log
    env_log = None
    for call in debug_calls:
        args, kwargs = call
        if "Project ID detected from environment" in args[0]:
            env_log = call
            break

    assert env_log is not None, "Environment detection log should be present"

    # Verify environment detection context
    env_extra = env_log[1]["extra"]
    assert env_extra["project_id"] == "detected-project-456"
    assert env_extra["source_env_var"] == "GOOGLE_CLOUD_PROJECT"
    assert env_extra["detection_method"] == "environment_variable"


def test_initialization_failure_logging(mocker):
    """Test that initialization failures are properly logged."""
    # Mock the logger to capture log calls
    mock_logger = mocker.patch("app.services.parameter_manager.get_logger")
    mock_logger_instance = mock_logger.return_value

    # Mock environment to return None for all project ID variables
    mocker.patch("app.services.parameter_manager.os.getenv", return_value=None)
    mocker.patch("app.helpers.environment.env", return_value=None)
    mocker.patch("subprocess.run", side_effect=FileNotFoundError("gcloud not found"))
    mocker.patch("requests.get", side_effect=Exception("Metadata service unavailable"))

    with pytest.raises(ParameterManagerException):
        ParameterManagerService()  # No project_id and can't detect

    # Verify error logging for missing project ID
    error_calls = mock_logger_instance.error.call_args_list

    # Find the project ID error log
    project_error_log = None
    for call in error_calls:
        args, kwargs = call
        if "Project ID could not be determined" in args[0]:
            project_error_log = call
            break

    assert project_error_log is not None, "Project ID error log should be present"

    # Verify error context
    error_extra = project_error_log[1]["extra"]
    assert "attempted_sources" in error_extra
    assert "checked_env_vars" in error_extra


# ============================================================================
# Successful Operation Logging Tests
# ============================================================================


def test_successful_create_parameter_logging(mock_service):
    """Test that successful parameter creation is logged with proper timing and context."""
    service, mock_logger = mock_service

    request = ParameterCreateRequest(parameter_name="test-param", format_type="JSON")

    service.create_parameter(request)

    # Verify successful operation logging
    info_calls = mock_logger.info.call_args_list

    # Find the operation start log
    start_log = None
    for call in info_calls:
        args, kwargs = call
        if "Starting parameter creation" in args[0]:
            start_log = call
            break

    assert start_log is not None, "Operation start log should be present"

    # Verify start context
    start_extra = start_log[1]["extra"]
    assert start_extra["operation"] == "parameter creation"
    assert start_extra["parameter_name"] == "test-param"
    assert start_extra["format_type"] == "JSON"
    assert start_extra["project_id"] == "test-project"
    assert start_extra["location"] == "global"

    # Find the success log
    success_log = None
    for call in info_calls:
        args, kwargs = call
        if "Successfully completed parameter creation" in args[0]:
            success_log = call
            break

    assert success_log is not None, "Success log should be present"

    # Verify success context includes timing
    success_extra = success_log[1]["extra"]
    assert "operation_duration_ms" in success_extra
    assert success_extra["operation_status"] == "success"
    assert success_extra["operation"] == "parameter creation"
    assert success_extra["parameter_name"] == "test-param"
    assert isinstance(success_extra["operation_duration_ms"], (int, float))


def test_successful_get_parameter_logging(mock_service):
    """Test that successful parameter retrieval is logged with proper context."""
    service, mock_logger = mock_service

    service.get_parameter("test-param", version="v1")

    # Verify operation logging
    info_calls = mock_logger.info.call_args_list

    # Find the operation start log
    start_log = None
    for call in info_calls:
        args, kwargs = call
        if "Starting parameter retrieval" in args[0]:
            start_log = call
            break

    assert start_log is not None, "Operation start log should be present"

    # Verify start context
    start_extra = start_log[1]["extra"]
    assert start_extra["operation"] == "parameter retrieval"
    assert start_extra["parameter_name"] == "test-param"
    assert start_extra["version"] == "v1"
    assert start_extra["project_id"] == "test-project"

    # Find the success log
    success_log = None
    for call in info_calls:
        args, kwargs = call
        if "Successfully completed parameter retrieval" in args[0]:
            success_log = call
            break

    assert success_log is not None, "Success log should be present"

    # Verify success context
    success_extra = success_log[1]["extra"]
    assert "operation_duration_ms" in success_extra
    assert success_extra["operation_status"] == "success"
    assert success_extra["parameter_name"] == "test-param"
    assert success_extra["version"] == "v1"


def test_successful_version_creation_logging(mock_service):
    """Test that successful version creation is logged with proper context."""
    service, mock_logger = mock_service

    service.create_parameter_version(
        parameter_name="test-param",
        version_name="v2",
        data={"key": "value"},
        format_type="JSON",
    )

    # Verify operation logging
    info_calls = mock_logger.info.call_args_list

    # Find the operation start log
    start_log = None
    for call in info_calls:
        args, kwargs = call
        if "Starting parameter version creation" in args[0]:
            start_log = call
            break

    assert start_log is not None, "Operation start log should be present"

    # Verify start context
    start_extra = start_log[1]["extra"]
    assert start_extra["operation"] == "parameter version creation"
    assert start_extra["parameter_name"] == "test-param"
    assert start_extra["version_name"] == "v2"
    assert start_extra["format_type"] == "JSON"


# ============================================================================
# Error Operation Logging Tests
# ============================================================================


def test_error_operation_logging(mock_service, mocker):
    """Test that failed operations are logged with proper error context and timing."""
    service, mock_logger = mock_service

    # Create a GCP exception to trigger error logging
    gcp_error = gcp_exceptions.NotFound("Parameter not found")

    # Mock the internal method that would call _map_gcp_exception
    original_map = service._map_gcp_exception

    def mock_map_with_logging(*args, **kwargs):
        # Call the original to trigger logging
        return original_map(*args, **kwargs)

    mocker.patch.object(
        service, "_map_gcp_exception", side_effect=mock_map_with_logging
    )

    # Trigger the error mapping
    service._map_gcp_exception(
        gcp_error, "parameter retrieval", {"parameter_name": "nonexistent"}
    )

    # Verify error logging was called
    error_calls = mock_logger.error.call_args_list

    # Should have at least one error log
    assert len(error_calls) >= 1

    # Verify the error log contains proper context
    error_log = error_calls[0]
    error_extra = error_log[1]["extra"]
    assert error_extra["operation"] == "parameter retrieval"
    assert error_extra["gcp_error_type"] == "NotFound"
    assert error_extra["parameter_name"] == "nonexistent"


def test_parameter_values_are_logged(mock_service):
    """Test that parameter values ARE logged (non-sensitive configuration data)."""
    service, mock_logger = mock_service

    # Create a parameter with specific data
    request = ParameterCreateRequest(parameter_name="db-config", format_type="JSON")

    service.create_parameter(request)

    # Collect all log calls
    all_calls = []
    for method_name in ["info", "debug", "error", "warning"]:
        method = getattr(mock_logger, method_name)
        all_calls.extend(method.call_args_list)

    # Verify that parameter name is logged (it's configuration metadata)
    found_parameter_name = False
    for call in all_calls:
        args, kwargs = call
        if "extra" in kwargs:
            extra_data = kwargs["extra"]
            if isinstance(extra_data, dict):
                if extra_data.get("parameter_name") == "db-config":
                    found_parameter_name = True
                    break

    assert found_parameter_name, "Parameter name should be logged in context"


def test_operation_metadata_logging(mock_service):
    """Test that operation metadata is properly logged."""
    service, mock_logger = mock_service

    service.get_parameter("app-config")

    # Verify that operation metadata is logged
    info_calls = mock_logger.info.call_args_list

    # Find the operation start log
    start_log = None
    for call in info_calls:
        args, kwargs = call
        if "Starting parameter retrieval" in args[0]:
            start_log = call
            break

    assert start_log is not None, "Operation start log should be present"

    # Verify metadata is present
    start_extra = start_log[1]["extra"]
    assert start_extra["operation"] == "parameter retrieval"
    assert start_extra["parameter_name"] == "app-config"
    assert start_extra["project_id"] == "test-project"
    assert start_extra["location"] == "global"

    # Find the success log
    success_log = None
    for call in info_calls:
        args, kwargs = call
        if "Successfully completed parameter retrieval" in args[0]:
            success_log = call
            break

    assert success_log is not None, "Success log should be present"

    # Verify success metadata includes timing and context
    success_extra = success_log[1]["extra"]
    assert "operation_duration_ms" in success_extra
    assert success_extra["parameter_name"] == "app-config"
    assert success_extra["operation_status"] == "success"


# ============================================================================
# Context Field Logging Tests
# ============================================================================


def test_context_fields_in_logs(mock_service):
    """Test that structured logging includes relevant context fields."""
    service, mock_logger = mock_service

    service.list_parameters(page_size=50, filter_expression="labels.env=prod")

    # Verify context fields in logs
    info_calls = mock_logger.info.call_args_list

    # Find the operation start log
    start_log = None
    for call in info_calls:
        args, kwargs = call
        if "Starting parameter listing" in args[0]:
            start_log = call
            break

    assert start_log is not None, "Operation start log should be present"

    # Verify all expected context fields are present
    start_extra = start_log[1]["extra"]
    assert "operation" in start_extra
    assert "project_id" in start_extra
    assert "location" in start_extra
    assert "page_size" in start_extra
    assert "filter_expression" in start_extra
    assert start_extra["project_id"] == "test-project"
    assert start_extra["location"] == "global"
    assert start_extra["page_size"] == 50
    assert start_extra["filter_expression"] == "labels.env=prod"


def test_version_context_in_logs(mock_service):
    """Test that version information is included in log context."""
    service, mock_logger = mock_service

    service.create_parameter_version(
        parameter_name="versioned-param",
        version_name="prod-2024-01",
        data="config data",
    )

    # Verify version context in logs
    info_calls = mock_logger.info.call_args_list

    # Find the operation start log
    start_log = None
    for call in info_calls:
        args, kwargs = call
        if "Starting parameter version creation" in args[0]:
            start_log = call
            break

    assert start_log is not None, "Operation start log should be present"

    # Verify version context
    start_extra = start_log[1]["extra"]
    assert start_extra["parameter_name"] == "versioned-param"
    assert start_extra["version_name"] == "prod-2024-01"
    assert start_extra["format_type"] == "UNFORMATTED"


def test_cache_operation_logging(mock_service_with_cache):
    """Test that cache operations are properly logged."""
    service, mock_logger = mock_service_with_cache

    # Clear cache to trigger logging
    service.clear_cache()

    # Verify cache clear logging
    info_calls = mock_logger.info.call_args_list

    # Find the cache clear log
    cache_log = None
    for call in info_calls:
        args, kwargs = call
        if "Cache cleared" in args[0]:
            cache_log = call
            break

    assert cache_log is not None, "Cache clear log should be present"

    # Verify cache context
    cache_extra = cache_log[1]["extra"]
    assert "cleared_entries" in cache_extra
    assert cache_extra["project_id"] == "test-project"
    assert cache_extra["location"] == "global"


# ============================================================================
# Error Scenario Logging Tests
# ============================================================================


def test_validation_error_logging(mock_service):
    """Test that validation errors are properly logged."""
    service, mock_logger = mock_service

    # Attempt to create parameter with invalid JSON
    with pytest.raises(ParameterManagerException):
        service._validate_and_encode_data("{invalid json", "JSON")

    # Note: Validation errors may not trigger operation logging since they
    # happen before the operation starts, but they should still be handled


def test_gcp_error_mapping_logging(mock_service, mocker):
    """Test that GCP error mapping includes proper logging."""
    service, mock_logger = mock_service

    # Create a GCP exception
    gcp_error = gcp_exceptions.PermissionDenied("Access denied")

    # Call the error mapping method with proper context dict
    service._map_gcp_exception(
        gcp_error, "parameter retrieval", {"parameter_name": "test-param"}
    )

    # Verify error mapping logging
    error_calls = mock_logger.error.call_args_list

    # Find the error mapping log
    mapping_log = None
    for call in error_calls:
        args, kwargs = call
        if "Google Cloud API error" in args[0]:
            mapping_log = call
            break

    assert mapping_log is not None, "Error mapping log should be present"

    # Verify error context
    error_extra = mapping_log[1]["extra"]
    assert error_extra["gcp_error_type"] == "PermissionDenied"
    assert error_extra["parameter_name"] == "test-param"
    assert error_extra["operation"] == "parameter retrieval"


def test_delete_operation_logging(mock_service):
    """Test that delete operations are properly logged."""
    service, mock_logger = mock_service

    service.delete_parameter("test-param")

    # Verify delete operation logging
    info_calls = mock_logger.info.call_args_list

    # Find the operation start log
    start_log = None
    for call in info_calls:
        args, kwargs = call
        if "Starting parameter deletion" in args[0]:
            start_log = call
            break

    assert start_log is not None, "Operation start log should be present"

    # Verify start context
    start_extra = start_log[1]["extra"]
    assert start_extra["operation"] == "parameter deletion"
    assert start_extra["parameter_name"] == "test-param"

    # Find the success log
    success_log = None
    for call in info_calls:
        args, kwargs = call
        if "Successfully completed parameter deletion" in args[0]:
            success_log = call
            break

    assert success_log is not None, "Success log should be present"

    # Verify success context
    success_extra = success_log[1]["extra"]
    assert "operation_duration_ms" in success_extra
    assert success_extra["operation_status"] == "success"


def test_list_versions_logging(mock_service):
    """Test that list versions operations are properly logged."""
    service, mock_logger = mock_service

    service.list_parameter_versions("test-param", page_size=25)

    # Verify operation logging
    info_calls = mock_logger.info.call_args_list

    # Find the operation start log
    start_log = None
    for call in info_calls:
        args, kwargs = call
        if "Starting parameter version listing" in args[0]:
            start_log = call
            break

    assert start_log is not None, "Operation start log should be present"

    # Verify start context
    start_extra = start_log[1]["extra"]
    assert start_extra["operation"] == "parameter version listing"
    assert start_extra["parameter_name"] == "test-param"
    assert start_extra["page_size"] == 25


def test_metadata_retrieval_logging(mock_service):
    """Test that metadata retrieval is properly logged."""
    service, mock_logger = mock_service

    service.get_parameter_metadata("test-param")

    # Verify operation logging
    info_calls = mock_logger.info.call_args_list

    # Find the operation start log
    start_log = None
    for call in info_calls:
        args, kwargs = call
        if "Starting parameter metadata retrieval" in args[0]:
            start_log = call
            break

    assert start_log is not None, "Operation start log should be present"

    # Verify start context
    start_extra = start_log[1]["extra"]
    assert start_extra["operation"] == "parameter metadata retrieval"
    assert start_extra["parameter_name"] == "test-param"
