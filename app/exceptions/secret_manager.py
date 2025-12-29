# Secret Manager Exception Classes
# This file will contain all custom exceptions for the Secret Manager service


class SecretManagerException(Exception):
    """Base exception for all Secret Manager operations."""

    def __init__(self, message="Secret Manager operation failed"):
        self.message = message
        super().__init__(self.message)


class SecretNotFoundException(SecretManagerException):
    """Raised when a requested secret is not found."""

    def __init__(self, message="Secret not found"):
        self.message = message
        super().__init__(self.message)


class SecretAlreadyExistsException(SecretManagerException):
    """Raised when attempting to create a secret that already exists."""

    def __init__(self, message="Secret already exists"):
        self.message = message
        super().__init__(self.message)


class SecretAccessDeniedException(SecretManagerException):
    """Raised when access to a secret is denied."""

    def __init__(self, message="Access to secret denied"):
        self.message = message
        super().__init__(self.message)


class SecretVersionNotFoundException(SecretManagerException):
    """Raised when a requested secret version is not found."""

    def __init__(self, message="Secret version not found"):
        self.message = message
        super().__init__(self.message)


class InvalidSecretNameException(SecretManagerException):
    """Raised when a secret name is invalid."""

    def __init__(self, message="Invalid secret name"):
        self.message = message
        super().__init__(self.message)


class InvalidSecretValueException(SecretManagerException):
    """Raised when a secret value is invalid."""

    def __init__(self, message="Invalid secret value"):
        self.message = message
        super().__init__(self.message)


class SecretConnectionException(SecretManagerException):
    """Raised when network connectivity issues occur."""

    def __init__(self, message="Network connectivity issue"):
        self.message = message
        super().__init__(self.message)


class SecretQuotaExceededException(SecretManagerException):
    """Raised when Google Cloud quotas are exceeded."""

    def __init__(self, message="Quota exceeded"):
        self.message = message
        super().__init__(self.message)


class SecretInternalErrorException(SecretManagerException):
    """Raised when Google Cloud internal errors occur."""

    def __init__(self, message="Internal server error"):
        self.message = message
        super().__init__(self.message)


class SecretUnavailableException(SecretManagerException):
    """Raised when the Secret Manager service is temporarily unavailable."""

    def __init__(self, message="Service temporarily unavailable"):
        self.message = message
        super().__init__(self.message)


class SecretTimeoutException(SecretManagerException):
    """Raised when operations timeout."""

    def __init__(self, message="Operation timed out"):
        self.message = message
        super().__init__(self.message)
