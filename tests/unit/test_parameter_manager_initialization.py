"""
Unit tests for Parameter Manager service initialization and configuration.

Tests the ParameterManagerService initialization with various environment
configurations, credential handling, and project detection scenarios.
"""

import subprocess

import pytest
from google.auth.credentials import Credentials
from google.oauth2 import service_account

from app.exceptions.parameter_manager import ParameterManagerException
from app.services.parameter_manager import ParameterManagerService


# Test fixtures
@pytest.fixture
def mock_logger(mocker):
    """Mock logger to prevent actual logging during tests."""
    return mocker.patch("app.services.parameter_manager.get_logger")


@pytest.fixture
def clean_environment(monkeypatch):
    """Clean environment variables before each test."""
    env_vars = [
        "GOOGLE_CLOUD_PROJECT",
        "GCP_PROJECT",
        "GCLOUD_PROJECT",
        "PROJECT_ID",
        "GOOGLE_APPLICATION_CREDENTIALS",
    ]
    for var in env_vars:
        monkeypatch.delenv(var, raising=False)
    yield


# ============================================================================
# Project ID Detection Tests
# ============================================================================


def test_init_with_explicit_project_id(mock_logger):
    """Test initialization with explicitly provided project ID."""
    service = ParameterManagerService(project_id="explicit-project")

    assert service.project_id == "explicit-project"
    assert service.location == "global"


def test_init_with_google_cloud_project_env(
    mock_logger, clean_environment, monkeypatch
):
    """Test project ID detection from GOOGLE_CLOUD_PROJECT environment variable."""
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "env-project")

    service = ParameterManagerService()

    assert service.project_id == "env-project"


def test_init_with_gcp_project_env(mock_logger, clean_environment, monkeypatch):
    """Test project ID detection from GCP_PROJECT environment variable."""
    monkeypatch.setenv("GCP_PROJECT", "gcp-env-project")

    service = ParameterManagerService()

    assert service.project_id == "gcp-env-project"


def test_init_with_gcloud_project_env(mock_logger, clean_environment, monkeypatch):
    """Test project ID detection from GCLOUD_PROJECT environment variable."""
    monkeypatch.setenv("GCLOUD_PROJECT", "gcloud-env-project")

    service = ParameterManagerService()

    assert service.project_id == "gcloud-env-project"


def test_init_with_project_id_env(mock_logger, clean_environment, monkeypatch):
    """Test project ID detection from PROJECT_ID environment variable."""
    monkeypatch.setenv("PROJECT_ID", "project-id-env")

    service = ParameterManagerService()

    assert service.project_id == "project-id-env"


def test_init_project_id_priority_explicit_over_env(mock_logger, monkeypatch):
    """Test that explicit project ID takes priority over environment variables."""
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "env-project")

    service = ParameterManagerService(project_id="explicit-project")

    assert service.project_id == "explicit-project"


def test_init_project_id_from_gcloud_config(mock_logger, clean_environment, mocker):
    """Test project ID detection from gcloud config."""
    mock_result = mocker.Mock()
    mock_result.returncode = 0
    mock_result.stdout = "gcloud-config-project\n"

    mocker.patch("subprocess.run", return_value=mock_result)
    service = ParameterManagerService()

    assert service.project_id == "gcloud-config-project"


def test_init_project_id_gcloud_config_fails(mock_logger, clean_environment, mocker):
    """Test handling when gcloud config command fails."""
    mocker.patch(
        "subprocess.run", side_effect=subprocess.CalledProcessError(1, "gcloud")
    )

    with pytest.raises(ParameterManagerException) as exc_info:
        ParameterManagerService()

    assert "Project ID must be provided" in str(exc_info.value)


def test_init_project_id_gcloud_config_timeout(mock_logger, clean_environment, mocker):
    """Test handling when gcloud config command times out."""
    mocker.patch("subprocess.run", side_effect=subprocess.TimeoutExpired("gcloud", 5))

    with pytest.raises(ParameterManagerException) as exc_info:
        ParameterManagerService()

    assert "Project ID must be provided" in str(exc_info.value)


def test_init_project_id_gcloud_not_installed(mock_logger, clean_environment, mocker):
    """Test handling when gcloud is not installed."""
    mocker.patch("subprocess.run", side_effect=FileNotFoundError("gcloud not found"))

    with pytest.raises(ParameterManagerException) as exc_info:
        ParameterManagerService()

    assert "Project ID must be provided" in str(exc_info.value)


def test_init_project_id_from_metadata_service(mock_logger, clean_environment, mocker):
    """Test project ID detection from GCP metadata service."""
    mock_response = mocker.Mock()
    mock_response.status_code = 200
    mock_response.text = "metadata-project"

    mocker.patch("subprocess.run", side_effect=FileNotFoundError())
    mocker.patch("requests.get", return_value=mock_response)

    service = ParameterManagerService()

    assert service.project_id == "metadata-project"


def test_init_project_id_metadata_service_fails(mock_logger, clean_environment, mocker):
    """Test handling when metadata service is unavailable."""
    mocker.patch("subprocess.run", side_effect=FileNotFoundError())
    mocker.patch("requests.get", side_effect=Exception("Connection failed"))

    with pytest.raises(ParameterManagerException) as exc_info:
        ParameterManagerService()

    assert "Project ID must be provided" in str(exc_info.value)


def test_init_project_id_metadata_service_404(mock_logger, clean_environment, mocker):
    """Test handling when metadata service returns 404."""
    mock_response = mocker.Mock()
    mock_response.status_code = 404

    mocker.patch("subprocess.run", side_effect=FileNotFoundError())
    mocker.patch("requests.get", return_value=mock_response)

    with pytest.raises(ParameterManagerException) as exc_info:
        ParameterManagerService()

    assert "Project ID must be provided" in str(exc_info.value)


def test_init_no_project_id_available(mock_logger, clean_environment, mocker):
    """Test initialization fails when no project ID can be determined."""
    mocker.patch("subprocess.run", side_effect=FileNotFoundError())
    mocker.patch("requests.get", side_effect=Exception("No metadata"))

    with pytest.raises(ParameterManagerException) as exc_info:
        ParameterManagerService()

    assert "Project ID must be provided" in str(exc_info.value)
    assert "GOOGLE_CLOUD_PROJECT" in str(exc_info.value)


# ============================================================================
# Credentials Handling Tests
# ============================================================================


def test_init_with_credentials_object(mock_logger, mocker):
    """Test initialization with a Credentials object."""
    mock_creds = mocker.Mock(spec=Credentials)

    service = ParameterManagerService(project_id="test-project", credentials=mock_creds)

    assert service.credentials == mock_creds


def test_init_with_credentials_json_string(mock_logger, mocker):
    """Test initialization with service account JSON string."""
    creds_json = """{
        "type": "service_account",
        "project_id": "test-project",
        "private_key_id": "key-id",
        "private_key": "-----BEGIN PRIVATE KEY-----\\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC\\n-----END PRIVATE KEY-----\\n",
        "client_email": "test@test-project.iam.gserviceaccount.com",
        "client_id": "123456789",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/test%40test-project.iam.gserviceaccount.com"
    }"""

    mock_creds = mocker.Mock(spec=service_account.Credentials)
    mock_from_info = mocker.patch(
        "google.oauth2.service_account.Credentials.from_service_account_info",
        return_value=mock_creds,
    )

    service = ParameterManagerService(project_id="test-project", credentials=creds_json)

    assert service.credentials == mock_creds
    mock_from_info.assert_called_once()


def test_init_with_invalid_credentials_json(mock_logger):
    """Test initialization fails with invalid JSON credentials string."""
    invalid_json = "{invalid json"

    with pytest.raises(ParameterManagerException) as exc_info:
        ParameterManagerService(project_id="test-project", credentials=invalid_json)

    assert "Invalid credentials JSON string" in str(exc_info.value)


def test_init_with_invalid_credentials_type(mock_logger):
    """Test initialization fails with invalid credentials type."""
    invalid_creds = 12345  # Not a Credentials object or string

    with pytest.raises(ParameterManagerException) as exc_info:
        ParameterManagerService(project_id="test-project", credentials=invalid_creds)

    assert "Invalid credentials type" in str(exc_info.value)


def test_init_with_credentials_path(mock_logger, tmp_path, mocker):
    """Test initialization with service account key file path."""
    # Create a temporary credentials file
    creds_file = tmp_path / "credentials.json"
    creds_file.write_text(
        """{
        "type": "service_account",
        "project_id": "test-project",
        "private_key_id": "key-id",
        "private_key": "-----BEGIN PRIVATE KEY-----\\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC\\n-----END PRIVATE KEY-----\\n",
        "client_email": "test@test-project.iam.gserviceaccount.com",
        "client_id": "123456789",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/test%40test-project.iam.gserviceaccount.com"
    }"""
    )

    mock_creds = mocker.Mock(spec=service_account.Credentials)
    mock_from_file = mocker.patch(
        "google.oauth2.service_account.Credentials.from_service_account_file",
        return_value=mock_creds,
    )

    service = ParameterManagerService(
        project_id="test-project", credentials_path=str(creds_file)
    )

    assert service.credentials == mock_creds
    mock_from_file.assert_called_once()


def test_init_with_nonexistent_credentials_path(mock_logger):
    """Test initialization fails with non-existent credentials file."""
    with pytest.raises(ParameterManagerException) as exc_info:
        ParameterManagerService(
            project_id="test-project",
            credentials_path="/nonexistent/path/credentials.json",
        )

    assert "Service account key file not found" in str(exc_info.value)


def test_init_with_invalid_credentials_file(mock_logger, tmp_path, mocker):
    """Test initialization fails with invalid credentials file."""
    creds_file = tmp_path / "invalid_credentials.json"
    creds_file.write_text("{invalid json}")

    mocker.patch(
        "google.oauth2.service_account.Credentials.from_service_account_file",
        side_effect=Exception("Invalid credentials file"),
    )

    with pytest.raises(ParameterManagerException) as exc_info:
        ParameterManagerService(
            project_id="test-project", credentials_path=str(creds_file)
        )

    assert "Failed to load credentials from file" in str(exc_info.value)


def test_init_credentials_path_priority_over_credentials(mock_logger, tmp_path, mocker):
    """Test that credentials_path takes priority over credentials parameter."""
    creds_file = tmp_path / "credentials.json"
    creds_file.write_text(
        """{
        "type": "service_account",
        "project_id": "test-project",
        "private_key_id": "key-id",
        "private_key": "-----BEGIN PRIVATE KEY-----\\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC\\n-----END PRIVATE KEY-----\\n",
        "client_email": "test@test-project.iam.gserviceaccount.com",
        "client_id": "123456789",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/test%40test-project.iam.gserviceaccount.com"
    }"""
    )

    mock_creds_param = mocker.Mock(spec=Credentials)
    mock_creds_file = mocker.Mock(spec=service_account.Credentials)
    mock_from_file = mocker.patch(
        "google.oauth2.service_account.Credentials.from_service_account_file",
        return_value=mock_creds_file,
    )

    service = ParameterManagerService(
        project_id="test-project",
        credentials=mock_creds_param,
        credentials_path=str(creds_file),
    )

    # Should use credentials from file, not the parameter
    assert service.credentials == mock_creds_file
    mock_from_file.assert_called_once()


def test_init_with_google_application_credentials_env(
    mock_logger, monkeypatch, tmp_path, mocker
):
    """Test credentials detection from GOOGLE_APPLICATION_CREDENTIALS environment variable."""
    creds_file = tmp_path / "credentials.json"
    creds_file.write_text(
        """{
        "type": "service_account",
        "project_id": "test-project",
        "private_key_id": "key-id",
        "private_key": "-----BEGIN PRIVATE KEY-----\\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC\\n-----END PRIVATE KEY-----\\n",
        "client_email": "test@test-project.iam.gserviceaccount.com",
        "client_id": "123456789",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/test%40test-project.iam.gserviceaccount.com"
    }"""
    )

    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", str(creds_file))

    mock_creds = mocker.Mock(spec=service_account.Credentials)
    mocker.patch(
        "google.oauth2.service_account.Credentials.from_service_account_file",
        return_value=mock_creds,
    )

    # Mock the env helper to return the path
    mocker.patch("app.helpers.environment.env", return_value=str(creds_file))

    service = ParameterManagerService(project_id="test-project")

    assert service.credentials == mock_creds


def test_init_with_default_credentials(mock_logger, mocker):
    """Test initialization with default credentials (ADC)."""
    mock_creds = mocker.Mock(spec=Credentials)

    mocker.patch(
        "app.services.parameter_manager.default_credentials",
        return_value=(mock_creds, "detected-project"),
    )

    service = ParameterManagerService(project_id="test-project")

    assert service.credentials == mock_creds


def test_init_default_credentials_failure(mock_logger, mocker):
    """Test handling when default credentials fail to load."""
    mocker.patch(
        "app.services.parameter_manager.default_credentials",
        side_effect=Exception("No credentials found"),
    )

    # Should not raise an exception, just use None for credentials
    service = ParameterManagerService(project_id="test-project")

    assert service.credentials is None


# ============================================================================
# Location Configuration Tests
# ============================================================================


def test_init_with_default_location(mock_logger):
    """Test initialization with default global location."""
    service = ParameterManagerService(project_id="test-project")

    assert service.location == "global"


def test_init_with_regional_location(mock_logger):
    """Test initialization with regional location."""
    service = ParameterManagerService(project_id="test-project", location="us-central1")

    assert service.location == "us-central1"


def test_init_with_custom_location(mock_logger):
    """Test initialization with custom location."""
    service = ParameterManagerService(
        project_id="test-project", location="europe-west1"
    )

    assert service.location == "europe-west1"


# ============================================================================
# Cache Configuration Tests
# ============================================================================


def test_init_with_cache_disabled(mock_logger):
    """Test initialization with caching disabled (default)."""
    service = ParameterManagerService(project_id="test-project")

    assert service.enable_cache is False
    assert service.cache_ttl_seconds == 300
    assert len(service._cache) == 0


def test_init_with_cache_enabled(mock_logger):
    """Test initialization with caching enabled."""
    service = ParameterManagerService(project_id="test-project", enable_cache=True)

    assert service.enable_cache is True
    assert service.cache_ttl_seconds == 300


def test_init_with_custom_cache_ttl(mock_logger):
    """Test initialization with custom cache TTL."""
    service = ParameterManagerService(
        project_id="test-project", enable_cache=True, cache_ttl_seconds=600
    )

    assert service.enable_cache is True
    assert service.cache_ttl_seconds == 600


# ============================================================================
# Client Initialization Tests
# ============================================================================


def test_init_client_initialization_success(mock_logger):
    """Test successful client initialization."""
    service = ParameterManagerService(project_id="test-project")

    # Client should be initialized (currently None as placeholder)
    assert hasattr(service, "client")


def test_init_logs_initialization_success(mock_logger, mocker):
    """Test that successful initialization is logged."""
    mock_log_instance = mocker.Mock()
    mock_logger.return_value = mock_log_instance

    ParameterManagerService(project_id="test-project")

    # Verify info log was called for successful initialization
    assert mock_log_instance.info.called


def test_init_with_all_parameters(mock_logger, mocker):
    """Test initialization with all parameters specified."""
    mock_creds = mocker.Mock(spec=Credentials)

    service = ParameterManagerService(
        project_id="full-config-project",
        location="us-east1",
        credentials=mock_creds,
        enable_cache=True,
        cache_ttl_seconds=600,
    )

    assert service.project_id == "full-config-project"
    assert service.location == "us-east1"
    assert service.credentials == mock_creds
    assert service.enable_cache is True
    assert service.cache_ttl_seconds == 600


# ============================================================================
# Error Handling Tests
# ============================================================================


def test_init_error_message_includes_helpful_info(
    mock_logger, clean_environment, mocker
):
    """Test that initialization error includes helpful information."""
    mocker.patch("subprocess.run", side_effect=FileNotFoundError())
    mocker.patch("requests.get", side_effect=Exception("No metadata"))

    with pytest.raises(ParameterManagerException) as exc_info:
        ParameterManagerService()

    error_msg = str(exc_info.value)
    assert "Project ID must be provided" in error_msg
    assert "GOOGLE_CLOUD_PROJECT" in error_msg
    assert "gcloud CLI" in error_msg or "environment variable" in error_msg


def test_init_validates_configuration(mock_logger, mocker):
    """Test that initialization validates configuration."""
    # Test with valid configuration
    service = ParameterManagerService(project_id="valid-project")
    assert service.project_id == "valid-project"

    # Test with invalid configuration (no project ID)
    mocker.patch("subprocess.run", side_effect=FileNotFoundError())
    mocker.patch("requests.get", side_effect=Exception("No metadata"))

    with pytest.raises(ParameterManagerException):
        ParameterManagerService()
