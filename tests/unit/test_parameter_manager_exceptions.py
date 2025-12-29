"""
Unit tests for Parameter Manager exception classes.

Tests the exception hierarchy and behavior following the Spartan Framework
testing patterns.
"""

import pytest

from app.exceptions.parameter_manager import (
    InvalidParameterNameException,
    InvalidParameterValueException,
    ParameterAccessDeniedException,
    ParameterAlreadyExistsException,
    ParameterConnectionException,
    ParameterInternalErrorException,
    ParameterManagerException,
    ParameterNotFoundException,
    ParameterQuotaExceededException,
    ParameterTimeoutException,
    ParameterUnavailableException,
    ParameterVersionNotFoundException,
)


def test_parameter_manager_exception_base():
    """Test that ParameterManagerException is the base exception."""
    exception = ParameterManagerException("Test error")
    assert str(exception) == "Test error"
    assert isinstance(exception, Exception)


def test_parameter_not_found_exception():
    """Test ParameterNotFoundException inherits from base."""
    exception = ParameterNotFoundException("Parameter not found")
    assert str(exception) == "Parameter not found"
    assert isinstance(exception, ParameterManagerException)


def test_parameter_already_exists_exception():
    """Test ParameterAlreadyExistsException inherits from base."""
    exception = ParameterAlreadyExistsException("Parameter already exists")
    assert str(exception) == "Parameter already exists"
    assert isinstance(exception, ParameterManagerException)


def test_parameter_access_denied_exception():
    """Test ParameterAccessDeniedException inherits from base."""
    exception = ParameterAccessDeniedException("Access denied")
    assert str(exception) == "Access denied"
    assert isinstance(exception, ParameterManagerException)


def test_parameter_version_not_found_exception():
    """Test ParameterVersionNotFoundException inherits from base."""
    exception = ParameterVersionNotFoundException("Version not found")
    assert str(exception) == "Version not found"
    assert isinstance(exception, ParameterManagerException)


def test_invalid_parameter_name_exception():
    """Test InvalidParameterNameException inherits from base."""
    exception = InvalidParameterNameException("Invalid name")
    assert str(exception) == "Invalid name"
    assert isinstance(exception, ParameterManagerException)


def test_invalid_parameter_value_exception():
    """Test InvalidParameterValueException inherits from base."""
    exception = InvalidParameterValueException("Invalid value")
    assert str(exception) == "Invalid value"
    assert isinstance(exception, ParameterManagerException)


def test_parameter_connection_exception():
    """Test ParameterConnectionException inherits from base."""
    exception = ParameterConnectionException("Connection failed")
    assert str(exception) == "Connection failed"
    assert isinstance(exception, ParameterManagerException)


def test_parameter_quota_exceeded_exception():
    """Test ParameterQuotaExceededException inherits from base."""
    exception = ParameterQuotaExceededException("Quota exceeded")
    assert str(exception) == "Quota exceeded"
    assert isinstance(exception, ParameterManagerException)


def test_parameter_internal_error_exception():
    """Test ParameterInternalErrorException inherits from base."""
    exception = ParameterInternalErrorException("Internal error")
    assert str(exception) == "Internal error"
    assert isinstance(exception, ParameterManagerException)


def test_parameter_unavailable_exception():
    """Test ParameterUnavailableException inherits from base."""
    exception = ParameterUnavailableException("Service unavailable")
    assert str(exception) == "Service unavailable"
    assert isinstance(exception, ParameterManagerException)


def test_parameter_timeout_exception():
    """Test ParameterTimeoutException inherits from base."""
    exception = ParameterTimeoutException("Operation timed out")
    assert str(exception) == "Operation timed out"
    assert isinstance(exception, ParameterManagerException)


def test_exception_can_be_raised_and_caught():
    """Test that exceptions can be raised and caught properly."""
    with pytest.raises(ParameterNotFoundException) as exc_info:
        raise ParameterNotFoundException("Test parameter not found")

    assert "Test parameter not found" in str(exc_info.value)


def test_exception_hierarchy():
    """Test that all exceptions inherit from ParameterManagerException."""
    exceptions = [
        ParameterNotFoundException,
        ParameterAlreadyExistsException,
        ParameterAccessDeniedException,
        ParameterVersionNotFoundException,
        InvalidParameterNameException,
        InvalidParameterValueException,
        ParameterConnectionException,
        ParameterQuotaExceededException,
        ParameterInternalErrorException,
        ParameterUnavailableException,
        ParameterTimeoutException,
    ]

    for exc_class in exceptions:
        assert issubclass(exc_class, ParameterManagerException)


def test_exceptions_default_messages():
    """Test that exceptions have appropriate default messages."""
    assert "Parameter Manager operation failed" in str(ParameterManagerException())
    assert "Parameter not found" in str(ParameterNotFoundException())
    assert "Parameter already exists" in str(ParameterAlreadyExistsException())
    assert "Access to parameter denied" in str(ParameterAccessDeniedException())
    assert "Parameter version not found" in str(ParameterVersionNotFoundException())
    assert "Invalid parameter name" in str(InvalidParameterNameException())
    assert "Invalid parameter value" in str(InvalidParameterValueException())
    assert "Network connectivity issue" in str(ParameterConnectionException())
    assert "Quota exceeded" in str(ParameterQuotaExceededException())
    assert "Internal server error" in str(ParameterInternalErrorException())
    assert "Service temporarily unavailable" in str(ParameterUnavailableException())
    assert "Operation timed out" in str(ParameterTimeoutException())


def test_exceptions_custom_messages():
    """Test that exceptions properly handle custom messages."""
    custom_message = "Custom error occurred"

    exceptions = [
        ParameterManagerException,
        ParameterNotFoundException,
        ParameterAlreadyExistsException,
        ParameterAccessDeniedException,
        ParameterVersionNotFoundException,
        InvalidParameterNameException,
        InvalidParameterValueException,
        ParameterConnectionException,
        ParameterQuotaExceededException,
        ParameterInternalErrorException,
        ParameterUnavailableException,
        ParameterTimeoutException,
    ]

    for exception_class in exceptions:
        exc = exception_class(custom_message)
        assert str(exc) == custom_message
        assert exc.message == custom_message


def test_parameter_not_found_exception_specific():
    """Test ParameterNotFoundException for requirement 5.1."""
    parameter_name = "test-parameter"
    exc = ParameterNotFoundException(f"Parameter '{parameter_name}' not found")
    assert "test-parameter" in str(exc)
    assert "not found" in str(exc)


def test_parameter_access_denied_exception_specific():
    """Test ParameterAccessDeniedException for requirement 5.3."""
    parameter_name = "protected-parameter"
    exc = ParameterAccessDeniedException(
        f"Access denied to parameter '{parameter_name}'"
    )
    assert "protected-parameter" in str(exc)
    assert "Access denied" in str(exc)


def test_invalid_input_exceptions_specific():
    """Test validation exceptions for requirement 5.4."""
    # Test invalid name
    name_exc = InvalidParameterNameException("Parameter name cannot be empty")
    assert "name" in str(name_exc)
    assert "empty" in str(name_exc)

    # Test invalid value
    value_exc = InvalidParameterValueException("Parameter value exceeds 1 MiB limit")
    assert "value" in str(value_exc)
    assert "1 MiB" in str(value_exc)


def test_all_exceptions_can_be_caught_as_base():
    """Test that all exceptions can be caught as ParameterManagerException."""
    exceptions = [
        ParameterNotFoundException(),
        ParameterAlreadyExistsException(),
        ParameterAccessDeniedException(),
        ParameterVersionNotFoundException(),
        InvalidParameterNameException(),
        InvalidParameterValueException(),
        ParameterConnectionException(),
        ParameterQuotaExceededException(),
        ParameterInternalErrorException(),
        ParameterUnavailableException(),
        ParameterTimeoutException(),
    ]

    for exception in exceptions:
        with pytest.raises(ParameterManagerException):
            raise exception
