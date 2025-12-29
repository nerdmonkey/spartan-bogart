# Unit tests for Secret Manager service
# This file will contain tests for the SecretManagerService class

import pytest

from app.services.secret_manager import SecretManagerService


def test_secret_manager_service_initialization(mocker):
    """Test SecretManagerService initialization."""
    # Mock the Secret Manager client
    mock_client = mocker.patch(
        "app.services.secret_manager.secretmanager.SecretManagerServiceClient"
    )
    # Mock environment to return project ID
    mocker.patch(
        "app.services.secret_manager.os.getenv", return_value="test-project-123"
    )

    service = SecretManagerService()
    assert service.project_id == "test-project-123"
    assert service.client is not None
    assert service.logger is not None
    mock_client.assert_called_once()


def test_secret_manager_service_initialization_with_project_id(mocker):
    """Test SecretManagerService initialization with project ID."""
    # Mock the Secret Manager client
    mock_client = mocker.patch(
        "app.services.secret_manager.secretmanager.SecretManagerServiceClient"
    )

    project_id = "test-project-123"
    service = SecretManagerService(project_id=project_id)
    assert service.project_id == project_id
    assert service.client is not None
    assert service.logger is not None
    mock_client.assert_called_once()


def test_secret_manager_service_initialization_no_project_id(mocker):
    """Test SecretManagerService initialization fails without project ID."""
    # Mock environment to return None (no project ID)
    mocker.patch("app.services.secret_manager.os.getenv", return_value=None)
    # Mock framework environment to return None
    mocker.patch("app.helpers.environment.env", return_value=None)
    # Mock subprocess to fail
    mocker.patch("subprocess.run", side_effect=FileNotFoundError("gcloud not found"))
    # Mock requests to fail
    mocker.patch("requests.get", side_effect=Exception("Metadata service unavailable"))

    from app.exceptions.secret_manager import SecretManagerException

    with pytest.raises(
        SecretManagerException,
        match="Project ID must be provided or available in environment",
    ):
        SecretManagerService()


def test_secret_manager_service_methods_exist(mocker):
    """Test that all required methods exist on the service."""
    # Mock the Secret Manager client
    mocker.patch("app.services.secret_manager.secretmanager.SecretManagerServiceClient")
    # Mock environment to return project ID
    mocker.patch(
        "app.services.secret_manager.os.getenv", return_value="test-project-123"
    )

    service = SecretManagerService()

    # Check that all required methods exist
    assert hasattr(service, "create_secret")
    assert hasattr(service, "get_secret")
    assert hasattr(service, "list_secrets")
    assert hasattr(service, "delete_secret")
    assert hasattr(service, "add_secret_version")
    assert hasattr(service, "list_secret_versions")
    assert hasattr(service, "disable_secret_version")
    assert hasattr(service, "enable_secret_version")
    assert hasattr(service, "destroy_secret_version")
    assert hasattr(service, "get_secret_metadata")

    # Check that methods are callable
    assert callable(service.create_secret)
    assert callable(service.get_secret)
    assert callable(service.list_secrets)
    assert callable(service.delete_secret)
    assert callable(service.add_secret_version)
    assert callable(service.list_secret_versions)
    assert callable(service.disable_secret_version)
    assert callable(service.enable_secret_version)
    assert callable(service.destroy_secret_version)
    assert callable(service.get_secret_metadata)


# Error handling unit tests
def test_secret_not_found_error_mapping(mocker):
    """Test that NotFound errors are properly mapped to SecretNotFoundException."""
    from google.api_core import exceptions as gcp_exceptions

    from app.exceptions.secret_manager import SecretVersionNotFoundException

    # Mock the Secret Manager client
    mock_client = mocker.patch(
        "app.services.secret_manager.secretmanager.SecretManagerServiceClient"
    )
    mock_client_instance = mock_client.return_value
    mock_client_instance.access_secret_version.side_effect = gcp_exceptions.NotFound(
        "Secret not found"
    )

    service = SecretManagerService(project_id="test-project")

    # For version-specific requests, we expect SecretVersionNotFoundException
    with pytest.raises(SecretVersionNotFoundException) as exc_info:
        service.get_secret("nonexistent-secret")

    assert "not found" in str(exc_info.value).lower()
    assert "nonexistent-secret" in str(exc_info.value)


def test_secret_not_found_for_metadata(mocker):
    """Test that NotFound errors are properly mapped to SecretNotFoundException for metadata requests."""
    from google.api_core import exceptions as gcp_exceptions

    from app.exceptions.secret_manager import SecretNotFoundException

    # Mock the Secret Manager client
    mock_client = mocker.patch(
        "app.services.secret_manager.secretmanager.SecretManagerServiceClient"
    )
    mock_client_instance = mock_client.return_value
    mock_client_instance.get_secret.side_effect = gcp_exceptions.NotFound(
        "Secret not found"
    )

    service = SecretManagerService(project_id="test-project")

    # For metadata requests (no version), we expect SecretNotFoundException
    with pytest.raises(SecretNotFoundException) as exc_info:
        service.get_secret_metadata("nonexistent-secret")

    assert "not found" in str(exc_info.value).lower()
    assert "nonexistent-secret" in str(exc_info.value)


def test_permission_denied_error_mapping(mocker):
    """Test that PermissionDenied errors are properly mapped to SecretAccessDeniedException."""
    from google.api_core import exceptions as gcp_exceptions

    from app.exceptions.secret_manager import SecretAccessDeniedException

    # Mock the Secret Manager client
    mock_client = mocker.patch(
        "app.services.secret_manager.secretmanager.SecretManagerServiceClient"
    )
    mock_client_instance = mock_client.return_value
    mock_client_instance.access_secret_version.side_effect = (
        gcp_exceptions.PermissionDenied("Permission denied")
    )

    service = SecretManagerService(project_id="test-project")

    with pytest.raises(SecretAccessDeniedException) as exc_info:
        service.get_secret("restricted-secret")

    assert "permission denied" in str(exc_info.value).lower()
    assert "restricted-secret" in str(exc_info.value)


def test_quota_exceeded_error_mapping(mocker):
    """Test that ResourceExhausted errors are properly mapped to SecretQuotaExceededException."""
    from google.api_core import exceptions as gcp_exceptions

    from app.exceptions.secret_manager import SecretQuotaExceededException

    # Mock the Secret Manager client
    mock_client = mocker.patch(
        "app.services.secret_manager.secretmanager.SecretManagerServiceClient"
    )
    mock_client_instance = mock_client.return_value
    mock_client_instance.list_secrets.side_effect = gcp_exceptions.ResourceExhausted(
        "Quota exceeded"
    )

    service = SecretManagerService(project_id="test-project")

    with pytest.raises(SecretQuotaExceededException) as exc_info:
        service.list_secrets()

    assert "quota exceeded" in str(exc_info.value).lower()


def test_timeout_error_mapping(mocker):
    """Test that DeadlineExceeded errors are properly mapped to SecretTimeoutException."""
    from google.api_core import exceptions as gcp_exceptions

    from app.exceptions.secret_manager import SecretTimeoutException

    # Mock the Secret Manager client
    mock_client = mocker.patch(
        "app.services.secret_manager.secretmanager.SecretManagerServiceClient"
    )
    mock_client_instance = mock_client.return_value
    mock_client_instance.access_secret_version.side_effect = (
        gcp_exceptions.DeadlineExceeded("Request timed out")
    )

    service = SecretManagerService(project_id="test-project")

    with pytest.raises(SecretTimeoutException) as exc_info:
        service.get_secret("slow-secret")

    assert "timed out" in str(exc_info.value).lower()


def test_service_unavailable_error_mapping(mocker):
    """Test that ServiceUnavailable errors are properly mapped to SecretUnavailableException."""
    from google.api_core import exceptions as gcp_exceptions

    from app.exceptions.secret_manager import SecretUnavailableException

    # Mock the Secret Manager client
    mock_client = mocker.patch(
        "app.services.secret_manager.secretmanager.SecretManagerServiceClient"
    )
    mock_client_instance = mock_client.return_value
    mock_client_instance.access_secret_version.side_effect = (
        gcp_exceptions.ServiceUnavailable("Service temporarily unavailable")
    )

    service = SecretManagerService(project_id="test-project")

    with pytest.raises(SecretUnavailableException) as exc_info:
        service.get_secret("test-secret")

    assert "unavailable" in str(exc_info.value).lower()


def test_internal_server_error_mapping(mocker):
    """Test that InternalServerError errors are properly mapped to SecretInternalErrorException."""
    from google.api_core import exceptions as gcp_exceptions

    from app.exceptions.secret_manager import SecretInternalErrorException

    # Mock the Secret Manager client
    mock_client = mocker.patch(
        "app.services.secret_manager.secretmanager.SecretManagerServiceClient"
    )
    mock_client_instance = mock_client.return_value
    mock_client_instance.access_secret_version.side_effect = (
        gcp_exceptions.InternalServerError("Internal server error")
    )

    service = SecretManagerService(project_id="test-project")

    with pytest.raises(SecretInternalErrorException) as exc_info:
        service.get_secret("test-secret")

    assert "internal" in str(exc_info.value).lower()


def test_network_connectivity_error_mapping(mocker):
    """Test that network connectivity errors are properly mapped to SecretConnectionException."""
    from app.exceptions.secret_manager import SecretConnectionException

    # Mock the Secret Manager client
    mock_client = mocker.patch(
        "app.services.secret_manager.secretmanager.SecretManagerServiceClient"
    )
    mock_client_instance = mock_client.return_value
    mock_client_instance.access_secret_version.side_effect = ConnectionError(
        "Network connection failed"
    )

    service = SecretManagerService(project_id="test-project")

    with pytest.raises(SecretConnectionException) as exc_info:
        service.get_secret("test-secret")

    assert "connectivity" in str(exc_info.value).lower()


def test_failed_precondition_disabled_version_mapping(mocker):
    """Test that FailedPrecondition errors for disabled versions are properly mapped."""
    from google.api_core import exceptions as gcp_exceptions

    from app.exceptions.secret_manager import SecretVersionNotFoundException

    # Mock the Secret Manager client
    mock_client = mocker.patch(
        "app.services.secret_manager.secretmanager.SecretManagerServiceClient"
    )
    mock_client_instance = mock_client.return_value
    mock_client_instance.access_secret_version.side_effect = (
        gcp_exceptions.FailedPrecondition("Secret version is disabled")
    )

    service = SecretManagerService(project_id="test-project")

    with pytest.raises(SecretVersionNotFoundException) as exc_info:
        service.get_secret("test-secret", version="2")

    assert "not accessible" in str(exc_info.value).lower()
    assert "test-secret" in str(exc_info.value)
    assert "2" in str(exc_info.value)


def test_invalid_argument_error_mapping(mocker):
    """Test that InvalidArgument errors are properly mapped to SecretManagerException."""
    from google.api_core import exceptions as gcp_exceptions

    from app.exceptions.secret_manager import SecretManagerException

    # Mock the Secret Manager client
    mock_client = mocker.patch(
        "app.services.secret_manager.secretmanager.SecretManagerServiceClient"
    )
    mock_client_instance = mock_client.return_value
    mock_client_instance.create_secret.side_effect = gcp_exceptions.InvalidArgument(
        "Invalid secret name format"
    )

    from app.requests.secret_manager import SecretCreateRequest

    service = SecretManagerService(project_id="test-project")
    request = SecretCreateRequest(secret_name="test-secret", secret_value="test-value")

    with pytest.raises(SecretManagerException) as exc_info:
        service.create_secret(request)

    assert "invalid argument" in str(exc_info.value).lower()


def test_already_exists_error_mapping(mocker):
    """Test that AlreadyExists errors are properly mapped to SecretManagerException."""
    from google.api_core import exceptions as gcp_exceptions

    from app.exceptions.secret_manager import SecretManagerException

    # Mock the Secret Manager client
    mock_client = mocker.patch(
        "app.services.secret_manager.secretmanager.SecretManagerServiceClient"
    )
    mock_client_instance = mock_client.return_value
    mock_client_instance.create_secret.side_effect = gcp_exceptions.AlreadyExists(
        "Secret already exists"
    )

    from app.requests.secret_manager import SecretCreateRequest

    service = SecretManagerService(project_id="test-project")
    request = SecretCreateRequest(
        secret_name="existing-secret", secret_value="test-value"
    )

    with pytest.raises(SecretManagerException) as exc_info:
        service.create_secret(request)

    assert "already exists" in str(exc_info.value).lower()
    assert "existing-secret" in str(exc_info.value)


def test_error_context_logging(mocker):
    """Test that error mapping includes proper context logging."""
    from google.api_core import exceptions as gcp_exceptions

    from app.exceptions.secret_manager import SecretVersionNotFoundException

    # Mock the Secret Manager client
    mock_client = mocker.patch(
        "app.services.secret_manager.secretmanager.SecretManagerServiceClient"
    )
    mock_client_instance = mock_client.return_value
    mock_client_instance.access_secret_version.side_effect = gcp_exceptions.NotFound(
        "Secret not found"
    )

    # Mock the logger to capture log calls
    mock_logger = mocker.patch("app.services.secret_manager.get_logger")
    mock_logger_instance = mock_logger.return_value

    service = SecretManagerService(project_id="test-project")

    with pytest.raises(SecretVersionNotFoundException):
        service.get_secret("test-secret", version="1")

    # Verify that error logging was called with proper context
    mock_logger_instance.error.assert_called()

    # Get the call arguments
    call_args = mock_logger_instance.error.call_args
    assert "Google Cloud API error during secret retrieval" in call_args[0][0]

    # Check that extra context was provided
    extra_context = call_args[1]["extra"]
    assert extra_context["operation"] == "secret retrieval"
    assert extra_context["gcp_error_type"] == "NotFound"
    assert extra_context["secret_name"] == "test-secret"
    assert extra_context["version"] == "1"
    assert extra_context["project_id"] == "test-project"


def test_generic_exception_mapping(mocker):
    """Test that unexpected exceptions are properly wrapped in SecretManagerException."""
    from app.exceptions.secret_manager import SecretManagerException

    # Mock the Secret Manager client
    mock_client = mocker.patch(
        "app.services.secret_manager.secretmanager.SecretManagerServiceClient"
    )
    mock_client_instance = mock_client.return_value
    mock_client_instance.access_secret_version.side_effect = ValueError(
        "Unexpected error"
    )

    service = SecretManagerService(project_id="test-project")

    with pytest.raises(SecretManagerException) as exc_info:
        service.get_secret("test-secret")

    assert "unexpected error" in str(exc_info.value).lower()
    assert "secret retrieval" in str(exc_info.value).lower()


def test_client_initialization_failure(mocker):
    """Test that client initialization failures are properly handled."""
    from app.exceptions.secret_manager import SecretManagerException

    # Mock the Secret Manager client to fail during initialization
    mock_client = mocker.patch(
        "app.services.secret_manager.secretmanager.SecretManagerServiceClient"
    )
    mock_client.side_effect = Exception("Failed to initialize client")

    with pytest.raises(SecretManagerException) as exc_info:
        SecretManagerService(project_id="test-project")

    assert "failed to initialize" in str(exc_info.value).lower()


def test_error_mapping_preserves_original_message(mocker):
    """Test that error mapping preserves important details from original exceptions."""
    from google.api_core import exceptions as gcp_exceptions

    from app.exceptions.secret_manager import SecretAccessDeniedException

    original_message = "IAM permission 'secretmanager.versions.access' denied on resource 'projects/test/secrets/my-secret'"

    # Mock the Secret Manager client
    mock_client = mocker.patch(
        "app.services.secret_manager.secretmanager.SecretManagerServiceClient"
    )
    mock_client_instance = mock_client.return_value
    mock_client_instance.access_secret_version.side_effect = (
        gcp_exceptions.PermissionDenied(original_message)
    )

    service = SecretManagerService(project_id="test-project")

    with pytest.raises(SecretAccessDeniedException) as exc_info:
        service.get_secret("my-secret")

    # The mapped exception should include the original detailed message
    exception_message = str(exc_info.value)
    assert "my-secret" in exception_message
    assert "permission denied" in exception_message.lower()


# Logging behavior unit tests
def test_successful_operation_logging(mocker):
    """Test that successful operations are logged with proper timing and context."""
    # Mock the Secret Manager client
    mock_client = mocker.patch(
        "app.services.secret_manager.secretmanager.SecretManagerServiceClient"
    )
    mock_client_instance = mock_client.return_value

    # Mock successful secret creation
    mock_secret = mocker.Mock()
    mock_secret.name = "projects/test-project/secrets/test-secret"
    mock_client_instance.create_secret.return_value = mock_secret

    mock_version = mocker.Mock()
    mock_version.name = "projects/test-project/secrets/test-secret/versions/1"
    mock_client_instance.add_secret_version.return_value = mock_version

    # Mock the logger to capture log calls
    mock_logger = mocker.patch("app.services.secret_manager.get_logger")
    mock_logger_instance = mock_logger.return_value

    service = SecretManagerService(project_id="test-project")

    from app.requests.secret_manager import SecretCreateRequest

    request = SecretCreateRequest(secret_name="test-secret", secret_value="test-value")

    service.create_secret(request)

    # Verify successful operation logging
    mock_logger_instance.info.assert_called()

    # Check for operation start and success logs
    info_calls = mock_logger_instance.info.call_args_list

    # Should have at least initialization, start, and success logs
    assert len(info_calls) >= 2

    # Check that timing information is included in success log
    success_call = None
    for call in info_calls:
        args, kwargs = call
        if "Successfully completed" in args[0]:
            success_call = call
            break

    assert success_call is not None, "Success log should be present"

    # Verify timing information is logged
    success_extra = success_call[1]["extra"]
    assert "operation_duration_ms" in success_extra
    assert "operation_status" in success_extra
    assert success_extra["operation_status"] == "success"
    assert success_extra["operation"] == "secret creation"
    assert success_extra["secret_name"] == "test-secret"
    assert success_extra["project_id"] == "test-project"


def test_error_operation_logging(mocker):
    """Test that failed operations are logged with proper error context and timing."""
    from google.api_core import exceptions as gcp_exceptions

    from app.exceptions.secret_manager import SecretVersionNotFoundException

    # Mock the Secret Manager client
    mock_client = mocker.patch(
        "app.services.secret_manager.secretmanager.SecretManagerServiceClient"
    )
    mock_client_instance = mock_client.return_value
    mock_client_instance.access_secret_version.side_effect = gcp_exceptions.NotFound(
        "Secret not found"
    )

    # Mock the logger to capture log calls
    mock_logger = mocker.patch("app.services.secret_manager.get_logger")
    mock_logger_instance = mock_logger.return_value

    service = SecretManagerService(project_id="test-project")

    with pytest.raises(SecretVersionNotFoundException):
        service.get_secret("nonexistent-secret")

    # Verify error logging was called
    mock_logger_instance.error.assert_called()

    # Check for operation start and error logs
    error_calls = mock_logger_instance.error.call_args_list

    # Should have error mapping log and operation error log
    assert len(error_calls) >= 1

    # Find the operation error log
    operation_error_call = None
    for call in error_calls:
        args, kwargs = call
        if "Failed to complete" in args[0]:
            operation_error_call = call
            break

    assert operation_error_call is not None, "Operation error log should be present"

    # Verify error timing and context information
    error_extra = operation_error_call[1]["extra"]
    assert "operation_duration_ms" in error_extra
    assert "operation_status" in error_extra
    assert error_extra["operation_status"] == "error"
    assert error_extra["operation"] == "secret retrieval"
    assert error_extra["secret_name"] == "nonexistent-secret"
    assert error_extra["project_id"] == "test-project"
    assert "error_type" in error_extra
    assert "error_message" in error_extra


def test_secret_values_never_logged(mocker):
    """Test that secret values are never included in log messages."""
    # Mock the Secret Manager client
    mock_client = mocker.patch(
        "app.services.secret_manager.secretmanager.SecretManagerServiceClient"
    )
    mock_client_instance = mock_client.return_value

    # Mock successful secret creation
    mock_secret = mocker.Mock()
    mock_secret.name = "projects/test-project/secrets/test-secret"
    mock_client_instance.create_secret.return_value = mock_secret

    mock_version = mocker.Mock()
    mock_version.name = "projects/test-project/secrets/test-secret/versions/1"
    mock_client_instance.add_secret_version.return_value = mock_version

    # Mock the logger to capture log calls
    mock_logger = mocker.patch("app.services.secret_manager.get_logger")
    mock_logger_instance = mock_logger.return_value

    service = SecretManagerService(project_id="test-project")

    from app.requests.secret_manager import SecretCreateRequest

    secret_value = "super-secret-password-123"
    request = SecretCreateRequest(secret_name="test-secret", secret_value=secret_value)

    service.create_secret(request)

    # Collect all log calls
    all_calls = []
    for method_name in ["info", "debug", "error", "warning"]:
        method = getattr(mock_logger_instance, method_name)
        all_calls.extend(method.call_args_list)

    # Verify that no log call contains the secret value
    for call in all_calls:
        args, kwargs = call

        # Check main message
        if args:
            message = str(args[0])
            assert (
                secret_value not in message
            ), f"Secret value found in log message: {message}"

        # Check extra context
        if "extra" in kwargs:
            extra_data = kwargs["extra"]
            if isinstance(extra_data, dict):
                # Ensure secret value is not in any field
                for key, value in extra_data.items():
                    str_value = str(value)
                    if key in ["secret_value", "payload", "data"]:
                        assert (
                            value != secret_value
                        ), f"Secret value found in prohibited log field '{key}'"
                    # For other fields, check that the secret value isn't accidentally included
                    if (
                        len(secret_value) >= 10
                    ):  # Only check for reasonably long values to avoid false positives
                        assert (
                            secret_value not in str_value
                        ), f"Secret value found in log field '{key}': {str_value}"


def test_operation_metadata_logging(mocker):
    """Test that operation metadata is properly logged without exposing sensitive data."""
    # Mock the Secret Manager client
    mock_client = mocker.patch(
        "app.services.secret_manager.secretmanager.SecretManagerServiceClient"
    )
    mock_client_instance = mock_client.return_value

    # Mock successful secret retrieval
    mock_access_response = mocker.Mock()
    mock_access_response.payload.data = b"secret-value"
    mock_access_response.name = "projects/test-project/secrets/test-secret/versions/1"
    mock_client_instance.access_secret_version.return_value = mock_access_response

    # Mock the logger to capture log calls
    mock_logger = mocker.patch("app.services.secret_manager.get_logger")
    mock_logger_instance = mock_logger.return_value

    service = SecretManagerService(project_id="test-project")

    service.get_secret("test-secret", version="1")

    # Verify that operation metadata is logged
    info_calls = mock_logger_instance.info.call_args_list

    # Find the operation start log
    start_call = None
    for call in info_calls:
        args, kwargs = call
        if "Starting secret retrieval" in args[0]:
            start_call = call
            break

    assert start_call is not None, "Operation start log should be present"

    # Verify metadata is present
    start_extra = start_call[1]["extra"]
    assert start_extra["operation"] == "secret retrieval"
    assert start_extra["secret_name"] == "test-secret"
    assert start_extra["version"] == "1"
    assert start_extra["project_id"] == "test-project"
    assert start_extra["access_type"] == "read"

    # Find the success log
    success_call = None
    for call in info_calls:
        args, kwargs = call
        if "Successfully completed secret retrieval" in args[0]:
            success_call = call
            break

    assert success_call is not None, "Success log should be present"

    # Verify success metadata includes timing and context
    success_extra = success_call[1]["extra"]
    assert "operation_duration_ms" in success_extra
    assert success_extra["secret_name"] == "test-secret"
    assert success_extra["version"] == "1"
    assert "secret_value_length" in success_extra
    assert success_extra["secret_value_length"] == len("secret-value")


def test_debug_logging_for_api_calls(mocker):
    """Test that debug logs are generated for API calls with appropriate context."""
    # Mock the Secret Manager client
    mock_client = mocker.patch(
        "app.services.secret_manager.secretmanager.SecretManagerServiceClient"
    )
    mock_client_instance = mock_client.return_value
    mock_client_instance.delete_secret.return_value = None

    # Mock the logger to capture log calls
    mock_logger = mocker.patch("app.services.secret_manager.get_logger")
    mock_logger_instance = mock_logger.return_value

    service = SecretManagerService(project_id="test-project")

    service.delete_secret("test-secret")

    # Verify debug logging for API calls
    debug_calls = mock_logger_instance.debug.call_args_list

    # Find the API call debug log
    api_call_log = None
    for call in debug_calls:
        args, kwargs = call
        if "Deleting secret from Google Cloud" in args[0]:
            api_call_log = call
            break

    assert api_call_log is not None, "API call debug log should be present"

    # Verify debug context
    debug_extra = api_call_log[1]["extra"]
    assert debug_extra["operation"] == "secret deletion"
    assert debug_extra["secret_name"] == "test-secret"
    assert debug_extra["project_id"] == "test-project"
    assert debug_extra["step"] == "delete_secret_api_call"
    assert "secret_path" in debug_extra


def test_initialization_logging(mocker):
    """Test that service initialization is properly logged with timing."""
    # Mock the Secret Manager client
    mocker.patch("app.services.secret_manager.secretmanager.SecretManagerServiceClient")

    # Mock the logger to capture log calls
    mock_logger = mocker.patch("app.services.secret_manager.get_logger")
    mock_logger_instance = mock_logger.return_value

    SecretManagerService(project_id="test-project")

    # Verify initialization logging
    info_calls = mock_logger_instance.info.call_args_list

    # Find the initialization success log
    init_log = None
    for call in info_calls:
        args, kwargs = call
        if "SecretManagerService initialized successfully" in args[0]:
            init_log = call
            break

    assert init_log is not None, "Initialization log should be present"

    # Verify initialization context
    init_extra = init_log[1]["extra"]
    assert init_extra["project_id"] == "test-project"
    assert "initialization_time_ms" in init_extra
    assert init_extra["client_type"] == "SecretManagerServiceClient"
    assert isinstance(init_extra["initialization_time_ms"], (int, float))


def test_environment_detection_logging(mocker):
    """Test that environment variable detection is properly logged."""
    # Mock environment variables
    mocker.patch(
        "app.services.secret_manager.os.getenv",
        side_effect=lambda var: {"GOOGLE_CLOUD_PROJECT": "detected-project-123"}.get(
            var
        ),
    )

    # Mock the Secret Manager client
    mocker.patch("app.services.secret_manager.secretmanager.SecretManagerServiceClient")

    # Mock the logger to capture log calls
    mock_logger = mocker.patch("app.services.secret_manager.get_logger")
    mock_logger_instance = mock_logger.return_value

    SecretManagerService()  # No project_id provided, should detect from env

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
    assert env_extra["project_id"] == "detected-project-123"
    assert env_extra["source_env_var"] == "GOOGLE_CLOUD_PROJECT"
    assert env_extra["detection_method"] == "environment_variable"


def test_initialization_failure_logging(mocker):
    """Test that initialization failures are properly logged."""
    # Mock the Secret Manager client to fail
    mock_client = mocker.patch(
        "app.services.secret_manager.secretmanager.SecretManagerServiceClient"
    )
    mock_client.side_effect = Exception("Client initialization failed")

    # Mock the logger to capture log calls
    mock_logger = mocker.patch("app.services.secret_manager.get_logger")
    mock_logger_instance = mock_logger.return_value

    from app.exceptions.secret_manager import SecretManagerException

    with pytest.raises(SecretManagerException):
        SecretManagerService(project_id="test-project")

    # Verify error logging for initialization failure
    error_calls = mock_logger_instance.error.call_args_list

    # Find the initialization error log
    init_error_log = None
    for call in error_calls:
        args, kwargs = call
        if "Failed to initialize Secret Manager client" in args[0]:
            init_error_log = call
            break

    assert init_error_log is not None, "Initialization error log should be present"

    # Verify error context
    error_extra = init_error_log[1]["extra"]
    assert error_extra["project_id"] == "test-project"
    assert error_extra["error"] == "Client initialization failed"
    assert error_extra["error_type"] == "Exception"


def test_project_id_missing_logging(mocker):
    """Test that missing project ID is properly logged."""
    # Mock environment to return None for all project ID variables
    mocker.patch("app.services.secret_manager.os.getenv", return_value=None)
    # Mock framework environment to return None
    mocker.patch("app.helpers.environment.env", return_value=None)
    # Mock subprocess to fail
    mocker.patch("subprocess.run", side_effect=FileNotFoundError("gcloud not found"))
    # Mock requests to fail
    mocker.patch("requests.get", side_effect=Exception("Metadata service unavailable"))

    # Mock the logger to capture log calls
    mock_logger = mocker.patch("app.services.secret_manager.get_logger")
    mock_logger_instance = mock_logger.return_value

    from app.exceptions.secret_manager import SecretManagerException

    with pytest.raises(SecretManagerException):
        SecretManagerService()  # No project_id provided and none in environment

    # Verify error logging for missing project ID
    error_calls = mock_logger_instance.error.call_args_list

    init_error_log = None
    for call in error_calls:
        args, kwargs = call
        if "Project ID could not be determined from any source" in args[0]:
            init_error_log = call
            break

    assert init_error_log is not None, "Project ID determination error should be logged"

    # Verify error context includes attempted sources
    error_extra = init_error_log[1]["extra"]
    assert "attempted_sources" in error_extra
    expected_sources = [
        "constructor_parameter",
        "framework_environment",
        "environment_variables",
        "gcloud_config",
        "metadata_service",
    ]
    assert error_extra["attempted_sources"] == expected_sources


# Enhanced initialization unit tests for Requirements 7.1, 7.2, 7.3, 7.4, 7.5
def test_initialization_with_gcp_project_env_var(mocker):
    """Test initialization using GCP_PROJECT environment variable."""
    # Mock environment variables
    mocker.patch(
        "app.services.secret_manager.os.getenv",
        side_effect=lambda var: {"GCP_PROJECT": "gcp-project-456"}.get(var),
    )

    # Mock framework environment to return None
    mocker.patch("app.helpers.environment.env", return_value=None)

    # Mock the Secret Manager client
    mock_client = mocker.patch(
        "app.services.secret_manager.secretmanager.SecretManagerServiceClient"
    )

    # Mock list_secrets for connection test
    mock_list_response = mocker.Mock()
    mock_list_response.secrets = []
    mock_client.return_value.list_secrets.return_value = mock_list_response

    service = SecretManagerService()

    assert service.project_id == "gcp-project-456"


def test_initialization_with_gcloud_config(mocker):
    """Test initialization using gcloud config for project detection."""
    # Mock environment variables to return None
    mocker.patch("app.services.secret_manager.os.getenv", return_value=None)
    # Mock framework environment to return None
    mocker.patch("app.helpers.environment.env", return_value=None)

    # Mock subprocess to return project from gcloud config
    mock_result = mocker.Mock()
    mock_result.returncode = 0
    mock_result.stdout = "gcloud-project-789\n"
    mocker.patch("subprocess.run", return_value=mock_result)

    # Mock the Secret Manager client
    mock_client = mocker.patch(
        "app.services.secret_manager.secretmanager.SecretManagerServiceClient"
    )

    # Mock list_secrets for connection test
    mock_list_response = mocker.Mock()
    mock_list_response.secrets = []
    mock_client.return_value.list_secrets.return_value = mock_list_response

    service = SecretManagerService()

    assert service.project_id == "gcloud-project-789"


def test_initialization_with_metadata_service(mocker):
    """Test initialization using GCP metadata service for project detection."""
    # Mock environment variables to return None
    mocker.patch("app.services.secret_manager.os.getenv", return_value=None)
    # Mock framework environment to return None
    mocker.patch("app.helpers.environment.env", return_value=None)
    # Mock subprocess to fail
    mocker.patch("subprocess.run", side_effect=FileNotFoundError("gcloud not found"))

    # Mock requests to return project from metadata service
    mock_response = mocker.Mock()
    mock_response.status_code = 200
    mock_response.text = "metadata-project-101"
    mocker.patch("requests.get", return_value=mock_response)

    # Mock the Secret Manager client
    mock_client = mocker.patch(
        "app.services.secret_manager.secretmanager.SecretManagerServiceClient"
    )

    # Mock list_secrets for connection test
    mock_list_response = mocker.Mock()
    mock_list_response.secrets = []
    mock_client.return_value.list_secrets.return_value = mock_list_response

    service = SecretManagerService()

    assert service.project_id == "metadata-project-101"


def test_initialization_with_service_account_file(mocker):
    """Test initialization with service account credentials file."""
    import json
    import tempfile

    # Create a temporary service account file
    service_account_data = {
        "type": "service_account",
        "project_id": "sa-project-123",
        "private_key_id": "key_id",
        "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC...\n-----END PRIVATE KEY-----\n",
        "client_email": "test@sa-project-123.iam.gserviceaccount.com",
        "client_id": "123456789",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(service_account_data, f)
        credentials_path = f.name

    try:
        # Mock service account credentials loading
        mock_credentials = mocker.Mock()
        mock_credentials.service_account_email = service_account_data["client_email"]
        mocker.patch(
            "google.oauth2.service_account.Credentials.from_service_account_file",
            return_value=mock_credentials,
        )

        # Mock the Secret Manager client
        mock_client = mocker.patch(
            "app.services.secret_manager.secretmanager.SecretManagerServiceClient"
        )

        # Mock list_secrets for connection test
        mock_list_response = mocker.Mock()
        mock_list_response.secrets = []
        mock_client.return_value.list_secrets.return_value = mock_list_response

        service = SecretManagerService(
            project_id="test-project", credentials_path=credentials_path
        )

        assert service.project_id == "test-project"
        assert service.credentials == mock_credentials
        assert service.client is not None

        # Verify client was initialized with custom credentials
        mock_client.assert_called_once_with(credentials=mock_credentials)

    finally:
        import os

        os.unlink(credentials_path)


def test_initialization_with_credentials_json_string(mocker):
    """Test initialization with service account credentials as JSON string."""
    import json

    service_account_data = {
        "type": "service_account",
        "project_id": "json-project-456",
        "private_key_id": "key_id",
        "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC...\n-----END PRIVATE KEY-----\n",
        "client_email": "test@json-project-456.iam.gserviceaccount.com",
        "client_id": "123456789",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
    }

    credentials_json = json.dumps(service_account_data)

    # Mock service account credentials loading
    mock_credentials = mocker.Mock()
    mock_credentials.service_account_email = service_account_data["client_email"]
    mocker.patch(
        "google.oauth2.service_account.Credentials.from_service_account_info",
        return_value=mock_credentials,
    )

    # Mock the Secret Manager client
    mock_client = mocker.patch(
        "app.services.secret_manager.secretmanager.SecretManagerServiceClient"
    )

    # Mock list_secrets for connection test
    mock_list_response = mocker.Mock()
    mock_list_response.secrets = []
    mock_client.return_value.list_secrets.return_value = mock_list_response

    service = SecretManagerService(
        project_id="test-project", credentials=credentials_json
    )

    assert service.project_id == "test-project"
    assert service.credentials == mock_credentials
    assert service.client is not None


def test_initialization_with_credentials_object(mocker):
    """Test initialization with credentials object."""
    from google.auth.credentials import Credentials

    # Create mock credentials object
    mock_credentials = mocker.Mock(spec=Credentials)

    # Mock the Secret Manager client
    mock_client = mocker.patch(
        "app.services.secret_manager.secretmanager.SecretManagerServiceClient"
    )

    # Mock list_secrets for connection test
    mock_list_response = mocker.Mock()
    mock_list_response.secrets = []
    mock_client.return_value.list_secrets.return_value = mock_list_response

    service = SecretManagerService(
        project_id="test-project", credentials=mock_credentials
    )

    assert service.project_id == "test-project"
    assert service.credentials == mock_credentials
    assert service.client is not None

    # Verify client was initialized with custom credentials
    mock_client.assert_called_once_with(credentials=mock_credentials)


def test_initialization_with_framework_credentials(mocker):
    """Test initialization using framework environment for credentials."""
    # Mock framework environment to return credentials path
    mock_credentials_path = "/path/to/credentials.json"
    mocker.patch(
        "app.helpers.environment.env",
        side_effect=lambda var, default=None: {
            "GOOGLE_APPLICATION_CREDENTIALS": mock_credentials_path
        }.get(var, default),
    )

    # Mock os.path.exists to return True for the credentials path
    mocker.patch("app.services.secret_manager.os.path.exists", return_value=True)

    # Mock service account credentials loading
    mock_credentials = mocker.Mock()
    mock_credentials.service_account_email = (
        "test@framework-creds-project.iam.gserviceaccount.com"
    )
    mocker.patch(
        "app.services.secret_manager.service_account.Credentials.from_service_account_file",
        return_value=mock_credentials,
    )

    # Mock default credentials to ensure framework credentials are used instead
    mocker.patch(
        "app.services.secret_manager.default_credentials",
        side_effect=Exception("Should not use default credentials"),
    )

    # Mock the Secret Manager client
    mock_client = mocker.patch(
        "app.services.secret_manager.secretmanager.SecretManagerServiceClient"
    )

    # Mock list_secrets for connection test
    mock_list_response = mocker.Mock()
    mock_list_response.secrets = []
    mock_client.return_value.list_secrets.return_value = mock_list_response

    service = SecretManagerService(project_id="test-project")

    assert service.project_id == "test-project"
    assert service.credentials == mock_credentials
    assert service.client is not None


def test_initialization_with_default_credentials(mocker):
    """Test initialization using default credentials (ADC)."""
    # Mock google.auth.default to return credentials
    mock_credentials = mocker.Mock()
    mocker.patch(
        "app.services.secret_manager.default_credentials",
        return_value=(mock_credentials, "detected-project"),
    )

    # Mock framework environment to return None (no custom credentials)
    mocker.patch("app.helpers.environment.env", return_value=None)

    # Mock the Secret Manager client
    mock_client = mocker.patch(
        "app.services.secret_manager.secretmanager.SecretManagerServiceClient"
    )

    # Mock list_secrets for connection test
    mock_list_response = mocker.Mock()
    mock_list_response.secrets = []
    mock_client.return_value.list_secrets.return_value = mock_list_response

    service = SecretManagerService(project_id="test-project")

    assert service.project_id == "test-project"
    assert service.credentials == mock_credentials
    assert service.client is not None


def test_initialization_invalid_credentials_file(mocker):
    """Test initialization failure with invalid credentials file path."""
    from app.exceptions.secret_manager import SecretManagerException

    invalid_path = "/nonexistent/path/to/credentials.json"

    with pytest.raises(SecretManagerException) as exc_info:
        SecretManagerService(project_id="test-project", credentials_path=invalid_path)

    assert "Service account key file not found" in str(exc_info.value)
    assert invalid_path in str(exc_info.value)


def test_initialization_invalid_credentials_json(mocker):
    """Test initialization failure with invalid credentials JSON string."""
    from app.exceptions.secret_manager import SecretManagerException

    invalid_json = "invalid json string"

    with pytest.raises(SecretManagerException) as exc_info:
        SecretManagerService(project_id="test-project", credentials=invalid_json)

    assert "Invalid credentials JSON string" in str(exc_info.value)


def test_initialization_invalid_credentials_type(mocker):
    """Test initialization failure with invalid credentials type."""
    from app.exceptions.secret_manager import SecretManagerException

    invalid_credentials = 12345  # Invalid type

    with pytest.raises(SecretManagerException) as exc_info:
        SecretManagerService(project_id="test-project", credentials=invalid_credentials)

    assert "Invalid credentials type" in str(exc_info.value)


def test_initialization_client_authentication_error(mocker):
    """Test initialization failure with authentication error."""
    from google.api_core import exceptions as gcp_exceptions

    from app.exceptions.secret_manager import SecretManagerException

    # Mock the Secret Manager client to raise authentication error
    mock_client = mocker.patch(
        "app.services.secret_manager.secretmanager.SecretManagerServiceClient"
    )
    mock_client.side_effect = gcp_exceptions.Unauthenticated("Authentication failed")

    with pytest.raises(SecretManagerException) as exc_info:
        SecretManagerService(project_id="test-project")

    assert "Authentication failed" in str(exc_info.value)
    assert "credentials" in str(exc_info.value).lower()


def test_initialization_client_permission_denied(mocker):
    """Test initialization failure with permission denied error."""
    from google.api_core import exceptions as gcp_exceptions

    from app.exceptions.secret_manager import SecretManagerException

    # Mock the Secret Manager client to raise permission denied error
    mock_client = mocker.patch(
        "app.services.secret_manager.secretmanager.SecretManagerServiceClient"
    )
    mock_client.side_effect = gcp_exceptions.PermissionDenied("Permission denied")

    with pytest.raises(SecretManagerException) as exc_info:
        SecretManagerService(project_id="test-project")

    assert "Permission denied" in str(exc_info.value)
    assert "test-project" in str(exc_info.value)
    assert "IAM roles" in str(exc_info.value)


def test_initialization_project_not_found(mocker):
    """Test initialization failure when project is not found."""
    from google.api_core import exceptions as gcp_exceptions

    from app.exceptions.secret_manager import SecretManagerException

    # Mock the Secret Manager client
    mock_client = mocker.patch(
        "app.services.secret_manager.secretmanager.SecretManagerServiceClient"
    )

    # Mock list_secrets to raise NotFound for connection test
    mock_client.return_value.list_secrets.side_effect = gcp_exceptions.NotFound(
        "Project not found"
    )

    # Mock PYTEST_CURRENT_TEST to be None so connection test runs
    mocker.patch(
        "app.services.secret_manager.os.getenv",
        side_effect=lambda var: (
            None if var == "PYTEST_CURRENT_TEST" else mocker.DEFAULT
        ),
    )

    with pytest.raises(SecretManagerException) as exc_info:
        SecretManagerService(project_id="nonexistent-project")

    assert "not found" in str(exc_info.value).lower()
    assert "nonexistent-project" in str(exc_info.value)


def test_initialization_connection_test_success(mocker):
    """Test that successful connection test is logged properly."""
    # Mock the Secret Manager client
    mock_client = mocker.patch(
        "app.services.secret_manager.secretmanager.SecretManagerServiceClient"
    )

    # Mock successful list_secrets for connection test
    mock_list_response = mocker.Mock()
    mock_list_response.secrets = []
    mock_client.return_value.list_secrets.return_value = mock_list_response

    # Mock PYTEST_CURRENT_TEST to be None so connection test runs
    mocker.patch(
        "app.services.secret_manager.os.getenv",
        side_effect=lambda var: (
            None if var == "PYTEST_CURRENT_TEST" else mocker.DEFAULT
        ),
    )

    # Mock the logger to capture log calls
    mock_logger = mocker.patch("app.services.secret_manager.get_logger")
    mock_logger_instance = mock_logger.return_value

    SecretManagerService(project_id="test-project")

    # Verify initialization success logging includes connection test
    info_calls = mock_logger_instance.info.call_args_list

    init_log = None
    for call in info_calls:
        args, kwargs = call
        if "SecretManagerService initialized successfully" in args[0]:
            init_log = call
            break

    assert init_log is not None

    # Verify connection test success is logged
    init_extra = init_log[1]["extra"]
    assert init_extra["connection_test"] == "success"


def test_initialization_connection_test_permission_denied(mocker):
    """Test that connection test permission denied is handled gracefully."""
    from google.api_core import exceptions as gcp_exceptions

    # Mock the Secret Manager client
    mock_client = mocker.patch(
        "app.services.secret_manager.secretmanager.SecretManagerServiceClient"
    )

    # Mock list_secrets to raise PermissionDenied for connection test
    mock_client.return_value.list_secrets.side_effect = gcp_exceptions.PermissionDenied(
        "Permission denied for list operation"
    )

    # Mock PYTEST_CURRENT_TEST to be None so connection test runs
    mocker.patch(
        "app.services.secret_manager.os.getenv",
        side_effect=lambda var: (
            None if var == "PYTEST_CURRENT_TEST" else mocker.DEFAULT
        ),
    )

    # Mock the logger to capture log calls
    mock_logger = mocker.patch("app.services.secret_manager.get_logger")
    mock_logger_instance = mock_logger.return_value

    # This should not raise an exception - permission denied on list is not critical for initialization
    SecretManagerService(project_id="test-project")

    # Verify initialization success logging includes connection test warning
    info_calls = mock_logger_instance.info.call_args_list

    init_log = None
    for call in info_calls:
        args, kwargs = call
        if "SecretManagerService initialized successfully" in args[0]:
            init_log = call
            break

    assert init_log is not None

    # Verify connection test permission denied is logged
    init_extra = init_log[1]["extra"]
    assert init_extra["connection_test"] == "permission_denied"
    assert "test_error" in init_extra


def test_initialization_enhanced_logging(mocker):
    """Test that enhanced initialization logging includes all relevant context."""
    # Mock service account credentials
    mock_credentials = mocker.Mock()
    mock_credentials.service_account_email = "test@project.iam.gserviceaccount.com"
    mocker.patch(
        "google.oauth2.service_account.Credentials.from_service_account_info",
        return_value=mock_credentials,
    )

    # Mock the Secret Manager client
    mock_client = mocker.patch(
        "app.services.secret_manager.secretmanager.SecretManagerServiceClient"
    )

    # Mock successful connection test
    mock_list_response = mocker.Mock()
    mock_list_response.secrets = []
    mock_client.return_value.list_secrets.return_value = mock_list_response

    # Mock PYTEST_CURRENT_TEST to be None so connection test runs
    mocker.patch(
        "app.services.secret_manager.os.getenv",
        side_effect=lambda var: (
            None if var == "PYTEST_CURRENT_TEST" else mocker.DEFAULT
        ),
    )

    # Mock the logger to capture log calls
    mock_logger = mocker.patch("app.services.secret_manager.get_logger")
    mock_logger_instance = mock_logger.return_value

    SecretManagerService(
        project_id="test-project",
        credentials='{"type": "service_account", "project_id": "test"}',
    )

    # Verify enhanced initialization logging
    info_calls = mock_logger_instance.info.call_args_list

    init_log = None
    for call in info_calls:
        args, kwargs = call
        if "SecretManagerService initialized successfully" in args[0]:
            init_log = call
            break

    assert init_log is not None

    # Verify enhanced context is logged
    init_extra = init_log[1]["extra"]
    assert init_extra["project_id"] == "test-project"
    assert "initialization_time_ms" in init_extra
    assert init_extra["client_type"] == "SecretManagerServiceClient"
    assert init_extra["credential_source"] == "custom_credentials"
    assert init_extra["credential_type"] == "Mock"
    assert init_extra["connection_test"] == "success"


# Caching functionality unit tests for Requirements 8.1, 8.2, 8.3, 8.4
def test_caching_enabled_initialization(mocker):
    """Test that caching can be enabled during initialization."""
    # Mock the Secret Manager client
    mock_client = mocker.Mock()
    mocker.patch(
        "app.services.secret_manager.secretmanager.SecretManagerServiceClient",
        return_value=mock_client,
    )

    # Mock logger
    mock_logger = mocker.Mock()
    mocker.patch("app.services.secret_manager.get_logger", return_value=mock_logger)

    # Initialize service with caching enabled
    service = SecretManagerService(
        project_id="test-project", enable_cache=True, cache_ttl_seconds=300
    )

    # Verify caching is enabled
    assert service.enable_cache is True
    assert service.cache_ttl_seconds == 300
    assert hasattr(service, "_cache")
    assert isinstance(service._cache, dict)

    # Verify initialization logging includes cache info
    assert any(
        call[0][0] == "Secret caching enabled"
        for call in mock_logger.info.call_args_list
    )


def test_caching_disabled_by_default(mocker):
    """Test that caching is disabled by default."""
    # Mock the Secret Manager client
    mock_client = mocker.Mock()
    mocker.patch(
        "app.services.secret_manager.secretmanager.SecretManagerServiceClient",
        return_value=mock_client,
    )

    # Initialize service without caching parameters
    service = SecretManagerService(project_id="test-project")

    # Verify caching is disabled
    assert service.enable_cache is False


def test_cache_hit_reduces_api_calls(mocker):
    """Test that cache hits reduce API calls."""
    # Mock the Secret Manager client
    mock_client = mocker.Mock()
    mock_access_response = mocker.Mock()
    mock_access_response.payload.data = b"secret-value"
    mock_access_response.name = "projects/test-project/secrets/test-secret/versions/1"
    mock_client.access_secret_version.return_value = mock_access_response

    mocker.patch(
        "app.services.secret_manager.secretmanager.SecretManagerServiceClient",
        return_value=mock_client,
    )

    # Initialize service with caching enabled
    service = SecretManagerService(
        project_id="test-project", enable_cache=True, cache_ttl_seconds=300
    )

    # First access should hit the API
    response1 = service.get_secret("test-secret")
    assert response1.secret_value == "secret-value"
    assert mock_client.access_secret_version.call_count == 1

    # Second access should use cache (no additional API call)
    response2 = service.get_secret("test-secret")
    assert response2.secret_value == "secret-value"
    assert mock_client.access_secret_version.call_count == 1  # Still 1, not 2

    # Verify both responses are identical
    assert response1.secret_name == response2.secret_name
    assert response1.secret_value == response2.secret_value


def test_cache_miss_without_caching(mocker):
    """Test that without caching, every access hits the API."""
    # Mock the Secret Manager client
    mock_client = mocker.Mock()
    mock_access_response = mocker.Mock()
    mock_access_response.payload.data = b"secret-value"
    mock_access_response.name = "projects/test-project/secrets/test-secret/versions/1"
    mock_client.access_secret_version.return_value = mock_access_response

    mocker.patch(
        "app.services.secret_manager.secretmanager.SecretManagerServiceClient",
        return_value=mock_client,
    )

    # Initialize service with caching disabled
    service = SecretManagerService(project_id="test-project", enable_cache=False)

    # Multiple accesses should all hit the API
    service.get_secret("test-secret")
    service.get_secret("test-secret")
    service.get_secret("test-secret")

    # Verify API was called 3 times
    assert mock_client.access_secret_version.call_count == 3


def test_cache_invalidation_on_version_add(mocker):
    """Test that adding a new version invalidates the cache for 'latest'."""
    # Mock the Secret Manager client
    mock_client = mocker.Mock()

    # Mock initial access response
    mock_access_response = mocker.Mock()
    mock_access_response.payload.data = b"old-value"
    mock_access_response.name = "projects/test-project/secrets/test-secret/versions/1"
    mock_client.access_secret_version.return_value = mock_access_response

    # Mock add version response
    mock_version = mocker.Mock()
    mock_version.name = "projects/test-project/secrets/test-secret/versions/2"
    mock_client.add_secret_version.return_value = mock_version

    mocker.patch(
        "app.services.secret_manager.secretmanager.SecretManagerServiceClient",
        return_value=mock_client,
    )

    # Initialize service with caching enabled
    service = SecretManagerService(
        project_id="test-project", enable_cache=True, cache_ttl_seconds=300
    )

    # Access secret to cache it
    service.get_secret("test-secret")
    initial_call_count = mock_client.access_secret_version.call_count

    # Verify it's cached (second access doesn't hit API)
    service.get_secret("test-secret")
    assert mock_client.access_secret_version.call_count == initial_call_count

    # Add a new version (should invalidate cache for "latest")
    from app.requests.secret_manager import SecretVersionCreateRequest

    version_request = SecretVersionCreateRequest(
        secret_name="test-secret", secret_value="new-value"
    )
    service.add_secret_version(version_request)

    # Mock new response for updated secret
    mock_new_access_response = mocker.Mock()
    mock_new_access_response.payload.data = b"new-value"
    mock_new_access_response.name = (
        "projects/test-project/secrets/test-secret/versions/2"
    )
    mock_client.access_secret_version.return_value = mock_new_access_response

    # Next access should hit API again (cache was invalidated)
    service.get_secret("test-secret")
    assert mock_client.access_secret_version.call_count > initial_call_count


def test_cache_invalidation_on_delete(mocker):
    """Test that deleting a secret invalidates all cached versions."""
    # Mock the Secret Manager client
    mock_client = mocker.Mock()

    # Mock access response
    mock_access_response = mocker.Mock()
    mock_access_response.payload.data = b"secret-value"
    mock_access_response.name = "projects/test-project/secrets/test-secret/versions/1"
    mock_client.access_secret_version.return_value = mock_access_response

    # Mock delete response
    mock_client.delete_secret.return_value = None

    mocker.patch(
        "app.services.secret_manager.secretmanager.SecretManagerServiceClient",
        return_value=mock_client,
    )

    # Initialize service with caching enabled
    service = SecretManagerService(
        project_id="test-project", enable_cache=True, cache_ttl_seconds=300
    )

    # Access secret to cache it
    service.get_secret("test-secret", version="1")
    initial_call_count = mock_client.access_secret_version.call_count

    # Verify it's cached
    service.get_secret("test-secret", version="1")
    assert mock_client.access_secret_version.call_count == initial_call_count

    # Delete the secret (should invalidate all cached versions)
    service.delete_secret("test-secret")

    # Next access should hit API again (cache was invalidated)
    service.get_secret("test-secret", version="1")
    assert mock_client.access_secret_version.call_count > initial_call_count


def test_cache_invalidation_on_disable(mocker):
    """Test that disabling a version invalidates that cached version."""
    # Mock the Secret Manager client
    mock_client = mocker.Mock()

    # Mock access response
    mock_access_response = mocker.Mock()
    mock_access_response.payload.data = b"secret-value"
    mock_access_response.name = "projects/test-project/secrets/test-secret/versions/1"
    mock_client.access_secret_version.return_value = mock_access_response

    # Mock disable response
    mock_client.disable_secret_version.return_value = None

    mocker.patch(
        "app.services.secret_manager.secretmanager.SecretManagerServiceClient",
        return_value=mock_client,
    )

    # Initialize service with caching enabled
    service = SecretManagerService(
        project_id="test-project", enable_cache=True, cache_ttl_seconds=300
    )

    # Access secret to cache it
    service.get_secret("test-secret", version="1")
    initial_call_count = mock_client.access_secret_version.call_count

    # Verify it's cached
    service.get_secret("test-secret", version="1")
    assert mock_client.access_secret_version.call_count == initial_call_count

    # Disable the version (should invalidate cache for that version)
    service.disable_secret_version("test-secret", "1")

    # Next access should hit API again (cache was invalidated)
    service.get_secret("test-secret", version="1")
    assert mock_client.access_secret_version.call_count > initial_call_count


def test_cache_stats(mocker):
    """Test that cache statistics are properly reported."""
    # Mock the Secret Manager client
    mock_client = mocker.Mock()
    mocker.patch(
        "app.services.secret_manager.secretmanager.SecretManagerServiceClient",
        return_value=mock_client,
    )

    # Test with caching enabled
    service_with_cache = SecretManagerService(
        project_id="test-project", enable_cache=True, cache_ttl_seconds=300
    )

    stats = service_with_cache.get_cache_stats()
    assert stats["enabled"] is True
    assert stats["size"] == 0  # No entries yet
    assert stats["ttl_seconds"] == 300

    # Test with caching disabled
    service_without_cache = SecretManagerService(
        project_id="test-project", enable_cache=False
    )

    stats_disabled = service_without_cache.get_cache_stats()
    assert stats_disabled["enabled"] is False
    assert stats_disabled["size"] == 0


def test_clear_cache(mocker):
    """Test that cache can be manually cleared."""
    # Mock the Secret Manager client
    mock_client = mocker.Mock()

    # Mock access response
    mock_access_response = mocker.Mock()
    mock_access_response.payload.data = b"secret-value"
    mock_access_response.name = "projects/test-project/secrets/test-secret/versions/1"
    mock_client.access_secret_version.return_value = mock_access_response

    mocker.patch(
        "app.services.secret_manager.secretmanager.SecretManagerServiceClient",
        return_value=mock_client,
    )

    # Initialize service with caching enabled
    service = SecretManagerService(
        project_id="test-project", enable_cache=True, cache_ttl_seconds=300
    )

    # Access secret to cache it
    service.get_secret("test-secret")

    # Verify cache has entries
    stats_before = service.get_cache_stats()
    assert stats_before["size"] > 0

    # Clear cache
    service.clear_cache()

    # Verify cache is empty
    stats_after = service.get_cache_stats()
    assert stats_after["size"] == 0


def test_cache_ttl_behavior(mocker):
    """Test that cache respects TTL settings."""
    from datetime import datetime, timedelta

    # Mock the Secret Manager client
    mock_client = mocker.Mock()

    # Mock access response
    mock_access_response = mocker.Mock()
    mock_access_response.payload.data = b"secret-value"
    mock_access_response.name = "projects/test-project/secrets/test-secret/versions/1"
    mock_client.access_secret_version.return_value = mock_access_response

    mocker.patch(
        "app.services.secret_manager.secretmanager.SecretManagerServiceClient",
        return_value=mock_client,
    )

    # Initialize service with short TTL
    service = SecretManagerService(
        project_id="test-project",
        enable_cache=True,
        cache_ttl_seconds=1,  # 1 second TTL
    )

    # Access secret to cache it
    service.get_secret("test-secret")
    initial_call_count = mock_client.access_secret_version.call_count

    # Immediate access should use cache
    service.get_secret("test-secret")
    assert mock_client.access_secret_version.call_count == initial_call_count

    # Manually expire the cache entry by modifying its expiry time
    cache_key = service._get_cache_key("test-secret", "latest")
    if cache_key in service._cache:
        value, _ = service._cache[cache_key]
        # Set expiry to past
        service._cache[cache_key] = (value, datetime.now() - timedelta(seconds=10))

    # Next access should hit API again (cache expired)
    service.get_secret("test-secret")
    assert mock_client.access_secret_version.call_count > initial_call_count


def test_cache_key_generation(mocker):
    """Test that cache keys are properly generated."""
    # Mock the Secret Manager client
    mock_client = mocker.Mock()
    mocker.patch(
        "app.services.secret_manager.secretmanager.SecretManagerServiceClient",
        return_value=mock_client,
    )

    service = SecretManagerService(project_id="test-project", enable_cache=True)

    # Test cache key generation
    key1 = service._get_cache_key("secret1", "latest")
    key2 = service._get_cache_key("secret1", "1")
    key3 = service._get_cache_key("secret2", "latest")

    # Verify keys are unique for different secrets/versions
    assert key1 != key2
    assert key1 != key3
    assert key2 != key3

    # Verify keys are consistent
    assert key1 == service._get_cache_key("secret1", "latest")
