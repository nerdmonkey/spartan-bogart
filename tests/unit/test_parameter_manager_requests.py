"""
Unit tests for Parameter Manager request models.

Tests Pydantic request model validation following the Spartan Framework
testing patterns.
"""

import pytest
from pydantic import ValidationError

from app.requests.parameter_manager import (
    ParameterAccessRequest,
    ParameterCreateRequest,
    ParameterUpdateRequest,
    ParameterVersionCreateRequest,
)


def test_parameter_create_request_valid():
    """Test creating a valid ParameterCreateRequest."""
    request = ParameterCreateRequest(
        parameter_name="test-param",
        format_type="JSON",
        labels={"env": "dev"},
    )

    assert request.parameter_name == "test-param"
    assert request.format_type == "JSON"
    assert request.labels == {"env": "dev"}


def test_parameter_create_request_defaults():
    """Test ParameterCreateRequest with default values."""
    request = ParameterCreateRequest(parameter_name="test-param")

    assert request.parameter_name == "test-param"
    assert request.format_type == "UNFORMATTED"
    assert request.labels is None


def test_parameter_create_request_invalid_format():
    """Test ParameterCreateRequest with invalid format type."""
    with pytest.raises(ValidationError) as exc_info:
        ParameterCreateRequest(
            parameter_name="test-param",
            format_type="INVALID",
        )

    assert "Format type must be one of" in str(exc_info.value)


def test_parameter_version_create_request_valid():
    """Test creating a valid ParameterVersionCreateRequest."""
    request = ParameterVersionCreateRequest(
        parameter_name="test-param",
        version_name="v1.0.0",
        data="test data",
        format_type="UNFORMATTED",
    )

    assert request.parameter_name == "test-param"
    assert request.version_name == "v1.0.0"
    assert request.data == "test data"
    assert request.format_type == "UNFORMATTED"


def test_parameter_version_create_request_with_dict():
    """Test ParameterVersionCreateRequest with dictionary data."""
    request = ParameterVersionCreateRequest(
        parameter_name="test-param",
        version_name="v1.0.0",
        data={"key": "value"},
        format_type="JSON",
    )

    assert request.data == {"key": "value"}
    assert request.format_type == "JSON"


def test_parameter_update_request_valid():
    """Test creating a valid ParameterUpdateRequest."""
    request = ParameterUpdateRequest(
        parameter_name="test-param",
        version_name="v2.0.0",
        data="updated data",
        labels={"env": "prod"},
    )

    assert request.parameter_name == "test-param"
    assert request.version_name == "v2.0.0"
    assert request.data == "updated data"
    assert request.labels == {"env": "prod"}


def test_parameter_access_request_valid():
    """Test creating a valid ParameterAccessRequest."""
    request = ParameterAccessRequest(
        parameter_name="test-param",
        version="v1.0.0",
    )

    assert request.parameter_name == "test-param"
    assert request.version == "v1.0.0"


def test_parameter_access_request_defaults():
    """Test ParameterAccessRequest with default version."""
    request = ParameterAccessRequest(parameter_name="test-param")

    assert request.parameter_name == "test-param"
    assert request.version is None


def test_parameter_create_request_missing_name():
    """Test ParameterCreateRequest without required parameter_name."""
    with pytest.raises(ValidationError):
        ParameterCreateRequest()


def test_format_type_validation_yaml():
    """Test that YAML format type is accepted."""
    request = ParameterCreateRequest(
        parameter_name="test-param",
        format_type="YAML",
    )

    assert request.format_type == "YAML"


def test_format_type_validation_unformatted():
    """Test that UNFORMATTED format type is accepted."""
    request = ParameterCreateRequest(
        parameter_name="test-param",
        format_type="UNFORMATTED",
    )

    assert request.format_type == "UNFORMATTED"


# Edge Cases and Validation Tests


def test_parameter_name_whitespace_only():
    """Test that parameter name with only whitespace is rejected."""
    with pytest.raises(ValidationError) as exc_info:
        ParameterCreateRequest(
            parameter_name="   ",
            format_type="UNFORMATTED",
        )

    assert "Parameter name cannot be empty or whitespace" in str(exc_info.value)


def test_parameter_name_empty_string():
    """Test that empty parameter name is rejected."""
    with pytest.raises(ValidationError) as exc_info:
        ParameterCreateRequest(
            parameter_name="",
            format_type="UNFORMATTED",
        )

    # Pydantic will catch this as min_length validation
    assert "String should have at least 1 character" in str(exc_info.value)


def test_parameter_name_trimmed():
    """Test that parameter name is trimmed of whitespace."""
    request = ParameterCreateRequest(
        parameter_name="  test-param  ",
        format_type="UNFORMATTED",
    )

    assert request.parameter_name == "test-param"


def test_version_name_whitespace_only():
    """Test that version name with only whitespace is rejected."""
    with pytest.raises(ValidationError) as exc_info:
        ParameterVersionCreateRequest(
            parameter_name="test-param",
            version_name="   ",
            data="test data",
        )

    assert "Version name cannot be empty or whitespace" in str(exc_info.value)


def test_version_name_trimmed():
    """Test that version name is trimmed of whitespace."""
    request = ParameterVersionCreateRequest(
        parameter_name="test-param",
        version_name="  v1.0.0  ",
        data="test data",
    )

    assert request.version_name == "v1.0.0"


def test_version_name_custom_patterns():
    """Test various custom version naming patterns."""
    # Semantic versioning
    request1 = ParameterVersionCreateRequest(
        parameter_name="test-param",
        version_name="v1.2.3",
        data="test data",
    )
    assert request1.version_name == "v1.2.3"

    # Date-based versioning
    request2 = ParameterVersionCreateRequest(
        parameter_name="test-param",
        version_name="2024-01-15",
        data="test data",
    )
    assert request2.version_name == "2024-01-15"

    # Custom string versioning
    request3 = ParameterVersionCreateRequest(
        parameter_name="test-param",
        version_name="production-release",
        data="test data",
    )
    assert request3.version_name == "production-release"

    # Alphanumeric versioning
    request4 = ParameterVersionCreateRequest(
        parameter_name="test-param",
        version_name="alpha-1.0",
        data="test data",
    )
    assert request4.version_name == "alpha-1.0"


# Format Type Validation Tests


def test_json_format_with_valid_json_string():
    """Test JSON format with valid JSON string data."""
    request = ParameterVersionCreateRequest(
        parameter_name="test-param",
        version_name="v1",
        data='{"key": "value", "number": 42}',
        format_type="JSON",
    )

    assert request.format_type == "JSON"
    assert request.data == '{"key": "value", "number": 42}'


def test_json_format_with_valid_json_dict():
    """Test JSON format with valid dictionary data."""
    request = ParameterVersionCreateRequest(
        parameter_name="test-param",
        version_name="v1",
        data={"key": "value", "number": 42},
        format_type="JSON",
    )

    assert request.format_type == "JSON"
    assert request.data == {"key": "value", "number": 42}


def test_yaml_format_with_valid_yaml_string():
    """Test YAML format with valid YAML string data."""
    request = ParameterVersionCreateRequest(
        parameter_name="test-param",
        version_name="v1",
        data="key: value\nnumber: 42",
        format_type="YAML",
    )

    assert request.format_type == "YAML"
    assert request.data == "key: value\nnumber: 42"


def test_yaml_format_with_valid_yaml_dict():
    """Test YAML format with valid dictionary data."""
    request = ParameterVersionCreateRequest(
        parameter_name="test-param",
        version_name="v1",
        data={"key": "value", "number": 42},
        format_type="YAML",
    )

    assert request.format_type == "YAML"
    assert request.data == {"key": "value", "number": 42}


def test_unformatted_accepts_any_string():
    """Test UNFORMATTED format accepts any string data."""
    request = ParameterVersionCreateRequest(
        parameter_name="test-param",
        version_name="v1",
        data="This is just plain text with no structure",
        format_type="UNFORMATTED",
    )

    assert request.format_type == "UNFORMATTED"
    assert request.data == "This is just plain text with no structure"


# Large Data Handling Tests (up to 1 MiB)


def test_data_size_within_limit():
    """Test that data within 1 MiB limit is accepted."""
    # Create data that's close to but under 1 MiB
    large_data = "x" * (1_048_576 - 100)  # Just under 1 MiB

    request = ParameterVersionCreateRequest(
        parameter_name="test-param",
        version_name="v1",
        data=large_data,
        format_type="UNFORMATTED",
    )

    assert len(request.data.encode("utf-8")) < 1_048_576


def test_data_size_at_limit():
    """Test that data at exactly 1 MiB limit is accepted."""
    # Create data that's exactly 1 MiB
    large_data = "x" * 1_048_576

    request = ParameterVersionCreateRequest(
        parameter_name="test-param",
        version_name="v1",
        data=large_data,
        format_type="UNFORMATTED",
    )

    assert len(request.data.encode("utf-8")) == 1_048_576


def test_data_size_exceeds_limit():
    """Test that data exceeding 1 MiB is rejected."""
    # Create data that exceeds 1 MiB
    large_data = "x" * (1_048_576 + 1)

    with pytest.raises(ValidationError) as exc_info:
        ParameterVersionCreateRequest(
            parameter_name="test-param",
            version_name="v1",
            data=large_data,
            format_type="UNFORMATTED",
        )

    assert "Parameter data cannot exceed 1 MiB" in str(exc_info.value)


def test_data_size_with_dict_within_limit():
    """Test that dictionary data within 1 MiB limit is accepted."""
    # Create a large dictionary
    large_dict = {f"key_{i}": f"value_{i}" * 100 for i in range(1000)}

    request = ParameterVersionCreateRequest(
        parameter_name="test-param",
        version_name="v1",
        data=large_dict,
        format_type="JSON",
    )

    # Verify it's within limits
    import json

    assert len(json.dumps(request.data).encode("utf-8")) < 1_048_576


def test_data_size_with_dict_exceeds_limit():
    """Test that dictionary data exceeding 1 MiB is rejected."""
    # Create a very large dictionary that exceeds 1 MiB
    large_dict = {f"key_{i}": "x" * 10000 for i in range(200)}

    with pytest.raises(ValidationError) as exc_info:
        ParameterVersionCreateRequest(
            parameter_name="test-param",
            version_name="v1",
            data=large_dict,
            format_type="JSON",
        )

    assert "Parameter data cannot exceed 1 MiB" in str(exc_info.value)


def test_update_request_data_size_limit():
    """Test that ParameterUpdateRequest also enforces 1 MiB limit."""
    large_data = "x" * (1_048_576 + 1)

    with pytest.raises(ValidationError) as exc_info:
        ParameterUpdateRequest(
            parameter_name="test-param",
            version_name="v2",
            data=large_data,
        )

    assert "Parameter data cannot exceed 1 MiB" in str(exc_info.value)


# List Request Validation Tests


def test_parameter_list_request_defaults():
    """Test ParameterListRequest with default values."""
    from app.requests.parameter_manager import ParameterListRequest

    request = ParameterListRequest()

    assert request.page_size == 100
    assert request.page_token is None
    assert request.filter_expression is None


def test_parameter_list_request_custom_page_size():
    """Test ParameterListRequest with custom page size."""
    from app.requests.parameter_manager import ParameterListRequest

    request = ParameterListRequest(page_size=50)

    assert request.page_size == 50


def test_parameter_list_request_page_size_too_small():
    """Test ParameterListRequest with page size below minimum."""
    from app.requests.parameter_manager import ParameterListRequest

    with pytest.raises(ValidationError) as exc_info:
        ParameterListRequest(page_size=0)

    # Pydantic's ge validator will catch this
    assert "greater than or equal to 1" in str(exc_info.value).lower()


def test_parameter_list_request_page_size_too_large():
    """Test ParameterListRequest with page size above maximum."""
    from app.requests.parameter_manager import ParameterListRequest

    with pytest.raises(ValidationError) as exc_info:
        ParameterListRequest(page_size=1001)

    # Pydantic's le validator will catch this
    assert "less than or equal to 1000" in str(exc_info.value).lower()


def test_parameter_list_request_with_filter():
    """Test ParameterListRequest with filter expression."""
    from app.requests.parameter_manager import ParameterListRequest

    request = ParameterListRequest(
        page_size=50,
        filter_expression="labels.env=prod",
    )

    assert request.filter_expression == "labels.env=prod"


def test_parameter_version_list_request_valid():
    """Test ParameterVersionListRequest with valid values."""
    from app.requests.parameter_manager import ParameterVersionListRequest

    request = ParameterVersionListRequest(
        parameter_name="test-param",
        page_size=25,
        page_token="token123",
    )

    assert request.parameter_name == "test-param"
    assert request.page_size == 25
    assert request.page_token == "token123"


def test_parameter_version_list_request_page_size_validation():
    """Test ParameterVersionListRequest page size validation."""
    from app.requests.parameter_manager import ParameterVersionListRequest

    with pytest.raises(ValidationError) as exc_info:
        ParameterVersionListRequest(
            parameter_name="test-param",
            page_size=2000,
        )

    # Pydantic's le validator will catch this
    assert "less than or equal to 1000" in str(exc_info.value).lower()


# Complex Validation Scenarios


def test_json_format_with_nested_structure():
    """Test JSON format with complex nested structure."""
    complex_data = {
        "config": {
            "database": {
                "host": "localhost",
                "port": 5432,
                "credentials": {
                    "username": "admin",
                    "password": "secret",
                },
            },
            "features": ["feature1", "feature2", "feature3"],
        }
    }

    request = ParameterVersionCreateRequest(
        parameter_name="test-param",
        version_name="v1",
        data=complex_data,
        format_type="JSON",
    )

    assert request.data == complex_data
    assert request.format_type == "JSON"


def test_yaml_format_with_nested_structure():
    """Test YAML format with complex nested structure."""
    yaml_string = """
config:
  database:
    host: localhost
    port: 5432
  features:
    - feature1
    - feature2
"""

    request = ParameterVersionCreateRequest(
        parameter_name="test-param",
        version_name="v1",
        data=yaml_string,
        format_type="YAML",
    )

    assert request.data == yaml_string
    assert request.format_type == "YAML"


def test_labels_validation():
    """Test that labels are properly handled."""
    request = ParameterCreateRequest(
        parameter_name="test-param",
        format_type="JSON",
        labels={"env": "production", "team": "backend", "version": "1.0"},
    )

    assert request.labels == {"env": "production", "team": "backend", "version": "1.0"}


def test_optional_labels_none():
    """Test that labels can be None."""
    request = ParameterCreateRequest(
        parameter_name="test-param",
        format_type="JSON",
    )

    assert request.labels is None


def test_parameter_name_max_length():
    """Test parameter name at maximum length."""
    long_name = "a" * 255

    request = ParameterCreateRequest(
        parameter_name=long_name,
        format_type="UNFORMATTED",
    )

    assert request.parameter_name == long_name


def test_parameter_name_exceeds_max_length():
    """Test parameter name exceeding maximum length."""
    too_long_name = "a" * 256

    with pytest.raises(ValidationError) as exc_info:
        ParameterCreateRequest(
            parameter_name=too_long_name,
            format_type="UNFORMATTED",
        )

    assert "String should have at most 255 characters" in str(exc_info.value)
