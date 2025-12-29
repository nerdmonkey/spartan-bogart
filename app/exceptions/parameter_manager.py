# Parameter Manager Exception Classes
# This file contains all custom exceptions for the Parameter Manager service


class ParameterManagerException(Exception):
    """Base exception for all Parameter Manager operations."""

    def __init__(self, message="Parameter Manager operation failed"):
        self.message = message
        super().__init__(self.message)


class ParameterNotFoundException(ParameterManagerException):
    """Raised when a requested parameter is not found."""

    def __init__(self, message="Parameter not found"):
        self.message = message
        super().__init__(self.message)


class ParameterAlreadyExistsException(ParameterManagerException):
    """Raised when attempting to create a parameter that already exists."""

    def __init__(self, message="Parameter already exists"):
        self.message = message
        super().__init__(self.message)


class ParameterAccessDeniedException(ParameterManagerException):
    """Raised when access to a parameter is denied."""

    def __init__(self, message="Access to parameter denied"):
        self.message = message
        super().__init__(self.message)


class ParameterVersionNotFoundException(ParameterManagerException):
    """Raised when a requested parameter version is not found."""

    def __init__(self, message="Parameter version not found"):
        self.message = message
        super().__init__(self.message)


class InvalidParameterNameException(ParameterManagerException):
    """Raised when a parameter name is invalid."""

    def __init__(self, message="Invalid parameter name"):
        self.message = message
        super().__init__(self.message)


class InvalidParameterValueException(ParameterManagerException):
    """Raised when a parameter value is invalid."""

    def __init__(self, message="Invalid parameter value"):
        self.message = message
        super().__init__(self.message)


class ParameterConnectionException(ParameterManagerException):
    """Raised when network connectivity issues occur."""

    def __init__(self, message="Network connectivity issue"):
        self.message = message
        super().__init__(self.message)


class ParameterQuotaExceededException(ParameterManagerException):
    """Raised when Google Cloud quotas are exceeded."""

    def __init__(self, message="Quota exceeded"):
        self.message = message
        super().__init__(self.message)


class ParameterInternalErrorException(ParameterManagerException):
    """Raised when Google Cloud internal errors occur."""

    def __init__(self, message="Internal server error"):
        self.message = message
        super().__init__(self.message)


class ParameterUnavailableException(ParameterManagerException):
    """Raised when the Parameter Manager service is temporarily unavailable."""

    def __init__(self, message="Service temporarily unavailable"):
        self.message = message
        super().__init__(self.message)


class ParameterTimeoutException(ParameterManagerException):
    """Raised when operations timeout."""

    def __init__(self, message="Operation timed out"):
        self.message = message
        super().__init__(self.message)
