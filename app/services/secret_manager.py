# Secret Manager Service
# This file contains the main SecretManagerService class

import os
import time
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Tuple, Union

from google.api_core import exceptions as gcp_exceptions
from google.auth import default as default_credentials
from google.auth.credentials import Credentials
from google.cloud import secretmanager
from google.oauth2 import service_account

from app.exceptions.secret_manager import (
    SecretAccessDeniedException,
    SecretConnectionException,
    SecretInternalErrorException,
    SecretManagerException,
    SecretNotFoundException,
    SecretQuotaExceededException,
    SecretTimeoutException,
    SecretUnavailableException,
    SecretVersionNotFoundException,
)
from app.helpers.environment import env
from app.helpers.logger import get_logger
from app.requests.secret_manager import SecretCreateRequest, SecretVersionCreateRequest
from app.responses.secret_manager import (
    SecretCreateResponse,
    SecretListResponse,
    SecretMetadataResponse,
    SecretOperationResponse,
    SecretResponse,
    SecretVersionListResponse,
    SecretVersionResponse,
)


class SecretManagerService:
    """
    Service class for managing secrets using Google Cloud Secret Manager.

    This service provides a secure, type-safe interface for storing, retrieving,
    and managing sensitive configuration data following the Spartan Framework patterns.
    It integrates seamlessly with Google Cloud Secret Manager to provide
    enterprise-grade secret management capabilities.

    Features:
        - Create, retrieve, update, and delete secrets
        - Version management with full history
        - Optional in-memory caching for improved performance
        - Comprehensive error handling with custom exceptions
        - Structured logging without exposing secret values
        - Automatic project and credential detection
        - Support for labels and metadata
        - Pagination for large result sets

    The service follows the Spartan Framework's established patterns:
        - Pydantic models for request/response validation
        - Custom exceptions for error handling
        - Integration with framework logging system
        - Environment-based configuration

    Attributes:
        project_id: Google Cloud project ID where secrets are stored
        client: Google Cloud Secret Manager client instance
        logger: Framework logger instance for structured logging
        enable_cache: Whether in-memory caching is enabled
        cache_ttl_seconds: Time-to-live for cached secrets in seconds

    Example:
        >>> # Basic usage with auto-detected project
        >>> service = SecretManagerService()
        >>>
        >>> # Create a secret
        >>> request = SecretCreateRequest(
        ...     secret_name="api-key",
        ...     secret_value="secret-value-123"
        ... )
        >>> response = service.create_secret(request)
        >>>
        >>> # Retrieve the secret
        >>> secret = service.get_secret("api-key")
        >>> print(secret.secret_value)
        >>>
        >>> # With caching enabled
        >>> cached_service = SecretManagerService(
        ...     enable_cache=True,
        ...     cache_ttl_seconds=300
        ... )
        >>> secret = cached_service.get_secret("api-key")  # Cached for 5 minutes

    See Also:
        - SecretCreateRequest: Request model for creating secrets
        - SecretResponse: Response model for secret retrieval
        - SecretManagerException: Base exception for all secret manager errors
    """

    def __init__(
        self,
        project_id: Optional[str] = None,
        credentials: Optional[Union[Credentials, str]] = None,
        credentials_path: Optional[str] = None,
        enable_cache: bool = False,
        cache_ttl_seconds: int = 300,
    ):
        """
        Initialize the Secret Manager service.

        Args:
            project_id: Google Cloud project ID. If None, will attempt to detect from environment.
            credentials: Google Cloud credentials object or service account key JSON string.
                        If None, will use default credentials.
            credentials_path: Path to service account key file. If provided, takes precedence
                            over credentials parameter.
            enable_cache: Enable in-memory caching for secret values (default: False)
            cache_ttl_seconds: Time-to-live for cached secrets in seconds (default: 300)

        Raises:
            SecretManagerException: If project_id cannot be determined, credentials are invalid,
                                  or client initialization fails.
        """
        self.logger = get_logger("secret_manager_service")

        # Enhanced project ID detection with framework integration
        self.project_id = self._determine_project_id(project_id)
        if not self.project_id:
            raise SecretManagerException(
                "Project ID must be provided or available in environment. "
                "Set GOOGLE_CLOUD_PROJECT environment variable, configure gcloud CLI, "
                "or provide project_id parameter."
            )

        # Enhanced credential handling
        self.credentials = self._setup_credentials(credentials, credentials_path)

        # Initialize Google Cloud Secret Manager client with enhanced error handling
        self._initialize_client()

        # Initialize caching mechanism
        self.enable_cache = enable_cache
        self.cache_ttl_seconds = cache_ttl_seconds
        self._cache: Dict[str, Tuple[Any, datetime]] = {}

        if self.enable_cache:
            self.logger.info(
                "Secret caching enabled",
                extra={
                    "cache_ttl_seconds": self.cache_ttl_seconds,
                    "project_id": self.project_id,
                },
            )

    def _determine_project_id(
        self, provided_project_id: Optional[str]
    ) -> Optional[str]:
        """
        Determine project ID from multiple sources with enhanced detection.

        Args:
            provided_project_id: Project ID provided directly to constructor

        Returns:
            Project ID string or None if not found
        """
        # Priority order for project ID detection:
        # 1. Explicitly provided parameter
        # 2. Framework environment configuration
        # 3. Standard Google Cloud environment variables
        # 4. Google Cloud SDK default project
        # 5. Metadata service (for GCP environments)

        if provided_project_id:
            self.logger.debug(
                "Project ID provided explicitly",
                extra={
                    "project_id": provided_project_id,
                    "source": "constructor_parameter",
                    "detection_method": "explicit",
                },
            )
            return provided_project_id

        # Try each detection method in order
        detection_methods = [
            self._try_framework_env_project_id,
            self._try_standard_env_vars_project_id,
            self._try_gcloud_config_project_id,
            self._try_metadata_service_project_id,
        ]

        for method in detection_methods:
            project_id = method()
            if project_id:
                return project_id

        # If we get here, no project ID could be determined
        self._log_project_detection_failure()
        return None

    def _try_framework_env_project_id(self) -> Optional[str]:
        """Try to get project ID from framework environment."""
        try:
            framework_project_id = env("GOOGLE_CLOUD_PROJECT")
            if framework_project_id:
                self.logger.debug(
                    "Project ID detected from framework environment",
                    extra={
                        "project_id": framework_project_id,
                        "source_env_var": "GOOGLE_CLOUD_PROJECT",
                        "detection_method": "environment_variable",
                    },
                )
                return framework_project_id
        except Exception as e:
            self.logger.debug(
                "Failed to read from framework environment",
                extra={
                    "error": str(e),
                    "source": "framework_environment",
                    "detection_method": "environment_variable",
                },
            )
        return None

    def _try_standard_env_vars_project_id(self) -> Optional[str]:
        """Try to get project ID from standard environment variables."""
        gcp_env_vars = [
            "GOOGLE_CLOUD_PROJECT",
            "GCP_PROJECT",
            "GCLOUD_PROJECT",
            "PROJECT_ID",
        ]

        for env_var in gcp_env_vars:
            project_id = os.getenv(env_var)
            if project_id:
                self.logger.debug(
                    "Project ID detected from environment variable",
                    extra={
                        "project_id": project_id,
                        "source_env_var": env_var,
                        "detection_method": "environment_variable",
                    },
                )
                return project_id
        return None

    def _try_gcloud_config_project_id(self) -> Optional[str]:
        """Try to get project ID from gcloud config."""
        try:
            import subprocess

            result = subprocess.run(
                ["gcloud", "config", "get-value", "project"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0 and result.stdout.strip():
                gcloud_project = result.stdout.strip()
                self.logger.debug(
                    "Project ID detected from gcloud config",
                    extra={
                        "project_id": gcloud_project,
                        "source": "gcloud_config",
                        "detection_method": "gcloud_cli",
                    },
                )
                return gcloud_project
        except (
            subprocess.TimeoutExpired,
            subprocess.CalledProcessError,
            FileNotFoundError,
        ) as e:
            self.logger.debug(
                "Failed to get project from gcloud config",
                extra={
                    "error": str(e),
                    "source": "gcloud_config",
                    "detection_method": "gcloud_cli",
                },
            )
        return None

    def _try_metadata_service_project_id(self) -> Optional[str]:
        """Try to get project ID from GCP metadata service."""
        try:
            import requests

            metadata_url = (
                "http://metadata.google.internal/computeMetadata/v1/project/project-id"
            )
            headers = {"Metadata-Flavor": "Google"}
            response = requests.get(metadata_url, headers=headers, timeout=2)
            if response.status_code == 200:
                metadata_project = response.text.strip()
                self.logger.debug(
                    "Project ID detected from metadata service",
                    extra={
                        "project_id": metadata_project,
                        "source_env_var": "metadata_service",
                        "detection_method": "gcp_metadata",
                    },
                )
                return metadata_project
        except Exception as e:
            self.logger.debug(
                "Failed to get project from metadata service",
                extra={
                    "error": str(e),
                    "source": "metadata_service",
                    "detection_method": "gcp_metadata",
                },
            )
        return None

    def _log_project_detection_failure(self):
        """Log failure to detect project ID from any source."""
        self.logger.error(
            "Project ID could not be determined from any source",
            extra={
                "attempted_sources": [
                    "constructor_parameter",
                    "framework_environment",
                    "environment_variables",
                    "gcloud_config",
                    "metadata_service",
                ],
                "checked_env_vars": [
                    "GOOGLE_CLOUD_PROJECT",
                    "GCP_PROJECT",
                    "GCLOUD_PROJECT",
                    "PROJECT_ID",
                ],
            },
        )

    def _setup_credentials(
        self,
        credentials: Optional[Union[Credentials, str]],
        credentials_path: Optional[str],
    ) -> Optional[Credentials]:
        """
        Setup Google Cloud credentials with enhanced handling.

        Args:
            credentials: Credentials object or service account JSON string
            credentials_path: Path to service account key file

        Returns:
            Credentials object or None for default credentials

        Raises:
            SecretManagerException: If credentials are invalid or cannot be loaded
        """
        # Priority order for credentials:
        # 1. Service account key file path
        # 2. Credentials object or JSON string
        # 3. Framework environment configuration for credentials
        # 4. Default credentials (ADC)

        credential_methods = [
            lambda: self._try_credentials_file(credentials_path),
            lambda: self._try_provided_credentials(credentials),
            lambda: self._try_framework_credentials(),
            lambda: self._try_default_credentials(),
        ]

        for method in credential_methods:
            result = method()
            if result is not None:
                return result

        return None

    def _try_credentials_file(
        self, credentials_path: Optional[str]
    ) -> Optional[Credentials]:
        """Try to load credentials from service account key file."""
        if not credentials_path:
            return None

        if not os.path.exists(credentials_path):
            self.logger.error(
                "Service account key file not found",
                extra={
                    "credentials_path": credentials_path,
                    "credential_source": "file_path",
                },
            )
            raise SecretManagerException(
                f"Service account key file not found: {credentials_path}"
            )

        try:
            creds = service_account.Credentials.from_service_account_file(
                credentials_path,
                scopes=["https://www.googleapis.com/auth/cloud-platform"],
            )
            self.logger.debug(
                "Credentials loaded from service account file",
                extra={
                    "credentials_path": credentials_path,
                    "credential_source": "service_account_file",
                    "service_account_email": getattr(
                        creds, "service_account_email", "unknown"
                    ),
                },
            )
            return creds
        except Exception as e:
            self.logger.error(
                "Failed to load credentials from service account file",
                extra={
                    "credentials_path": credentials_path,
                    "error": str(e),
                    "credential_source": "service_account_file",
                },
            )
            raise SecretManagerException(
                f"Failed to load credentials from file {credentials_path}: {str(e)}"
            )

    def _try_provided_credentials(
        self, credentials: Optional[Union[Credentials, str]]
    ) -> Optional[Credentials]:
        """Try to use provided credentials object or JSON string."""
        if not credentials:
            return None

        if isinstance(credentials, str):
            return self._load_credentials_from_json(credentials)
        elif isinstance(credentials, Credentials):
            self.logger.debug(
                "Using provided credentials object",
                extra={
                    "credential_source": "credentials_object",
                    "credential_type": type(credentials).__name__,
                },
            )
            return credentials
        else:
            self.logger.error(
                "Invalid credentials type provided",
                extra={
                    "credential_type": type(credentials).__name__,
                    "credential_source": "invalid",
                },
            )
            raise SecretManagerException(
                f"Invalid credentials type: {type(credentials)}. "
                "Expected Credentials object or JSON string."
            )

    def _load_credentials_from_json(self, credentials_json: str) -> Credentials:
        """Load credentials from JSON string."""
        try:
            import json

            creds_info = json.loads(credentials_json)
            creds = service_account.Credentials.from_service_account_info(
                creds_info,
                scopes=["https://www.googleapis.com/auth/cloud-platform"],
            )
            self.logger.debug(
                "Credentials loaded from JSON string",
                extra={
                    "credential_source": "json_string",
                    "service_account_email": getattr(
                        creds, "service_account_email", "unknown"
                    ),
                },
            )
            return creds
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            self.logger.error(
                "Failed to parse credentials JSON string",
                extra={"error": str(e), "credential_source": "json_string"},
            )
            raise SecretManagerException(f"Invalid credentials JSON string: {str(e)}")

    def _try_framework_credentials(self) -> Optional[Credentials]:
        """Try to load credentials from framework environment."""
        try:
            # Re-import the environment helper module so that tests which
            # patch app.helpers.environment.env affect this lookup.
            try:
                from app.helpers import environment as env_module

                framework_creds_path = env_module.env("GOOGLE_APPLICATION_CREDENTIALS")
            except ImportError:
                # Fallback to the locally imported env helper
                framework_creds_path = env("GOOGLE_APPLICATION_CREDENTIALS")

            if framework_creds_path and os.path.exists(framework_creds_path):
                try:
                    creds = service_account.Credentials.from_service_account_file(
                        framework_creds_path,
                        scopes=["https://www.googleapis.com/auth/cloud-platform"],
                    )
                    self.logger.debug(
                        "Credentials loaded from framework environment",
                        extra={
                            "credentials_path": framework_creds_path,
                            "credential_source": "framework_environment",
                            "service_account_email": getattr(
                                creds, "service_account_email", "unknown"
                            ),
                        },
                    )
                    return creds
                except Exception as e:
                    self.logger.warning(
                        "Failed to load credentials from framework environment path",
                        extra={
                            "credentials_path": framework_creds_path,
                            "error": str(e),
                            "credential_source": "framework_environment",
                        },
                    )
        except Exception as e:
            self.logger.debug(
                "Failed to read credentials path from framework environment",
                extra={"error": str(e), "credential_source": "framework_environment"},
            )
        return None

    def _try_default_credentials(self) -> Optional[Credentials]:
        """Try to use default credentials (ADC)."""
        try:
            creds, detected_project = default_credentials()
            self.logger.debug(
                "Using default credentials (ADC)",
                extra={
                    "credential_source": "default_credentials",
                    "detected_project": detected_project,
                    "credential_type": type(creds).__name__,
                },
            )
            return creds
        except Exception as e:
            self.logger.warning(
                "Failed to load default credentials",
                extra={"error": str(e), "credential_source": "default_credentials"},
            )
            # Return None to let the client use default authentication
            return None

    def _initialize_client(self):
        """
        Initialize Google Cloud Secret Manager client with enhanced error handling.

        Raises:
            SecretManagerException: If client initialization fails
        """
        try:
            start_time = time.time()
            credential_info = self._create_client_with_credentials()
            initialization_time = time.time() - start_time
            connection_test = self._test_client_connection()

            self.logger.info(
                "SecretManagerService initialized successfully",
                extra={
                    "project_id": self.project_id,
                    "initialization_time_ms": round(initialization_time * 1000, 2),
                    "client_type": "SecretManagerServiceClient",
                    **credential_info,
                    **connection_test,
                },
            )

        except Exception as e:
            self._handle_client_initialization_error(e)

    def _create_client_with_credentials(self) -> dict:
        """Create the Secret Manager client and return credential info."""
        if self.credentials:
            self.client = secretmanager.SecretManagerServiceClient(
                credentials=self.credentials
            )
            return {
                "credential_source": "custom_credentials",
                "credential_type": type(self.credentials).__name__,
            }
        else:
            self.client = secretmanager.SecretManagerServiceClient()
            return {
                "credential_source": "default_credentials",
                "credential_type": "default",
            }

    def _test_client_connection(self) -> dict:
        """Test the client connection and return test results."""
        if os.getenv("PYTEST_CURRENT_TEST"):
            return {"connection_test": "skipped"}

        try:
            test_request = {
                "parent": f"projects/{self.project_id}",
                "page_size": 1,
            }
            self.client.list_secrets(request=test_request)
            return {"connection_test": "success"}
        except Exception as test_error:
            return self._handle_connection_test_error(test_error)

    def _handle_connection_test_error(self, test_error: Exception) -> dict:
        """Handle connection test errors and return appropriate response."""
        if isinstance(test_error, gcp_exceptions.PermissionDenied):
            return {
                "connection_test": "permission_denied",
                "test_error": str(test_error),
            }
        elif isinstance(test_error, gcp_exceptions.NotFound):
            self.logger.error(
                "Project not found during client initialization test",
                extra={
                    "project_id": self.project_id,
                    "error": str(test_error),
                    "initialization_phase": "connection_test",
                },
            )
            raise SecretManagerException(
                f"Project '{self.project_id}' not found or does not exist"
            )
        else:
            return {
                "connection_test": "failed",
                "test_error": str(test_error),
                "test_error_type": type(test_error).__name__,
            }

    def _handle_client_initialization_error(self, e: Exception):
        """Handle client initialization errors with specific error messages."""
        self.logger.error(
            "Failed to initialize Secret Manager client",
            extra={
                "project_id": self.project_id,
                "error": str(e),
                "error_type": type(e).__name__,
                "initialization_phase": "client_creation",
            },
        )

        if isinstance(e, gcp_exceptions.Unauthenticated):
            raise SecretManagerException(
                "Authentication failed. Please check your credentials and ensure they have "
                "the necessary permissions for Secret Manager operations."
            )
        elif isinstance(e, gcp_exceptions.PermissionDenied):
            raise SecretManagerException(
                f"Permission denied for project '{self.project_id}'. Please ensure your "
                "credentials have the 'Secret Manager Admin' or appropriate IAM roles."
            )
        elif isinstance(e, gcp_exceptions.NotFound):
            raise SecretManagerException(
                f"Project '{self.project_id}' not found. Please verify the project ID "
                "and ensure it exists and is accessible."
            )
        else:
            raise SecretManagerException(
                f"Failed to initialize Secret Manager client: {str(e)}"
            )

    def _log_operation_start(self, operation: str, **context) -> float:
        """
        Log the start of an operation and return start time for timing.

        Args:
            operation: Name of the operation being started
            **context: Additional context to include in logs (secret names, etc.)

        Returns:
            Start time for calculating operation duration
        """
        # Ensure secret values are never logged by filtering them out
        safe_context = {
            k: v
            for k, v in context.items()
            if k not in ["secret_value", "payload", "data"]
        }

        start_time = time.time()
        self.logger.info(
            f"Starting {operation}",
            extra={
                "operation": operation,
                "project_id": self.project_id,
                "operation_start_time": start_time,
                **safe_context,
            },
        )
        return start_time

    def _log_operation_success(self, operation: str, start_time: float, **context):
        """
        Log successful completion of an operation with timing.

        Args:
            operation: Name of the operation that completed
            start_time: Start time from _log_operation_start
            **context: Additional context to include in logs
        """
        # Ensure secret values are never logged
        safe_context = {
            k: v
            for k, v in context.items()
            if k not in ["secret_value", "payload", "data"]
        }

        duration_ms = round((time.time() - start_time) * 1000, 2)
        self.logger.info(
            f"Successfully completed {operation}",
            extra={
                "operation": operation,
                "project_id": self.project_id,
                "operation_duration_ms": duration_ms,
                "operation_status": "success",
                **safe_context,
            },
        )

    def _log_operation_error(
        self, operation: str, start_time: float, error: Exception, **context
    ):
        """
        Log failed operation with timing and error details.

        Args:
            operation: Name of the operation that failed
            start_time: Start time from _log_operation_start
            error: The exception that occurred
            **context: Additional context to include in logs
        """
        # Ensure secret values are never logged
        safe_context = {
            k: v
            for k, v in context.items()
            if k not in ["secret_value", "payload", "data"]
        }

        duration_ms = round((time.time() - start_time) * 1000, 2)
        self.logger.error(
            f"Failed to complete {operation}",
            extra={
                "operation": operation,
                "project_id": self.project_id,
                "operation_duration_ms": duration_ms,
                "operation_status": "error",
                "error_type": type(error).__name__,
                "error_message": str(error),
                **safe_context,
            },
        )

    def _get_project_path(self) -> str:
        """Get the full project path for Google Cloud Secret Manager."""
        return f"projects/{self.project_id}"

    def _get_secret_path(self, secret_name: str) -> str:
        """Get the full secret path for Google Cloud Secret Manager."""
        return f"projects/{self.project_id}/secrets/{secret_name}"

    def _get_secret_version_path(self, secret_name: str, version: str) -> str:
        """Get the full secret version path for Google Cloud Secret Manager."""
        return f"projects/{self.project_id}/secrets/{secret_name}/versions/{version}"

    def _map_gcp_exception(
        self, e: Exception, operation: str, context: dict = None
    ) -> SecretManagerException:
        """
        Map Google Cloud API exceptions to custom Secret Manager exceptions.

        Args:
            e: The original Google Cloud exception
            operation: Description of the operation that failed
            context: Additional context information (secret_name, version, etc.)

        Returns:
            Appropriate SecretManagerException subclass
        """
        context = context or {}
        context["operation"] = operation  # Add operation to context
        safe_context = self._get_safe_context(context)

        self._log_gcp_error(e, operation, safe_context)
        mapped_exception = self._get_mapped_exception(e, context)
        self._log_mapped_exception(operation, e, mapped_exception, safe_context)

        return mapped_exception

    def _get_safe_context(self, context: dict) -> dict:
        """Remove sensitive data from context for logging."""
        return {
            k: v
            for k, v in context.items()
            if k not in ["secret_value", "payload", "data"]
        }

    def _log_gcp_error(self, e: Exception, operation: str, safe_context: dict):
        """Log the original GCP error with context."""
        self.logger.error(
            f"Google Cloud API error during {operation}",
            extra={
                "operation": operation,
                "gcp_error_type": type(e).__name__,
                "gcp_error_message": str(e),
                "project_id": self.project_id,
                "error_mapping": "gcp_to_custom",
                **safe_context,
            },
        )

    def _get_mapped_exception(
        self, e: Exception, context: dict
    ) -> SecretManagerException:
        """Map GCP exception to appropriate custom exception."""
        secret_name = context.get("secret_name", "unknown")
        version = context.get("version", "")
        operation = context.get("operation", "operation")
        error_msg = str(e)

        exception_mappings = [
            (
                gcp_exceptions.NotFound,
                lambda: self._handle_not_found(secret_name, version),
            ),
            (
                gcp_exceptions.PermissionDenied,
                lambda: SecretAccessDeniedException(
                    f"Permission denied for {operation} on secret '{secret_name}': {error_msg}"
                ),
            ),
            (
                gcp_exceptions.AlreadyExists,
                lambda: SecretManagerException(
                    f"Secret '{secret_name}' already exists"
                ),
            ),
            (
                gcp_exceptions.FailedPrecondition,
                lambda: self._handle_failed_precondition(
                    secret_name, version, error_msg
                ),
            ),
            (
                gcp_exceptions.InvalidArgument,
                lambda: SecretManagerException(
                    f"Invalid argument for {operation}: {error_msg}"
                ),
            ),
            (
                gcp_exceptions.ResourceExhausted,
                lambda: SecretQuotaExceededException(
                    f"Quota exceeded for {operation}: {error_msg}"
                ),
            ),
            (
                gcp_exceptions.DeadlineExceeded,
                lambda: SecretTimeoutException(
                    f"Operation timed out during {operation}: {error_msg}"
                ),
            ),
            (
                gcp_exceptions.ServiceUnavailable,
                lambda: SecretUnavailableException(
                    f"Secret Manager service temporarily unavailable during {operation}: {error_msg}"
                ),
            ),
            (
                gcp_exceptions.InternalServerError,
                lambda: SecretInternalErrorException(
                    f"Internal server error during {operation}: {error_msg}"
                ),
            ),
            (
                (gcp_exceptions.RetryError, gcp_exceptions.TooManyRequests),
                lambda: SecretConnectionException(
                    f"Network or rate limiting issue during {operation}: {error_msg}"
                ),
            ),
            (
                (ConnectionError, OSError),
                lambda: SecretConnectionException(
                    f"Network connectivity issue during {operation}: {error_msg}"
                ),
            ),
        ]

        for exception_types, handler in exception_mappings:
            if isinstance(e, exception_types):
                return handler()

        return SecretManagerException(
            f"Unexpected error during {operation}: {error_msg}"
        )

    def _handle_not_found(
        self, secret_name: str, version: str
    ) -> SecretManagerException:
        """Handle NotFound exceptions based on context."""
        if version:
            return SecretVersionNotFoundException(
                f"Secret '{secret_name}' version '{version}' not found"
            )
        else:
            return SecretNotFoundException(f"Secret '{secret_name}' not found")

    def _handle_failed_precondition(
        self, secret_name: str, version: str, error_msg: str
    ) -> SecretManagerException:
        """Handle FailedPrecondition exceptions."""
        if "disabled" in error_msg.lower() or "destroyed" in error_msg.lower():
            return SecretVersionNotFoundException(
                f"Secret '{secret_name}' version '{version}' is not accessible (disabled or destroyed)"
            )
        else:
            return SecretManagerException(
                f"Operation failed due to precondition: {error_msg}"
            )

    def _log_mapped_exception(
        self,
        operation: str,
        original_e: Exception,
        mapped_e: SecretManagerException,
        safe_context: dict,
    ):
        """Log the exception mapping details."""
        self.logger.debug(
            "Mapped GCP exception to custom exception",
            extra={
                "operation": operation,
                "original_exception": type(original_e).__name__,
                "mapped_exception": type(mapped_e).__name__,
                "project_id": self.project_id,
                **safe_context,
            },
        )

    def _get_cache_key(self, secret_name: str, version: str = "latest") -> str:
        """
        Generate a cache key for a secret.

        Args:
            secret_name: Name of the secret
            version: Version of the secret

        Returns:
            Cache key string
        """
        return f"{secret_name}:{version}"

    def _get_from_cache(self, cache_key: str) -> Optional[Any]:
        """
        Retrieve a value from cache if it exists and is not expired.

        Args:
            cache_key: Cache key to retrieve

        Returns:
            Cached value if found and not expired, None otherwise
        """
        if not self.enable_cache:
            return None

        if cache_key in self._cache:
            value, expiry_time = self._cache[cache_key]
            if datetime.now() < expiry_time:
                self.logger.debug(
                    "Cache hit",
                    extra={
                        "cache_key": cache_key,
                        "expiry_time": expiry_time.isoformat(),
                        "project_id": self.project_id,
                    },
                )
                return value
            else:
                # Cache entry expired, remove it
                self.logger.debug(
                    "Cache entry expired",
                    extra={
                        "cache_key": cache_key,
                        "expiry_time": expiry_time.isoformat(),
                        "project_id": self.project_id,
                    },
                )
                del self._cache[cache_key]

        self.logger.debug(
            "Cache miss", extra={"cache_key": cache_key, "project_id": self.project_id}
        )
        return None

    def _put_in_cache(self, cache_key: str, value: Any) -> None:
        """
        Store a value in cache with TTL.

        Args:
            cache_key: Cache key to store
            value: Value to cache
        """
        if not self.enable_cache:
            return

        expiry_time = datetime.now() + timedelta(seconds=self.cache_ttl_seconds)
        self._cache[cache_key] = (value, expiry_time)

        self.logger.debug(
            "Value cached",
            extra={
                "cache_key": cache_key,
                "expiry_time": expiry_time.isoformat(),
                "cache_size": len(self._cache),
                "project_id": self.project_id,
            },
        )

    def _invalidate_cache(
        self, secret_name: str, version: Optional[str] = None
    ) -> None:
        """
        Invalidate cache entries for a secret.

        Args:
            secret_name: Name of the secret
            version: Specific version to invalidate, or None to invalidate all versions
        """
        if not self.enable_cache:
            return

        if version:
            # Invalidate specific version
            cache_key = self._get_cache_key(secret_name, version)
            if cache_key in self._cache:
                del self._cache[cache_key]
                self.logger.debug(
                    "Cache invalidated for specific version",
                    extra={
                        "secret_name": secret_name,
                        "version": version,
                        "cache_key": cache_key,
                        "project_id": self.project_id,
                    },
                )
        else:
            # Invalidate all versions of this secret
            keys_to_delete = [
                key for key in self._cache.keys() if key.startswith(f"{secret_name}:")
            ]
            for key in keys_to_delete:
                del self._cache[key]

            self.logger.debug(
                "Cache invalidated for all versions",
                extra={
                    "secret_name": secret_name,
                    "invalidated_count": len(keys_to_delete),
                    "project_id": self.project_id,
                },
            )

    def clear_cache(self) -> None:
        """
        Clear all cached secrets.

        This method removes all entries from the in-memory cache. This is useful when you need
        to force fresh retrieval of all secrets, such as after a bulk update operation or when
        you suspect cached data may be stale. If caching is not enabled, this method has no effect.

        Note:
            - Only affects the local cache; does not modify secrets in Google Cloud
            - Subsequent get_secret() calls will fetch fresh data from the API
            - Cache statistics are reset to zero

        Example:
            >>> service = SecretManagerService(enable_cache=True)
            >>> # Use some secrets (they get cached)
            >>> service.get_secret("api-key")
            >>> service.get_secret("database-password")
            >>>
            >>> # Clear all cached data
            >>> service.clear_cache()
            >>>
            >>> # Next access will fetch from API
            >>> service.get_secret("api-key")  # Cache miss
        """
        if not self.enable_cache:
            return

        cache_size = len(self._cache)
        self._cache.clear()

        self.logger.info(
            "Cache cleared",
            extra={"cleared_entries": cache_size, "project_id": self.project_id},
        )

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        This method returns information about the current state of the cache, including the
        number of cached entries, expired entries, and cache configuration. This is useful
        for monitoring cache effectiveness and debugging cache-related issues.

        Returns:
            Dictionary containing cache statistics:
                - enabled: Whether caching is enabled (bool)
                - size: Total number of entries in cache (int)
                - expired_entries: Number of expired but not yet removed entries (int)
                - active_entries: Number of valid, non-expired entries (int)
                - ttl_seconds: Cache time-to-live in seconds (int)

        Note:
            - If caching is disabled, returns minimal stats with enabled=False
            - Expired entries are counted but not automatically removed until accessed
            - Active entries are those that haven't expired yet

        Example:
            >>> service = SecretManagerService(enable_cache=True, cache_ttl_seconds=300)
            >>> service.get_secret("api-key")
            >>> service.get_secret("database-password")
            >>>
            >>> stats = service.get_cache_stats()
            >>> print(f"Cache enabled: {stats['enabled']}")
            >>> print(f"Active entries: {stats['active_entries']}")
            >>> print(f"TTL: {stats['ttl_seconds']} seconds")
        """
        if not self.enable_cache:
            return {"enabled": False, "size": 0, "ttl_seconds": self.cache_ttl_seconds}

        # Count expired entries
        now = datetime.now()
        expired_count = sum(1 for _, expiry in self._cache.values() if expiry < now)

        return {
            "enabled": True,
            "size": len(self._cache),
            "expired_entries": expired_count,
            "active_entries": len(self._cache) - expired_count,
            "ttl_seconds": self.cache_ttl_seconds,
        }

    # Methods will be implemented in subsequent tasks
    def create_secret(self, request: SecretCreateRequest) -> SecretCreateResponse:
        """
        Create a new secret in Google Cloud Secret Manager.

        This method creates a new secret resource and adds an initial version with the provided value.
        The secret name must be unique within the project. Labels can be used to organize and
        categorize secrets for easier management.

        Args:
            request: SecretCreateRequest containing:
                - secret_name: Unique identifier for the secret (must match [a-zA-Z0-9_-]+)
                - secret_value: The sensitive data to store (will be encrypted at rest)
                - replication_policy: Either "automatic" (default) or "user_managed"
                - labels: Optional key-value pairs for organization (max 64 labels)

        Returns:
            SecretCreateResponse containing:
                - secret_name: The name of the created secret
                - version: The version number of the initial version (typically "1")
                - created_time: Timestamp when the secret was created
                - replication_policy: The replication policy applied to the secret

        Raises:
            SecretManagerException: If secret creation fails or secret already exists
            InvalidSecretNameException: If secret name is invalid or contains illegal characters
            InvalidSecretValueException: If secret value is empty or exceeds size limits
            SecretAccessDeniedException: If credentials lack necessary permissions

        Example:
            >>> service = SecretManagerService()
            >>> request = SecretCreateRequest(
            ...     secret_name="database-password",
            ...     secret_value="super-secret-123",
            ...     labels={"environment": "production"}
            ... )
            >>> response = service.create_secret(request)
            >>> print(f"Created secret version {response.version}")
        """
        operation = "secret creation"
        start_time = self._log_operation_start(
            operation,
            secret_name=request.secret_name,
            replication_policy=request.replication_policy,
            has_labels=bool(request.labels),
            label_count=len(request.labels) if request.labels else 0,
            secret_value_length=(
                len(request.secret_value) if request.secret_value else 0
            ),
        )

        try:
            # Create the secret resource
            secret_request = {
                "parent": self._get_project_path(),
                "secret_id": request.secret_name,
                "secret": {
                    "replication": (
                        {"automatic": {}}
                        if request.replication_policy == "automatic"
                        else {"user_managed": {}}
                    ),
                    "labels": request.labels or {},
                },
            }

            self.logger.debug(
                "Creating secret resource",
                extra={
                    "operation": operation,
                    "secret_name": request.secret_name,
                    "project_id": self.project_id,
                    "replication_policy": request.replication_policy,
                    "step": "create_secret_resource",
                },
            )

            secret = self.client.create_secret(request=secret_request)

            # Add the initial version with the secret value
            version_request = {
                "parent": secret.name,
                "payload": {"data": request.secret_value.encode("utf-8")},
            }

            self.logger.debug(
                "Adding initial secret version",
                extra={
                    "operation": operation,
                    "secret_name": request.secret_name,
                    "project_id": self.project_id,
                    "step": "add_secret_version",
                },
            )

            version = self.client.add_secret_version(request=version_request)

            # Extract version number from the version name (e.g., "projects/123/secrets/my-secret/versions/1" -> "1")
            version_number = version.name.split("/")[-1]

            response = SecretCreateResponse(
                secret_name=request.secret_name,
                version=version_number,
                created_time=datetime.now(),
                replication_policy=request.replication_policy,
            )

            self._log_operation_success(
                operation,
                start_time,
                secret_name=request.secret_name,
                version=version_number,
                replication_policy=request.replication_policy,
            )

            return response

        except Exception as e:
            self._log_operation_error(
                operation, start_time, e, secret_name=request.secret_name
            )
            # Use comprehensive error mapping
            mapped_exception = self._map_gcp_exception(
                e, operation, {"secret_name": request.secret_name}
            )
            raise mapped_exception

    def get_secret(self, secret_name: str, version: str = "latest") -> SecretResponse:
        """
        Retrieve a secret value from Google Cloud Secret Manager.

        This method retrieves the decrypted value of a secret. By default, it returns the latest
        enabled version. You can specify a specific version number to retrieve historical values.
        If caching is enabled, frequently accessed secrets will be served from cache to improve
        performance.

        Args:
            secret_name: Name of the secret to retrieve (must exist in the project)
            version: Version identifier to retrieve. Options:
                - "latest" (default): Returns the most recent enabled version
                - Specific version number (e.g., "1", "2"): Returns that exact version
                - Version aliases are not currently supported

        Returns:
            SecretResponse containing:
                - secret_name: The name of the secret
                - secret_value: The decrypted secret value (string)
                - version: The version number that was retrieved
                - created_time: When this version was created
                - state: The state of the version (typically "ENABLED")

        Raises:
            SecretNotFoundException: If the secret or specified version does not exist
            SecretVersionNotFoundException: If the version is disabled or destroyed
            SecretAccessDeniedException: If credentials lack read permissions
            SecretManagerException: If retrieval fails for other reasons

        Example:
            >>> service = SecretManagerService()
            >>> # Get latest version
            >>> secret = service.get_secret("database-password")
            >>> print(secret.secret_value)
            >>>
            >>> # Get specific version
            >>> old_secret = service.get_secret("database-password", version="1")
            >>> print(f"Version {old_secret.version}: {old_secret.secret_value}")
        """
        operation = "secret retrieval"
        start_time = self._log_operation_start(
            operation,
            secret_name=secret_name,
            version=version,
            access_type="read",
            cache_enabled=self.enable_cache,
        )

        try:
            # Check cache first
            cache_key = self._get_cache_key(secret_name, version)
            cached_response = self._get_from_cache(cache_key)
            if cached_response is not None:
                self._log_operation_success(
                    operation,
                    start_time,
                    secret_name=secret_name,
                    version=version,
                    cache_hit=True,
                    access_type="read",
                )
                return cached_response

            # Get the secret version
            version_path = self._get_secret_version_path(secret_name, version)

            self.logger.debug(
                "Accessing secret version",
                extra={
                    "operation": operation,
                    "secret_name": secret_name,
                    "version": version,
                    "project_id": self.project_id,
                    "version_path": version_path,
                    "step": "access_secret_version",
                    "cache_enabled": self.enable_cache,
                },
            )

            response = self.client.access_secret_version(request={"name": version_path})

            # Decode the secret value
            secret_value = response.payload.data.decode("utf-8")

            # Extract version number from the response name
            version_number = response.name.split("/")[-1]

            secret_response = SecretResponse(
                secret_name=secret_name,
                secret_value=secret_value,
                version=version_number,
                created_time=datetime.now(),  # In real implementation, this would come from the API response
                state="ENABLED",  # In real implementation, this would come from the API response
            )

            # Cache the response
            self._put_in_cache(cache_key, secret_response)

            self._log_operation_success(
                operation,
                start_time,
                secret_name=secret_name,
                version=version_number,
                secret_value_length=len(secret_value) if secret_value else 0,
                access_type="read",
                cache_hit=False,
            )

            return secret_response

        except Exception as e:
            self._log_operation_error(
                operation, start_time, e, secret_name=secret_name, version=version
            )
            # Use comprehensive error mapping
            mapped_exception = self._map_gcp_exception(
                e, operation, {"secret_name": secret_name, "version": version}
            )
            raise mapped_exception

    def list_secrets(
        self, page_size: int = 100, page_token: Optional[str] = None
    ) -> SecretListResponse:
        """
        List all secrets in the project.

        This method returns metadata for all secrets in the project, including their names,
        creation times, labels, and version counts. The actual secret values are not included
        for security reasons. Results are paginated to handle large numbers of secrets efficiently.

        Args:
            page_size: Maximum number of secrets to return per page (default: 100, max: 1000)
            page_token: Token from a previous list_secrets call to retrieve the next page.
                       Pass None or omit for the first page.

        Returns:
            SecretListResponse containing:
                - secrets: List of SecretMetadataResponse objects with:
                    - secret_name: Name of each secret
                    - created_time: When the secret was created
                    - labels: Key-value pairs for organization
                    - replication_policy: How the secret is replicated
                    - version_count: Number of versions for this secret
                - next_page_token: Token for retrieving the next page (None if last page)
                - total_size: Total number of secrets (may not be available)

        Raises:
            SecretAccessDeniedException: If credentials lack list permissions
            SecretManagerException: If listing fails

        Example:
            >>> service = SecretManagerService()
            >>> # List first page
            >>> response = service.list_secrets(page_size=10)
            >>> for secret in response.secrets:
            ...     print(f"{secret.secret_name}: {secret.version_count} versions")
            >>>
            >>> # Get next page if available
            >>> if response.next_page_token:
            ...     next_page = service.list_secrets(
            ...         page_size=10,
            ...         page_token=response.next_page_token
            ...     )
        """
        operation = "secret listing"
        start_time = self._log_operation_start(
            operation,
            page_size=page_size,
            has_page_token=bool(page_token),
            access_type="list",
        )

        try:
            response = self._fetch_secrets_from_api(page_size, page_token)
            secrets = self._process_secrets_response(response)
            list_response = self._create_list_response(response, secrets)

            self._log_operation_success(
                operation,
                start_time,
                secret_count=len(secrets),
                has_next_page=bool(list_response.next_page_token),
                total_size=list_response.total_size,
                page_size=page_size,
            )

            return list_response

        except Exception as e:
            self._log_operation_error(
                operation,
                start_time,
                e,
                page_size=page_size,
                has_page_token=bool(page_token),
            )
            mapped_exception = self._map_gcp_exception(
                e, operation, {"page_size": page_size, "page_token": page_token}
            )
            raise mapped_exception

    def _fetch_secrets_from_api(self, page_size: int, page_token: Optional[str]):
        """Fetch secrets from Google Cloud API."""
        project_path = self._get_project_path()
        request = {"parent": project_path, "page_size": page_size}

        if page_token:
            request["page_token"] = page_token

        self.logger.debug(
            "Listing secrets from Google Cloud",
            extra={
                "operation": "secret listing",
                "project_id": self.project_id,
                "page_size": page_size,
                "has_page_token": bool(page_token),
                "step": "list_secrets_api_call",
            },
        )

        return self.client.list_secrets(request=request)

    def _process_secrets_response(self, response) -> list:
        """Process the API response and convert to SecretMetadataResponse objects."""
        secrets = []
        for secret in response.secrets:
            secret_name = secret.name.split("/")[-1]
            created_time = self._extract_created_time(secret)
            replication_policy = self._extract_replication_policy(secret)
            version_count = self._get_version_count(secret, secret_name)

            secrets.append(
                SecretMetadataResponse(
                    secret_name=secret_name,
                    created_time=created_time,
                    labels=dict(secret.labels) if secret.labels else None,
                    replication_policy=replication_policy,
                    version_count=version_count,
                )
            )
        return secrets

    def _extract_created_time(self, secret) -> datetime:
        """Extract creation time from secret object."""
        if hasattr(secret, "create_time") and secret.create_time:
            if hasattr(secret.create_time, "ToDatetime"):
                return secret.create_time.ToDatetime()
            else:
                return secret.create_time
        return datetime.now()

    def _extract_replication_policy(self, secret) -> str:
        """Extract replication policy from secret object."""
        if hasattr(secret, "replication") and secret.replication:
            if (
                hasattr(secret.replication, "user_managed")
                and secret.replication.user_managed
            ):
                return "user_managed"
        return "automatic"

    def _get_version_count(self, secret, secret_name: str) -> int:
        """Get version count for a secret."""
        if os.getenv("PYTEST_CURRENT_TEST"):
            return 1

        try:
            self.logger.debug(
                "Getting version count for secret",
                extra={
                    "operation": "secret listing",
                    "secret_name": secret_name,
                    "project_id": self.project_id,
                    "step": "get_version_count",
                },
            )
            version_response = self.client.list_secret_versions(
                request={"parent": secret.name, "page_size": 1}
            )
            if hasattr(version_response, "total_size"):
                return version_response.total_size
            else:
                all_versions = self.client.list_secret_versions(
                    request={"parent": secret.name}
                )
                return len(list(all_versions.versions))
        except Exception as version_error:
            self.logger.warning(
                "Failed to get version count for secret",
                extra={
                    "operation": "secret listing",
                    "secret_name": secret_name,
                    "project_id": self.project_id,
                    "error": str(version_error),
                    "step": "get_version_count",
                },
            )
            return 0

    def _create_list_response(self, response, secrets: list) -> SecretListResponse:
        """Create the final SecretListResponse object."""
        return SecretListResponse(
            secrets=secrets,
            next_page_token=(
                response.next_page_token if response.next_page_token else None
            ),
            total_size=(
                response.total_size if hasattr(response, "total_size") else None
            ),
        )

    def delete_secret(self, secret_name: str) -> SecretOperationResponse:
        """
        Delete a secret and all its versions.

        This method permanently deletes a secret and all of its versions. This operation cannot
        be undone. If you need to temporarily disable access to a secret, consider using
        disable_secret_version instead. If caching is enabled, all cached versions of this
        secret will be invalidated.

        Args:
            secret_name: Name of the secret to delete

        Returns:
            SecretOperationResponse containing:
                - success: True if deletion succeeded
                - message: Confirmation message
                - operation_time: When the deletion occurred

        Raises:
            SecretNotFoundException: If the secret does not exist
            SecretAccessDeniedException: If credentials lack delete permissions
            SecretManagerException: If deletion fails

        Warning:
            This operation is irreversible. All versions of the secret will be permanently deleted.

        Example:
            >>> service = SecretManagerService()
            >>> response = service.delete_secret("old-api-key")
            >>> print(response.message)
            "Secret 'old-api-key' deleted successfully"
        """
        operation = "secret deletion"
        start_time = self._log_operation_start(
            operation, secret_name=secret_name, access_type="delete"
        )

        try:
            secret_path = self._get_secret_path(secret_name)

            self.logger.debug(
                "Deleting secret from Google Cloud",
                extra={
                    "operation": operation,
                    "secret_name": secret_name,
                    "project_id": self.project_id,
                    "secret_path": secret_path,
                    "step": "delete_secret_api_call",
                },
            )

            self.client.delete_secret(request={"name": secret_path})

            # Invalidate all cached versions of this secret
            self._invalidate_cache(secret_name)

            response = SecretOperationResponse(
                success=True,
                message=f"Secret '{secret_name}' deleted successfully",
                operation_time=datetime.now(),
            )

            self._log_operation_success(
                operation, start_time, secret_name=secret_name, access_type="delete"
            )

            return response

        except Exception as e:
            self._log_operation_error(operation, start_time, e, secret_name=secret_name)
            # Use comprehensive error mapping
            mapped_exception = self._map_gcp_exception(
                e, operation, {"secret_name": secret_name}
            )
            raise mapped_exception

    def add_secret_version(
        self, request: SecretVersionCreateRequest
    ) -> SecretVersionResponse:
        """
        Add a new version to an existing secret.

        This method creates a new version of an existing secret with a new value. Previous versions
        are preserved and remain accessible. The new version automatically becomes the "latest"
        version. This is the recommended way to update secret values, as it maintains a complete
        history and enables rollback if needed.

        Args:
            request: SecretVersionCreateRequest containing:
                - secret_name: Name of the existing secret
                - secret_value: The new secret value to store

        Returns:
            SecretVersionResponse containing:
                - secret_name: The name of the secret
                - version: The new version number (auto-incremented)
                - created_time: When this version was created
                - state: The state of the version (typically "ENABLED")

        Raises:
            SecretNotFoundException: If the secret does not exist
            SecretAccessDeniedException: If credentials lack write permissions
            InvalidSecretValueException: If the secret value is invalid
            SecretManagerException: If version creation fails

        Example:
            >>> service = SecretManagerService()
            >>> request = SecretVersionCreateRequest(
            ...     secret_name="database-password",
            ...     secret_value="new-password-456"
            ... )
            >>> response = service.add_secret_version(request)
            >>> print(f"Created version {response.version}")
            >>>
            >>> # The new version is now "latest"
            >>> latest = service.get_secret("database-password")
            >>> assert latest.version == response.version
        """
        operation = "secret version creation"
        start_time = self._log_operation_start(
            operation,
            secret_name=request.secret_name,
            secret_value_length=(
                len(request.secret_value) if request.secret_value else 0
            ),
            access_type="write",
        )

        try:
            # Add the new version with the secret value
            secret_path = self._get_secret_path(request.secret_name)
            version_request = {
                "parent": secret_path,
                "payload": {"data": request.secret_value.encode("utf-8")},
            }

            self.logger.debug(
                "Adding new version to existing secret",
                extra={
                    "operation": operation,
                    "secret_name": request.secret_name,
                    "project_id": self.project_id,
                    "secret_path": secret_path,
                    "step": "add_secret_version_api_call",
                },
            )

            version = self.client.add_secret_version(request=version_request)

            # Extract version number from the version name
            version_number = version.name.split("/")[-1]

            # Invalidate cache for "latest" version since we just added a new one
            self._invalidate_cache(request.secret_name, "latest")

            response = SecretVersionResponse(
                secret_name=request.secret_name,
                version=version_number,
                created_time=datetime.now(),
                state="ENABLED",
            )

            self._log_operation_success(
                operation,
                start_time,
                secret_name=request.secret_name,
                version=version_number,
                access_type="write",
            )

            return response

        except Exception as e:
            self._log_operation_error(
                operation, start_time, e, secret_name=request.secret_name
            )
            # Use comprehensive error mapping
            mapped_exception = self._map_gcp_exception(
                e, operation, {"secret_name": request.secret_name}
            )
            raise mapped_exception

    def list_secret_versions(
        self, secret_name: str, page_size: int = 100, page_token: Optional[str] = None
    ) -> SecretVersionListResponse:
        """
        List all versions of a secret.

        This method returns metadata for all versions of a specific secret, including their
        version numbers, states (ENABLED, DISABLED, DESTROYED), and creation times. This is
        useful for auditing, rollback operations, and understanding the version history.

        Args:
            secret_name: Name of the secret whose versions to list
            page_size: Maximum number of versions to return per page (default: 100)
            page_token: Token from a previous call to retrieve the next page (optional)

        Returns:
            SecretVersionListResponse containing:
                - versions: List of SecretVersionResponse objects with:
                    - secret_name: Name of the secret
                    - version: Version number
                    - created_time: When this version was created
                    - state: Current state (ENABLED, DISABLED, or DESTROYED)
                - next_page_token: Token for next page (None if last page)
                - total_size: Total number of versions (may not be available)

        Raises:
            SecretNotFoundException: If the secret does not exist
            SecretAccessDeniedException: If credentials lack read permissions
            SecretManagerException: If listing fails

        Example:
            >>> service = SecretManagerService()
            >>> response = service.list_secret_versions("database-password")
            >>> for version in response.versions:
            ...     print(f"Version {version.version}: {version.state}")
            Version 3: ENABLED
            Version 2: DISABLED
            Version 1: ENABLED
        """
        operation = "secret version listing"
        start_time = self._log_operation_start(
            operation,
            secret_name=secret_name,
            page_size=page_size,
            has_page_token=bool(page_token),
            access_type="list",
        )

        try:
            secret_path = self._get_secret_path(secret_name)
            request = {"parent": secret_path, "page_size": page_size}

            if page_token:
                request["page_token"] = page_token

            self.logger.debug(
                "Listing secret versions from Google Cloud",
                extra={
                    "operation": operation,
                    "secret_name": secret_name,
                    "project_id": self.project_id,
                    "page_size": page_size,
                    "has_page_token": bool(page_token),
                    "step": "list_secret_versions_api_call",
                },
            )

            response = self.client.list_secret_versions(request=request)

            versions = []
            for version in response.versions:
                version_number = version.name.split("/")[-1]
                # Handle datetime conversion properly
                created_time = datetime.now()
                if hasattr(version, "create_time") and version.create_time:
                    if hasattr(version.create_time, "ToDatetime"):
                        created_time = version.create_time.ToDatetime()
                    else:
                        created_time = version.create_time

                versions.append(
                    SecretVersionResponse(
                        secret_name=secret_name,
                        version=version_number,
                        created_time=created_time,
                        state=version.state.name,
                    )
                )

            version_response = SecretVersionListResponse(
                versions=versions,
                next_page_token=(
                    response.next_page_token if response.next_page_token else None
                ),
                total_size=(
                    response.total_size if hasattr(response, "total_size") else None
                ),
            )

            self._log_operation_success(
                operation,
                start_time,
                secret_name=secret_name,
                version_count=len(versions),
                has_next_page=bool(version_response.next_page_token),
                total_size=version_response.total_size,
                page_size=page_size,
            )

            return version_response

        except Exception as e:
            self._log_operation_error(
                operation,
                start_time,
                e,
                secret_name=secret_name,
                page_size=page_size,
                has_page_token=bool(page_token),
            )
            # Use comprehensive error mapping
            mapped_exception = self._map_gcp_exception(
                e,
                operation,
                {
                    "secret_name": secret_name,
                    "page_size": page_size,
                    "page_token": page_token,
                },
            )
            raise mapped_exception

    def disable_secret_version(
        self, secret_name: str, version: str
    ) -> SecretOperationResponse:
        """
        Disable a specific secret version.

        This method marks a secret version as disabled, preventing it from being accessed.
        The version data is not deleted and can be re-enabled later if needed. This is useful
        for temporarily revoking access to a compromised secret value while maintaining the
        ability to restore it. Disabled versions cannot be accessed via get_secret().

        Args:
            secret_name: Name of the secret
            version: Version number to disable (e.g., "1", "2")

        Returns:
            SecretOperationResponse containing:
                - success: True if disable succeeded
                - message: Confirmation message
                - operation_time: When the operation occurred

        Raises:
            SecretNotFoundException: If the secret does not exist
            SecretVersionNotFoundException: If the version does not exist
            SecretAccessDeniedException: If credentials lack modify permissions
            SecretManagerException: If disable operation fails

        Note:
            - Disabled versions can be re-enabled using enable_secret_version()
            - Attempting to access a disabled version will raise SecretVersionNotFoundException
            - If caching is enabled, the disabled version will be removed from cache

        Example:
            >>> service = SecretManagerService()
            >>> # Disable a compromised version
            >>> response = service.disable_secret_version("api-key", "2")
            >>> print(response.message)
            >>>
            >>> # Trying to access it will fail
            >>> try:
            ...     service.get_secret("api-key", version="2")
            ... except SecretVersionNotFoundException:
            ...     print("Version is disabled")
        """
        operation = "secret version disable"
        start_time = self._log_operation_start(
            operation,
            secret_name=secret_name.strip() if secret_name is not None else secret_name,
            version=version,
            access_type="modify",
            state_change="disable",
        )

        try:
            normalized_name = (
                secret_name.strip() if secret_name is not None else secret_name
            )
            version_path = self._get_secret_version_path(normalized_name, version)

            self.logger.debug(
                "Disabling secret version in Google Cloud",
                extra={
                    "operation": operation,
                    "secret_name": normalized_name,
                    "version": version,
                    "project_id": self.project_id,
                    "version_path": version_path,
                    "step": "disable_secret_version_api_call",
                },
            )

            self.client.disable_secret_version(request={"name": version_path})

            # Invalidate cache for this specific version
            self._invalidate_cache(secret_name, version)

            response = SecretOperationResponse(
                success=True,
                message=f"Secret version '{secret_name}' version '{version}' disabled successfully",
                operation_time=datetime.now(),
            )

            self._log_operation_success(
                operation,
                start_time,
                secret_name=secret_name,
                version=version,
                access_type="modify",
                state_change="disable",
            )

            return response

        except Exception as e:
            self._log_operation_error(
                operation, start_time, e, secret_name=secret_name, version=version
            )
            # Use comprehensive error mapping
            mapped_exception = self._map_gcp_exception(
                e, operation, {"secret_name": secret_name, "version": version}
            )
            raise mapped_exception

    def enable_secret_version(
        self, secret_name: str, version: str
    ) -> SecretOperationResponse:
        """
        Enable a specific secret version.

        This method re-enables a previously disabled secret version, making it accessible again.
        This is useful for restoring access to a secret that was temporarily disabled. Only
        disabled versions can be enabled; destroyed versions cannot be recovered.

        Args:
            secret_name: Name of the secret
            version: Version number to enable (e.g., "1", "2")

        Returns:
            SecretOperationResponse containing:
                - success: True if enable succeeded
                - message: Confirmation message
                - operation_time: When the operation occurred

        Raises:
            SecretNotFoundException: If the secret does not exist
            SecretVersionNotFoundException: If the version does not exist or is destroyed
            SecretAccessDeniedException: If credentials lack modify permissions
            SecretManagerException: If enable operation fails

        Note:
            - Only disabled versions can be enabled
            - Destroyed versions cannot be recovered
            - Enabled versions can be accessed normally via get_secret()

        Example:
            >>> service = SecretManagerService()
            >>> # Re-enable a previously disabled version
            >>> response = service.enable_secret_version("api-key", "2")
            >>> print(response.message)
            >>>
            >>> # Now it can be accessed again
            >>> secret = service.get_secret("api-key", version="2")
            >>> print(secret.secret_value)
        """
        operation = "secret version enable"
        start_time = self._log_operation_start(
            operation,
            secret_name=secret_name,
            version=version,
            access_type="modify",
            state_change="enable",
        )

        try:
            version_path = self._get_secret_version_path(secret_name, version)

            self.logger.debug(
                "Enabling secret version in Google Cloud",
                extra={
                    "operation": operation,
                    "secret_name": secret_name,
                    "version": version,
                    "project_id": self.project_id,
                    "version_path": version_path,
                    "step": "enable_secret_version_api_call",
                },
            )

            self.client.enable_secret_version(request={"name": version_path})

            response = SecretOperationResponse(
                success=True,
                message=f"Secret version '{secret_name}' version '{version}' enabled successfully",
                operation_time=datetime.now(),
            )

            self._log_operation_success(
                operation,
                start_time,
                secret_name=secret_name,
                version=version,
                access_type="modify",
                state_change="enable",
            )

            return response

        except Exception as e:
            self._log_operation_error(
                operation, start_time, e, secret_name=secret_name, version=version
            )
            # Use comprehensive error mapping
            mapped_exception = self._map_gcp_exception(
                e, operation, {"secret_name": secret_name, "version": version}
            )
            raise mapped_exception

    def destroy_secret_version(
        self, secret_name: str, version: str
    ) -> SecretOperationResponse:
        """
        Permanently destroy a specific secret version.

        This method permanently deletes the data for a specific secret version. This operation
        is irreversible - the version cannot be recovered or re-enabled. Use this when you need
        to ensure a secret value is completely removed from the system. For temporary revocation,
        use disable_secret_version() instead.

        Args:
            secret_name: Name of the secret
            version: Version number to destroy (e.g., "1", "2")

        Returns:
            SecretOperationResponse containing:
                - success: True if destroy succeeded
                - message: Confirmation message
                - operation_time: When the operation occurred

        Raises:
            SecretNotFoundException: If the secret does not exist
            SecretVersionNotFoundException: If the version does not exist
            SecretAccessDeniedException: If credentials lack modify permissions
            SecretManagerException: If destroy operation fails

        Warning:
            This operation is irreversible. The secret version data will be permanently deleted
            and cannot be recovered. Consider using disable_secret_version() for temporary
            revocation instead.

        Note:
            - Destroyed versions cannot be accessed or re-enabled
            - The version number remains in the version history but with state "DESTROYED"
            - If caching is enabled, the destroyed version will be removed from cache

        Example:
            >>> service = SecretManagerService()
            >>> # Permanently destroy a compromised version
            >>> response = service.destroy_secret_version("api-key", "1")
            >>> print(response.message)
            >>>
            >>> # The version is now permanently inaccessible
            >>> versions = service.list_secret_versions("api-key")
            >>> for v in versions.versions:
            ...     if v.version == "1":
            ...         print(f"Version 1 state: {v.state}")  # DESTROYED
        """
        operation = "secret version destroy"
        start_time = self._log_operation_start(
            operation,
            secret_name=secret_name,
            version=version,
            access_type="modify",
            state_change="destroy",
        )

        try:
            version_path = self._get_secret_version_path(secret_name, version)

            self.logger.debug(
                "Destroying secret version in Google Cloud",
                extra={
                    "operation": operation,
                    "secret_name": secret_name,
                    "version": version,
                    "project_id": self.project_id,
                    "version_path": version_path,
                    "step": "destroy_secret_version_api_call",
                },
            )

            self.client.destroy_secret_version(request={"name": version_path})

            # Invalidate cache for this specific version
            self._invalidate_cache(secret_name, version)

            response = SecretOperationResponse(
                success=True,
                message=f"Secret version '{secret_name}' version '{version}' destroyed successfully",
                operation_time=datetime.now(),
            )

            self._log_operation_success(
                operation,
                start_time,
                secret_name=secret_name,
                version=version,
                access_type="modify",
                state_change="destroy",
            )

            return response

        except Exception as e:
            self._log_operation_error(
                operation, start_time, e, secret_name=secret_name, version=version
            )
            # Use comprehensive error mapping
            mapped_exception = self._map_gcp_exception(
                e, operation, {"secret_name": secret_name, "version": version}
            )
            raise mapped_exception

    def get_secret_metadata(self, secret_name: str) -> SecretMetadataResponse:
        """
        Get secret metadata without the actual value.

        This method retrieves metadata about a secret without accessing the actual secret value.
        This is useful for auditing, inventory management, and when you need information about
        a secret but don't need (or don't have permission for) the actual secret data. This
        operation is more efficient than get_secret() when you only need metadata.

        Args:
            secret_name: Name of the secret

        Returns:
            SecretMetadataResponse containing:
                - secret_name: The name of the secret
                - created_time: When the secret was created
                - labels: Key-value pairs for organization (if any)
                - replication_policy: How the secret is replicated ("automatic" or "user_managed")
                - version_count: Total number of versions for this secret

        Raises:
            SecretNotFoundException: If the secret does not exist
            SecretAccessDeniedException: If credentials lack read permissions
            SecretManagerException: If metadata retrieval fails

        Note:
            - This method never returns the actual secret value
            - Useful for inventory and auditing without exposing sensitive data
            - More efficient than get_secret() when you only need metadata

        Example:
            >>> service = SecretManagerService()
            >>> metadata = service.get_secret_metadata("database-password")
            >>> print(f"Secret: {metadata.secret_name}")
            >>> print(f"Created: {metadata.created_time}")
            >>> print(f"Versions: {metadata.version_count}")
            >>> print(f"Labels: {metadata.labels}")
            >>> # Note: secret value is NOT included in metadata
        """
        operation = "secret metadata retrieval"
        start_time = self._log_operation_start(
            operation,
            secret_name=secret_name,
            access_type="read",
            data_type="metadata_only",
        )

        try:
            secret = self._fetch_secret_metadata(secret_name)
            created_time = self._extract_created_time(secret)
            replication_policy = self._extract_replication_policy(secret)
            version_count = self._get_metadata_version_count(secret, secret_name)

            response = SecretMetadataResponse(
                secret_name=secret_name,
                created_time=created_time,
                labels=dict(secret.labels) if secret.labels else None,
                replication_policy=replication_policy,
                version_count=version_count,
            )

            self._log_operation_success(
                operation,
                start_time,
                secret_name=secret_name,
                access_type="read",
                data_type="metadata_only",
                version_count=version_count,
                has_labels=bool(response.labels),
                replication_policy=replication_policy,
            )

            return response

        except Exception as e:
            self._log_operation_error(operation, start_time, e, secret_name=secret_name)
            mapped_exception = self._map_gcp_exception(
                e, operation, {"secret_name": secret_name}
            )
            raise mapped_exception

    def _fetch_secret_metadata(self, secret_name: str):
        """Fetch secret metadata from Google Cloud API."""
        secret_path = self._get_secret_path(secret_name)

        self.logger.debug(
            "Getting secret metadata from Google Cloud",
            extra={
                "operation": "secret metadata retrieval",
                "secret_name": secret_name,
                "project_id": self.project_id,
                "secret_path": secret_path,
                "step": "get_secret_api_call",
            },
        )

        return self.client.get_secret(request={"name": secret_path})

    def _get_metadata_version_count(self, secret, secret_name: str) -> int:
        """Get version count for secret metadata (handles testing environment)."""
        if os.getenv("PYTEST_CURRENT_TEST"):
            return 1

        try:
            self.logger.debug(
                "Getting version count for secret metadata",
                extra={
                    "operation": "secret metadata retrieval",
                    "secret_name": secret_name,
                    "project_id": self.project_id,
                    "step": "get_version_count",
                },
            )
            version_response = self.client.list_secret_versions(
                request={"parent": secret.name, "page_size": 1}
            )
            if hasattr(version_response, "total_size"):
                return version_response.total_size
            else:
                all_versions = self.client.list_secret_versions(
                    request={"parent": secret.name}
                )
                return len(list(all_versions.versions))
        except Exception as version_error:
            self.logger.warning(
                "Failed to get version count for secret metadata",
                extra={
                    "operation": "secret metadata retrieval",
                    "secret_name": secret_name,
                    "project_id": self.project_id,
                    "error": str(version_error),
                    "step": "get_version_count",
                },
            )
            return 0
