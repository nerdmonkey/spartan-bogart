# Unit tests for Secret Manager exceptions
# This file will contain tests for the secret manager exception classes

import pytest

from app.exceptions.secret_manager import (
    InvalidSecretNameException,
    InvalidSecretValueException,
    SecretAccessDeniedException,
    SecretAlreadyExistsException,
    SecretManagerException,
    SecretNotFoundException,
    SecretVersionNotFoundException,
)


def test_secret_manager_exception_hierarchy():
    """Test that all secret manager exceptions inherit from SecretManagerException."""
    exceptions = [
        SecretNotFoundException,
        SecretAlreadyExistsException,
        SecretAccessDeniedException,
        SecretVersionNotFoundException,
        InvalidSecretNameException,
        InvalidSecretValueException,
    ]

    for exception_class in exceptions:
        assert issubclass(exception_class, SecretManagerException)
        assert issubclass(exception_class, Exception)


def test_secret_manager_exceptions_can_be_raised():
    """Test that all secret manager exceptions can be instantiated and raised."""
    test_message = "Test error message"

    exceptions = [
        SecretManagerException,
        SecretNotFoundException,
        SecretAlreadyExistsException,
        SecretAccessDeniedException,
        SecretVersionNotFoundException,
        InvalidSecretNameException,
        InvalidSecretValueException,
    ]

    for exception_class in exceptions:
        with pytest.raises(exception_class) as exc_info:
            raise exception_class(test_message)
        assert str(exc_info.value) == test_message


def test_secret_manager_exceptions_default_messages():
    """Test that exceptions have appropriate default messages."""
    # Test default messages match expected patterns
    assert "Secret Manager operation failed" in str(SecretManagerException())
    assert "Secret not found" in str(SecretNotFoundException())
    assert "Secret already exists" in str(SecretAlreadyExistsException())
    assert "Access to secret denied" in str(SecretAccessDeniedException())
    assert "Secret version not found" in str(SecretVersionNotFoundException())
    assert "Invalid secret name" in str(InvalidSecretNameException())
    assert "Invalid secret value" in str(InvalidSecretValueException())


def test_secret_manager_exceptions_custom_messages():
    """Test that exceptions properly handle custom messages."""
    custom_message = "Custom error occurred"

    exceptions = [
        SecretManagerException,
        SecretNotFoundException,
        SecretAlreadyExistsException,
        SecretAccessDeniedException,
        SecretVersionNotFoundException,
        InvalidSecretNameException,
        InvalidSecretValueException,
    ]

    for exception_class in exceptions:
        exc = exception_class(custom_message)
        assert str(exc) == custom_message
        assert exc.message == custom_message


def test_secret_not_found_exception_specific():
    """Test SecretNotFoundException for requirement 4.1."""
    secret_name = "test-secret"
    exc = SecretNotFoundException(f"Secret '{secret_name}' not found")
    assert "test-secret" in str(exc)
    assert "not found" in str(exc)


def test_secret_access_denied_exception_specific():
    """Test SecretAccessDeniedException for requirement 4.3."""
    secret_name = "protected-secret"
    exc = SecretAccessDeniedException(f"Access denied to secret '{secret_name}'")
    assert "protected-secret" in str(exc)
    assert "Access denied" in str(exc)


def test_invalid_input_exceptions_specific():
    """Test validation exceptions for requirement 4.3."""
    # Test invalid name
    name_exc = InvalidSecretNameException("Secret name cannot be empty")
    assert "name" in str(name_exc)
    assert "empty" in str(name_exc)

    # Test invalid value
    value_exc = InvalidSecretValueException("Secret value cannot be empty")
    assert "value" in str(value_exc)
    assert "empty" in str(value_exc)
