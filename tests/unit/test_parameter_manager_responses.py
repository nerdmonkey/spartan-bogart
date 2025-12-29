"""
Unit tests for Parameter Manager response models.

Tests Pydantic response model serialization following the Spartan Framework
testing patterns.
"""

from datetime import datetime

from app.responses.parameter_manager import (
    ParameterCreateResponse,
    ParameterListResponse,
    ParameterMetadataResponse,
    ParameterOperationResponse,
    ParameterResponse,
    ParameterUpdateResponse,
    ParameterVersionListResponse,
    ParameterVersionResponse,
)


def test_parameter_response_valid():
    """Test creating a valid ParameterResponse."""
    now = datetime.now()
    response = ParameterResponse(
        parameter_name="test-param",
        data="test data",
        format_type="UNFORMATTED",
        version="v1.0.0",
        created_time=now,
        updated_time=now,
        labels={"env": "dev"},
    )

    assert response.parameter_name == "test-param"
    assert response.data == "test data"
    assert response.format_type == "UNFORMATTED"
    assert response.version == "v1.0.0"
    assert response.created_time == now
    assert response.updated_time == now
    assert response.labels == {"env": "dev"}


def test_parameter_response_with_dict_data():
    """Test ParameterResponse with dictionary data."""
    now = datetime.now()
    response = ParameterResponse(
        parameter_name="test-param",
        data={"key": "value"},
        format_type="JSON",
        version="v1.0.0",
        created_time=now,
        updated_time=now,
    )

    assert response.data == {"key": "value"}
    assert response.format_type == "JSON"


def test_parameter_create_response_valid():
    """Test creating a valid ParameterCreateResponse."""
    now = datetime.now()
    response = ParameterCreateResponse(
        parameter_name="test-param",
        created_time=now,
        format_type="JSON",
    )

    assert response.parameter_name == "test-param"
    assert response.created_time == now
    assert response.format_type == "JSON"


def test_parameter_update_response_valid():
    """Test creating a valid ParameterUpdateResponse."""
    now = datetime.now()
    response = ParameterUpdateResponse(
        parameter_name="test-param",
        version="v2.0.0",
        updated_time=now,
    )

    assert response.parameter_name == "test-param"
    assert response.version == "v2.0.0"
    assert response.updated_time == now


def test_parameter_metadata_response_valid():
    """Test creating a valid ParameterMetadataResponse."""
    now = datetime.now()
    response = ParameterMetadataResponse(
        parameter_name="test-param",
        format_type="YAML",
        created_time=now,
        updated_time=now,
        labels={"env": "prod"},
        version_count=5,
    )

    assert response.parameter_name == "test-param"
    assert response.format_type == "YAML"
    assert response.version_count == 5
    assert response.labels == {"env": "prod"}


def test_parameter_list_response_valid():
    """Test creating a valid ParameterListResponse."""
    now = datetime.now()
    metadata = ParameterMetadataResponse(
        parameter_name="test-param",
        format_type="JSON",
        created_time=now,
        updated_time=now,
        version_count=3,
    )

    response = ParameterListResponse(
        parameters=[metadata],
        next_page_token="token123",
        total_size=10,
    )

    assert len(response.parameters) == 1
    assert response.next_page_token == "token123"
    assert response.total_size == 10


def test_parameter_version_response_valid():
    """Test creating a valid ParameterVersionResponse."""
    now = datetime.now()
    response = ParameterVersionResponse(
        parameter_name="test-param",
        version="v1.0.0",
        data="version data",
        format_type="UNFORMATTED",
        created_time=now,
    )

    assert response.parameter_name == "test-param"
    assert response.version == "v1.0.0"
    assert response.data == "version data"
    assert response.format_type == "UNFORMATTED"


def test_parameter_version_list_response_valid():
    """Test creating a valid ParameterVersionListResponse."""
    now = datetime.now()
    version = ParameterVersionResponse(
        parameter_name="test-param",
        version="v1.0.0",
        data="data",
        format_type="JSON",
        created_time=now,
    )

    response = ParameterVersionListResponse(
        versions=[version],
        next_page_token="token456",
        total_size=5,
    )

    assert len(response.versions) == 1
    assert response.next_page_token == "token456"
    assert response.total_size == 5


def test_parameter_operation_response_valid():
    """Test creating a valid ParameterOperationResponse."""
    now = datetime.now()
    response = ParameterOperationResponse(
        success=True,
        message="Operation completed successfully",
        operation_time=now,
    )

    assert response.success is True
    assert response.message == "Operation completed successfully"
    assert response.operation_time == now


def test_parameter_response_optional_labels():
    """Test ParameterResponse with optional labels as None."""
    now = datetime.now()
    response = ParameterResponse(
        parameter_name="test-param",
        data="test data",
        format_type="UNFORMATTED",
        version="v1.0.0",
        created_time=now,
        updated_time=now,
    )

    assert response.labels is None


def test_parameter_list_response_empty():
    """Test ParameterListResponse with empty list."""
    response = ParameterListResponse(
        parameters=[],
        next_page_token=None,
        total_size=0,
    )

    assert len(response.parameters) == 0
    assert response.next_page_token is None
    assert response.total_size == 0


# Datetime Handling Tests


def test_parameter_response_datetime_serialization():
    """Test that datetime fields are properly serialized to ISO format."""
    now = datetime(2024, 1, 15, 10, 30, 45)
    response = ParameterResponse(
        parameter_name="test-param",
        data="test data",
        format_type="UNFORMATTED",
        version="v1.0.0",
        created_time=now,
        updated_time=now,
    )

    # Test model_dump with mode='json' to trigger serialization
    json_data = response.model_dump(mode="json")
    assert json_data["created_time"] == now.isoformat()
    assert json_data["updated_time"] == now.isoformat()


def test_parameter_create_response_datetime_serialization():
    """Test ParameterCreateResponse datetime serialization."""
    now = datetime(2024, 1, 15, 10, 30, 45)
    response = ParameterCreateResponse(
        parameter_name="test-param",
        created_time=now,
        format_type="JSON",
    )

    json_data = response.model_dump(mode="json")
    assert json_data["created_time"] == now.isoformat()


def test_parameter_update_response_datetime_serialization():
    """Test ParameterUpdateResponse datetime serialization."""
    now = datetime(2024, 1, 15, 10, 30, 45)
    response = ParameterUpdateResponse(
        parameter_name="test-param",
        version="v2.0.0",
        updated_time=now,
    )

    json_data = response.model_dump(mode="json")
    assert json_data["updated_time"] == now.isoformat()


def test_parameter_metadata_response_datetime_serialization():
    """Test ParameterMetadataResponse datetime serialization."""
    created = datetime(2024, 1, 15, 10, 30, 45)
    updated = datetime(2024, 1, 16, 14, 20, 30)

    response = ParameterMetadataResponse(
        parameter_name="test-param",
        format_type="YAML",
        created_time=created,
        updated_time=updated,
        version_count=5,
    )

    json_data = response.model_dump(mode="json")
    assert json_data["created_time"] == created.isoformat()
    assert json_data["updated_time"] == updated.isoformat()


def test_parameter_version_response_datetime_serialization():
    """Test ParameterVersionResponse datetime serialization."""
    now = datetime(2024, 1, 15, 10, 30, 45)
    response = ParameterVersionResponse(
        parameter_name="test-param",
        version="v1.0.0",
        data="version data",
        format_type="UNFORMATTED",
        created_time=now,
    )

    json_data = response.model_dump(mode="json")
    assert json_data["created_time"] == now.isoformat()


def test_parameter_operation_response_datetime_serialization():
    """Test ParameterOperationResponse datetime serialization."""
    now = datetime(2024, 1, 15, 10, 30, 45)
    response = ParameterOperationResponse(
        success=True,
        message="Operation completed",
        operation_time=now,
    )

    json_data = response.model_dump(mode="json")
    assert json_data["operation_time"] == now.isoformat()


# Optional Field Tests


def test_parameter_metadata_response_without_labels():
    """Test ParameterMetadataResponse with labels as None."""
    now = datetime.now()
    response = ParameterMetadataResponse(
        parameter_name="test-param",
        format_type="JSON",
        created_time=now,
        updated_time=now,
        version_count=1,
    )

    assert response.labels is None


def test_parameter_list_response_without_pagination():
    """Test ParameterListResponse without pagination tokens."""
    now = datetime.now()
    metadata = ParameterMetadataResponse(
        parameter_name="test-param",
        format_type="JSON",
        created_time=now,
        updated_time=now,
        version_count=1,
    )

    response = ParameterListResponse(
        parameters=[metadata],
    )

    assert response.next_page_token is None
    assert response.total_size is None


def test_parameter_version_list_response_without_pagination():
    """Test ParameterVersionListResponse without pagination tokens."""
    now = datetime.now()
    version = ParameterVersionResponse(
        parameter_name="test-param",
        version="v1.0.0",
        data="data",
        format_type="JSON",
        created_time=now,
    )

    response = ParameterVersionListResponse(
        versions=[version],
    )

    assert response.next_page_token is None
    assert response.total_size is None


# Format Type Tests


def test_parameter_response_all_format_types():
    """Test ParameterResponse with all supported format types."""
    now = datetime.now()

    # UNFORMATTED
    response1 = ParameterResponse(
        parameter_name="test-param-1",
        data="plain text",
        format_type="UNFORMATTED",
        version="v1",
        created_time=now,
        updated_time=now,
    )
    assert response1.format_type == "UNFORMATTED"

    # JSON
    response2 = ParameterResponse(
        parameter_name="test-param-2",
        data={"key": "value"},
        format_type="JSON",
        version="v1",
        created_time=now,
        updated_time=now,
    )
    assert response2.format_type == "JSON"

    # YAML
    response3 = ParameterResponse(
        parameter_name="test-param-3",
        data="key: value",
        format_type="YAML",
        version="v1",
        created_time=now,
        updated_time=now,
    )
    assert response3.format_type == "YAML"


def test_parameter_create_response_all_format_types():
    """Test ParameterCreateResponse with all format types."""
    now = datetime.now()

    for format_type in ["UNFORMATTED", "JSON", "YAML"]:
        response = ParameterCreateResponse(
            parameter_name=f"test-param-{format_type}",
            created_time=now,
            format_type=format_type,
        )
        assert response.format_type == format_type


def test_parameter_metadata_response_all_format_types():
    """Test ParameterMetadataResponse with all format types."""
    now = datetime.now()

    for format_type in ["UNFORMATTED", "JSON", "YAML"]:
        response = ParameterMetadataResponse(
            parameter_name=f"test-param-{format_type}",
            format_type=format_type,
            created_time=now,
            updated_time=now,
            version_count=1,
        )
        assert response.format_type == format_type


# Version Naming Tests


def test_parameter_response_various_version_names():
    """Test ParameterResponse with various version naming patterns."""
    now = datetime.now()

    version_patterns = [
        "v1.0.0",
        "2024-01-15",
        "production-release",
        "alpha-1.0",
        "latest",
        "stable",
    ]

    for version in version_patterns:
        response = ParameterResponse(
            parameter_name="test-param",
            data="test data",
            format_type="UNFORMATTED",
            version=version,
            created_time=now,
            updated_time=now,
        )
        assert response.version == version


def test_parameter_update_response_various_version_names():
    """Test ParameterUpdateResponse with various version names."""
    now = datetime.now()

    version_patterns = [
        "v2.0.0",
        "2024-02-01",
        "hotfix-1.2.3",
    ]

    for version in version_patterns:
        response = ParameterUpdateResponse(
            parameter_name="test-param",
            version=version,
            updated_time=now,
        )
        assert response.version == version


def test_parameter_version_response_various_version_names():
    """Test ParameterVersionResponse with various version names."""
    now = datetime.now()

    version_patterns = [
        "v1.0.0",
        "release-2024",
        "beta-3",
    ]

    for version in version_patterns:
        response = ParameterVersionResponse(
            parameter_name="test-param",
            version=version,
            data="data",
            format_type="JSON",
            created_time=now,
        )
        assert response.version == version


# Large Data Handling Tests


def test_parameter_response_with_large_data():
    """Test ParameterResponse with large data (close to 1 MiB)."""
    now = datetime.now()
    large_data = "x" * (1_048_576 - 1000)  # Close to 1 MiB

    response = ParameterResponse(
        parameter_name="test-param",
        data=large_data,
        format_type="UNFORMATTED",
        version="v1",
        created_time=now,
        updated_time=now,
    )

    assert len(response.data) == len(large_data)
    assert response.data == large_data


def test_parameter_version_response_with_large_dict():
    """Test ParameterVersionResponse with large dictionary data."""
    now = datetime.now()
    large_dict = {f"key_{i}": f"value_{i}" * 100 for i in range(1000)}

    response = ParameterVersionResponse(
        parameter_name="test-param",
        version="v1",
        data=large_dict,
        format_type="JSON",
        created_time=now,
    )

    assert response.data == large_dict
    assert len(response.data) == 1000


# Multiple Items in List Responses


def test_parameter_list_response_multiple_items():
    """Test ParameterListResponse with multiple parameters."""
    now = datetime.now()

    parameters = [
        ParameterMetadataResponse(
            parameter_name=f"test-param-{i}",
            format_type="JSON",
            created_time=now,
            updated_time=now,
            version_count=i + 1,
        )
        for i in range(5)
    ]

    response = ParameterListResponse(
        parameters=parameters,
        next_page_token="next_token",
        total_size=10,
    )

    assert len(response.parameters) == 5
    assert response.parameters[0].version_count == 1
    assert response.parameters[4].version_count == 5


def test_parameter_version_list_response_multiple_versions():
    """Test ParameterVersionListResponse with multiple versions."""
    now = datetime.now()

    versions = [
        ParameterVersionResponse(
            parameter_name="test-param",
            version=f"v{i}.0.0",
            data=f"data for version {i}",
            format_type="UNFORMATTED",
            created_time=now,
        )
        for i in range(1, 6)
    ]

    response = ParameterVersionListResponse(
        versions=versions,
        next_page_token="next_token",
        total_size=10,
    )

    assert len(response.versions) == 5
    assert response.versions[0].version == "v1.0.0"
    assert response.versions[4].version == "v5.0.0"


# Operation Response Tests


def test_parameter_operation_response_success():
    """Test ParameterOperationResponse for successful operation."""
    now = datetime.now()
    response = ParameterOperationResponse(
        success=True,
        message="Parameter deleted successfully",
        operation_time=now,
    )

    assert response.success is True
    assert "successfully" in response.message


def test_parameter_operation_response_failure():
    """Test ParameterOperationResponse for failed operation."""
    now = datetime.now()
    response = ParameterOperationResponse(
        success=False,
        message="Failed to delete parameter: not found",
        operation_time=now,
    )

    assert response.success is False
    assert "Failed" in response.message


# Complex Data Structure Tests


def test_parameter_response_with_complex_json():
    """Test ParameterResponse with complex nested JSON structure."""
    now = datetime.now()
    complex_data = {
        "database": {
            "host": "localhost",
            "port": 5432,
            "pools": [
                {"name": "pool1", "size": 10},
                {"name": "pool2", "size": 20},
            ],
        },
        "cache": {
            "enabled": True,
            "ttl": 300,
        },
    }

    response = ParameterResponse(
        parameter_name="test-param",
        data=complex_data,
        format_type="JSON",
        version="v1",
        created_time=now,
        updated_time=now,
    )

    assert response.data == complex_data
    assert response.data["database"]["pools"][0]["name"] == "pool1"


def test_parameter_version_response_with_yaml_string():
    """Test ParameterVersionResponse with YAML string data."""
    now = datetime.now()
    yaml_data = """
database:
  host: localhost
  port: 5432
cache:
  enabled: true
  ttl: 300
"""

    response = ParameterVersionResponse(
        parameter_name="test-param",
        version="v1",
        data=yaml_data,
        format_type="YAML",
        created_time=now,
    )

    assert response.data == yaml_data
    assert "database:" in response.data
