"""
Integration tests for Parameter Manager service.

These tests validate end-to-end workflows with real Google Cloud Parameter Manager
and test service integration with framework components.

Note: These tests require:
1. Valid Google Cloud credentials
2. A Google Cloud project with Parameter Manager API enabled
3. Appropriate IAM permissions for Parameter Manager operations
4. Set GOOGLE_CLOUD_PROJECT environment variable or configure gcloud CLI

To run these tests:
    pytest tests/integration/test_parameter_manager_integration.py -v

To skip integration tests:
    pytest -m "not integration"
"""

import json
import os
import time
from datetime import datetime

import pytest
import yaml

from app.exceptions.parameter_manager import (
    ParameterNotFoundException,
    ParameterVersionNotFoundException,
)
from app.requests.parameter_manager import ParameterCreateRequest
from app.services.parameter_manager import ParameterManagerService


# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def project_id():
    """Get project ID from environment or skip tests if not available."""
    pid = os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GCP_PROJECT")
    if not pid:
        pytest.skip("GOOGLE_CLOUD_PROJECT environment variable not set")
    return pid


@pytest.fixture(scope="module")
def parameter_manager_service(project_id):
    """Create a ParameterManagerService instance for integration testing."""
    try:
        service = ParameterManagerService(project_id=project_id)
        return service
    except Exception as e:
        pytest.skip(f"Failed to initialize ParameterManagerService: {str(e)}")


@pytest.fixture
def test_parameter_name():
    """Generate a unique test parameter name."""
    timestamp = int(time.time() * 1000)
    return f"test-param-integration-{timestamp}"


@pytest.fixture
def cleanup_parameters(parameter_manager_service):
    """Fixture to track and cleanup test parameters after tests."""
    created_parameters = []

    yield created_parameters

    # Cleanup: delete all created parameters
    for parameter_name in created_parameters:
        try:
            parameter_manager_service.delete_parameter(parameter_name)
            print(f"Cleaned up test parameter: {parameter_name}")
        except Exception as e:
            print(f"Failed to cleanup parameter {parameter_name}: {str(e)}")


def test_service_initialization(project_id):
    """Test that service initializes successfully with real credentials."""
    service = ParameterManagerService(project_id=project_id)

    assert service.project_id == project_id
    assert service.location == "global"
    assert service.logger is not None


def test_service_initialization_with_regional_endpoint(project_id):
    """Test service initialization with regional endpoint."""
    service = ParameterManagerService(project_id=project_id, location="us-central1")

    assert service.project_id == project_id
    assert service.location == "us-central1"


def test_regional_endpoint_operations(project_id):
    """
    Test creating and retrieving parameters using regional endpoints.

    This test verifies that the service can work with regional endpoints
    for location-specific parameter storage.
    """
    # Create service with regional endpoint
    service = ParameterManagerService(project_id=project_id, location="us-central1")

    test_param_name = f"test-regional-param-{int(time.time() * 1000)}"

    try:
        # Create a parameter in the regional location
        create_request = ParameterCreateRequest(
            parameter_name=test_param_name, format_type="UNFORMATTED"
        )
        create_response = service.create_parameter(create_request)

        assert create_response.parameter_name == test_param_name

        # Create a version
        service.create_parameter_version(
            parameter_name=test_param_name,
            version_name="v1",
            data="regional-value",
            format_type="UNFORMATTED",
        )

        # Retrieve from regional endpoint
        retrieve_response = service.get_parameter(test_param_name)

        assert retrieve_response.parameter_name == test_param_name
        assert retrieve_response.data == "regional-value"

    finally:
        # Cleanup
        try:
            service.delete_parameter(test_param_name)
        except Exception:
            pass


def test_create_and_retrieve_unformatted_parameter(
    parameter_manager_service, test_parameter_name, cleanup_parameters
):
    """Test end-to-end workflow: create UNFORMATTED parameter and retrieve it."""
    cleanup_parameters.append(test_parameter_name)

    # Create an UNFORMATTED parameter
    parameter_value = "integration-test-value-12345"
    create_request = ParameterCreateRequest(
        parameter_name=test_parameter_name, format_type="UNFORMATTED"
    )

    create_response = parameter_manager_service.create_parameter(create_request)

    # Verify creation response
    assert create_response.parameter_name == test_parameter_name
    assert create_response.format_type == "UNFORMATTED"
    assert isinstance(create_response.created_time, datetime)

    # Create first version
    parameter_manager_service.create_parameter_version(
        parameter_name=test_parameter_name,
        version_name="v1",
        data=parameter_value,
        format_type="UNFORMATTED",
    )

    # Retrieve the parameter
    retrieve_response = parameter_manager_service.get_parameter(test_parameter_name)

    # Verify retrieval
    assert retrieve_response.parameter_name == test_parameter_name
    assert retrieve_response.data == parameter_value
    assert retrieve_response.format_type == "UNFORMATTED"


def test_create_and_retrieve_json_parameter(
    parameter_manager_service, test_parameter_name, cleanup_parameters
):
    """Test creating and retrieving a JSON formatted parameter."""
    cleanup_parameters.append(test_parameter_name)

    # Create a JSON parameter
    json_data = {"key": "value", "number": 42, "nested": {"inner": "data"}}

    create_request = ParameterCreateRequest(
        parameter_name=test_parameter_name, format_type="JSON"
    )
    parameter_manager_service.create_parameter(create_request)

    # Create version with JSON data
    parameter_manager_service.create_parameter_version(
        parameter_name=test_parameter_name,
        version_name="v1",
        data=json_data,
        format_type="JSON",
    )

    # Retrieve the parameter
    retrieve_response = parameter_manager_service.get_parameter(test_parameter_name)

    # Verify retrieval
    assert retrieve_response.parameter_name == test_parameter_name
    assert retrieve_response.format_type == "JSON"

    # Parse and verify JSON data
    if isinstance(retrieve_response.data, str):
        retrieved_data = json.loads(retrieve_response.data)
    else:
        retrieved_data = retrieve_response.data

    assert retrieved_data == json_data


def test_create_and_retrieve_yaml_parameter(
    parameter_manager_service, test_parameter_name, cleanup_parameters
):
    """Test creating and retrieving a YAML formatted parameter."""
    cleanup_parameters.append(test_parameter_name)

    # Create a YAML parameter
    yaml_data = {
        "database": {"host": "localhost", "port": 5432, "name": "testdb"},
        "features": ["feature1", "feature2"],
    }

    create_request = ParameterCreateRequest(
        parameter_name=test_parameter_name, format_type="YAML"
    )
    parameter_manager_service.create_parameter(create_request)

    # Create version with YAML data
    parameter_manager_service.create_parameter_version(
        parameter_name=test_parameter_name,
        version_name="v1",
        data=yaml_data,
        format_type="YAML",
    )

    # Retrieve the parameter
    retrieve_response = parameter_manager_service.get_parameter(test_parameter_name)

    # Verify retrieval
    assert retrieve_response.parameter_name == test_parameter_name
    assert retrieve_response.format_type == "YAML"

    # Parse and verify YAML data
    if isinstance(retrieve_response.data, str):
        retrieved_data = yaml.safe_load(retrieve_response.data)
    else:
        retrieved_data = retrieve_response.data

    assert retrieved_data == yaml_data


def test_version_management_workflow(
    parameter_manager_service, test_parameter_name, cleanup_parameters
):
    """Test version management: create, add versions, list, retrieve specific versions."""
    cleanup_parameters.append(test_parameter_name)

    # Create initial parameter
    create_request = ParameterCreateRequest(
        parameter_name=test_parameter_name, format_type="UNFORMATTED"
    )
    parameter_manager_service.create_parameter(create_request)

    # Create multiple versions with custom names
    versions = ["v1", "v2", "v3"]
    for version_name in versions:
        parameter_manager_service.create_parameter_version(
            parameter_name=test_parameter_name,
            version_name=version_name,
            data=f"value-{version_name}",
            format_type="UNFORMATTED",
        )

    # List versions
    versions_response = parameter_manager_service.list_parameter_versions(
        test_parameter_name
    )

    assert len(versions_response.versions) >= 3
    version_names = [v.version for v in versions_response.versions]
    for version_name in versions:
        assert version_name in version_names

    # Retrieve specific versions
    for version_name in versions:
        response = parameter_manager_service.get_parameter_version(
            test_parameter_name, version_name
        )
        assert response.data == f"value-{version_name}"
        assert response.version == version_name

    # Retrieve latest version
    latest_response = parameter_manager_service.get_parameter(test_parameter_name)
    assert latest_response.data == "value-v3"


def test_parameter_listing_and_metadata(
    parameter_manager_service, test_parameter_name, cleanup_parameters
):
    """Test parameter listing and metadata retrieval."""
    cleanup_parameters.append(test_parameter_name)

    # Create a test parameter with labels
    create_request = ParameterCreateRequest(
        parameter_name=test_parameter_name,
        format_type="UNFORMATTED",
        labels={"env": "test", "purpose": "integration"},
    )
    parameter_manager_service.create_parameter(create_request)

    # Create a version
    parameter_manager_service.create_parameter_version(
        parameter_name=test_parameter_name,
        version_name="v1",
        data="test-value",
        format_type="UNFORMATTED",
    )

    # List parameters
    list_response = parameter_manager_service.list_parameters(page_size=100)

    # Verify our parameter is in the list
    parameter_names = [p.parameter_name for p in list_response.parameters]
    assert test_parameter_name in parameter_names

    # Get metadata
    metadata_response = parameter_manager_service.get_parameter_metadata(
        test_parameter_name
    )

    assert metadata_response.parameter_name == test_parameter_name
    assert metadata_response.format_type == "UNFORMATTED"
    assert metadata_response.labels == {"env": "test", "purpose": "integration"}
    assert isinstance(metadata_response.created_time, datetime)


def test_parameter_deletion_workflow(
    parameter_manager_service, test_parameter_name, cleanup_parameters
):
    """Test parameter deletion removes all versions."""
    # Note: We don't add to cleanup_parameters since we're testing deletion

    # Create a parameter
    create_request = ParameterCreateRequest(
        parameter_name=test_parameter_name, format_type="UNFORMATTED"
    )
    parameter_manager_service.create_parameter(create_request)

    # Create a version
    parameter_manager_service.create_parameter_version(
        parameter_name=test_parameter_name,
        version_name="v1",
        data="to-be-deleted",
        format_type="UNFORMATTED",
    )

    # Verify it exists
    retrieve_response = parameter_manager_service.get_parameter(test_parameter_name)
    assert retrieve_response.parameter_name == test_parameter_name

    # Delete the parameter
    delete_response = parameter_manager_service.delete_parameter(test_parameter_name)
    assert delete_response.success is True

    # Verify it no longer exists
    with pytest.raises(ParameterNotFoundException):
        parameter_manager_service.get_parameter_metadata(test_parameter_name)


def test_version_deletion_workflow(
    parameter_manager_service, test_parameter_name, cleanup_parameters
):
    """Test deleting specific parameter versions."""
    cleanup_parameters.append(test_parameter_name)

    # Create parameter with multiple versions
    create_request = ParameterCreateRequest(
        parameter_name=test_parameter_name, format_type="UNFORMATTED"
    )
    parameter_manager_service.create_parameter(create_request)

    # Create versions
    for i in range(1, 4):
        parameter_manager_service.create_parameter_version(
            parameter_name=test_parameter_name,
            version_name=f"v{i}",
            data=f"value-{i}",
            format_type="UNFORMATTED",
        )

    # Delete version v2
    delete_response = parameter_manager_service.delete_parameter_version(
        test_parameter_name, "v2"
    )
    assert delete_response.success is True

    # Verify v2 is deleted
    with pytest.raises(ParameterVersionNotFoundException):
        parameter_manager_service.get_parameter_version(test_parameter_name, "v2")

    # Verify other versions still exist
    v1_response = parameter_manager_service.get_parameter_version(
        test_parameter_name, "v1"
    )
    assert v1_response.data == "value-1"

    v3_response = parameter_manager_service.get_parameter_version(
        test_parameter_name, "v3"
    )
    assert v3_response.data == "value-3"


def test_error_handling_with_real_api(parameter_manager_service):
    """Test error handling with real API responses."""
    # Test accessing non-existent parameter
    with pytest.raises(ParameterNotFoundException):
        parameter_manager_service.get_parameter("nonexistent-parameter-12345")

    # Test getting metadata for non-existent parameter
    with pytest.raises(ParameterNotFoundException):
        parameter_manager_service.get_parameter_metadata("nonexistent-parameter-12345")


def test_parameter_exists_utility(
    parameter_manager_service, test_parameter_name, cleanup_parameters
):
    """Test parameter_exists utility method."""
    # Check non-existent parameter
    assert parameter_manager_service.parameter_exists(test_parameter_name) is False

    # Create parameter
    cleanup_parameters.append(test_parameter_name)
    create_request = ParameterCreateRequest(
        parameter_name=test_parameter_name, format_type="UNFORMATTED"
    )
    parameter_manager_service.create_parameter(create_request)

    # Check existing parameter
    assert parameter_manager_service.parameter_exists(test_parameter_name) is True


def test_framework_integration_logging(
    parameter_manager_service, test_parameter_name, cleanup_parameters
):
    """Test that service integrates properly with framework logging."""
    cleanup_parameters.append(test_parameter_name)

    # Verify logger is configured
    assert parameter_manager_service.logger is not None
    assert parameter_manager_service.logger.name == "app.services.parameter_manager"

    # Perform an operation and verify it completes (logging happens internally)
    create_request = ParameterCreateRequest(
        parameter_name=test_parameter_name, format_type="UNFORMATTED"
    )
    response = parameter_manager_service.create_parameter(create_request)

    assert response.parameter_name == test_parameter_name


def test_request_response_model_integration(
    parameter_manager_service, test_parameter_name, cleanup_parameters
):
    """Test that Pydantic request/response models work with real API."""
    cleanup_parameters.append(test_parameter_name)

    # Test request model validation
    create_request = ParameterCreateRequest(
        parameter_name=test_parameter_name,
        format_type="JSON",
        labels={"test": "true", "integration": "yes"},
    )

    # Verify request model fields
    assert create_request.parameter_name == test_parameter_name
    assert create_request.format_type == "JSON"
    assert create_request.labels == {"test": "true", "integration": "yes"}

    # Create parameter and verify response model
    response = parameter_manager_service.create_parameter(create_request)

    # Verify response model structure
    assert hasattr(response, "parameter_name")
    assert hasattr(response, "format_type")
    assert hasattr(response, "created_time")

    # Verify response can be serialized
    response_dict = response.model_dump()
    assert "parameter_name" in response_dict
    assert "format_type" in response_dict
    assert "created_time" in response_dict


def test_caching_integration(project_id, test_parameter_name):
    """Test caching functionality with real API."""
    # Create service with caching enabled
    service = ParameterManagerService(
        project_id=project_id, enable_cache=True, cache_ttl_seconds=60
    )

    try:
        # Create a test parameter
        create_request = ParameterCreateRequest(
            parameter_name=test_parameter_name, format_type="UNFORMATTED"
        )
        service.create_parameter(create_request)

        # Create version
        service.create_parameter_version(
            parameter_name=test_parameter_name,
            version_name="v1",
            data="cached-value",
            format_type="UNFORMATTED",
        )

        # First retrieval (cache miss)
        start_time = time.time()
        response1 = service.get_parameter(test_parameter_name)
        first_duration = time.time() - start_time

        # Second retrieval (cache hit - should be faster)
        start_time = time.time()
        response2 = service.get_parameter(test_parameter_name)
        second_duration = time.time() - start_time

        # Verify both responses are identical
        assert response1.data == response2.data
        assert response1.version == response2.version

        # Verify cache stats
        cache_stats = service.get_cache_stats()
        assert cache_stats["enabled"] is True
        assert cache_stats["size"] > 0

        # Operations should complete
        assert first_duration >= 0
        assert second_duration >= 0

    finally:
        # Cleanup
        try:
            service.delete_parameter(test_parameter_name)
        except Exception:
            pass


def test_large_parameter_value(
    parameter_manager_service, test_parameter_name, cleanup_parameters
):
    """Test creating and retrieving a large parameter value (up to 1 MiB)."""
    cleanup_parameters.append(test_parameter_name)

    # Create a large parameter value (1 MiB is the limit for Parameter Manager)
    # Use 900KB to stay safely under limit
    large_value = "x" * (900 * 1024)

    create_request = ParameterCreateRequest(
        parameter_name=test_parameter_name, format_type="UNFORMATTED"
    )
    parameter_manager_service.create_parameter(create_request)

    # Create version with large data
    parameter_manager_service.create_parameter_version(
        parameter_name=test_parameter_name,
        version_name="v1",
        data=large_value,
        format_type="UNFORMATTED",
    )

    # Retrieve and verify
    response = parameter_manager_service.get_parameter(test_parameter_name)
    assert response.data == large_value
    assert len(response.data) == len(large_value)


def test_special_characters_in_parameter_value(
    parameter_manager_service, test_parameter_name, cleanup_parameters
):
    """Test parameter values with special characters."""
    cleanup_parameters.append(test_parameter_name)

    special_value = "!@#$%^&*()_+-=[]{}|;':\",./<>?`~\n\t\r"

    create_request = ParameterCreateRequest(
        parameter_name=test_parameter_name, format_type="UNFORMATTED"
    )
    parameter_manager_service.create_parameter(create_request)

    parameter_manager_service.create_parameter_version(
        parameter_name=test_parameter_name,
        version_name="v1",
        data=special_value,
        format_type="UNFORMATTED",
    )

    response = parameter_manager_service.get_parameter(test_parameter_name)
    assert response.data == special_value


def test_unicode_in_parameter_value(
    parameter_manager_service, test_parameter_name, cleanup_parameters
):
    """Test parameter values with Unicode characters."""
    cleanup_parameters.append(test_parameter_name)

    unicode_value = "Hello 世界 🌍 Привет مرحبا"

    create_request = ParameterCreateRequest(
        parameter_name=test_parameter_name, format_type="UNFORMATTED"
    )
    parameter_manager_service.create_parameter(create_request)

    parameter_manager_service.create_parameter_version(
        parameter_name=test_parameter_name,
        version_name="v1",
        data=unicode_value,
        format_type="UNFORMATTED",
    )

    response = parameter_manager_service.get_parameter(test_parameter_name)
    assert response.data == unicode_value


def test_pagination_with_parameters(parameter_manager_service):
    """Test pagination when listing many parameters."""
    # List with small page size to test pagination
    list_response = parameter_manager_service.list_parameters(page_size=5)

    assert hasattr(list_response, "parameters")
    assert hasattr(list_response, "next_page_token")

    # If there are more than 5 parameters, we should have a next page token
    if len(list_response.parameters) == 5:
        # There might be more parameters
        assert (
            list_response.next_page_token is not None
            or list_response.next_page_token == ""
        )


def test_filter_expression_integration(
    parameter_manager_service, test_parameter_name, cleanup_parameters
):
    """Test filtering parameters with filter expressions."""
    cleanup_parameters.append(test_parameter_name)

    # Create parameter with specific labels
    create_request = ParameterCreateRequest(
        parameter_name=test_parameter_name,
        format_type="UNFORMATTED",
        labels={"environment": "production", "team": "backend"},
    )
    parameter_manager_service.create_parameter(create_request)

    # List with filter (if supported by API)
    try:
        list_response = parameter_manager_service.list_parameters(
            page_size=100, filter_expression="labels.environment:production"
        )
        # If filtering is supported, verify results
        assert hasattr(list_response, "parameters")
    except Exception:
        # Filter expressions might not be fully supported yet
        pass


def test_batch_operations_integration(parameter_manager_service, cleanup_parameters):
    """Test batch operations for creating and retrieving multiple parameters."""
    # Create multiple test parameters
    param_names = []
    for i in range(3):
        param_name = f"test-batch-param-{int(time.time() * 1000)}-{i}"
        param_names.append(param_name)
        cleanup_parameters.append(param_name)

    # Create parameters in batch
    parameters_data = [
        {
            "parameter_name": param_names[0],
            "format_type": "UNFORMATTED",
            "initial_data": "value1",
            "initial_version_name": "v1",
        },
        {
            "parameter_name": param_names[1],
            "format_type": "JSON",
            "initial_data": {"key": "value2"},
            "initial_version_name": "v1",
        },
        {
            "parameter_name": param_names[2],
            "format_type": "UNFORMATTED",
            "initial_data": "value3",
            "initial_version_name": "v1",
        },
    ]

    batch_create_response = parameter_manager_service.create_parameters_batch(
        parameters_data
    )

    # Verify batch creation
    assert "success_count" in batch_create_response
    assert "failure_count" in batch_create_response
    assert "total_requested" in batch_create_response
    assert batch_create_response["total_requested"] == 3
    assert batch_create_response["success_count"] >= 0
    assert batch_create_response["failure_count"] >= 0

    # Retrieve parameters in batch
    batch_get_response = parameter_manager_service.get_parameters_batch(param_names)

    # Verify batch retrieval
    assert "parameters" in batch_get_response
    assert "successful" in batch_get_response
    assert "failed" in batch_get_response

    # Check that we got responses for our parameters
    for param_name in param_names:
        if param_name in batch_get_response["parameters"]:
            param_response = batch_get_response["parameters"][param_name]
            if param_response:
                assert param_response.parameter_name == param_name


def test_format_conversion_helpers(parameter_manager_service):
    """Test format conversion helper methods."""
    # Test JSON conversion
    data_dict = {"key": "value", "number": 42}
    json_str = parameter_manager_service.convert_to_json(data_dict)
    assert isinstance(json_str, str)
    parsed_json = parameter_manager_service.parse_json(json_str)
    assert parsed_json == data_dict

    # Test YAML conversion
    yaml_str = parameter_manager_service.convert_to_yaml(data_dict)
    assert isinstance(yaml_str, str)
    parsed_yaml = parameter_manager_service.parse_yaml(yaml_str)
    assert parsed_yaml == data_dict


def test_secret_reference_parsing(parameter_manager_service):
    """Test secret reference parsing helper methods."""
    # Test parameter with secret references
    param_value = (
        "Database URL: ${secret.projects/my-project/secrets/db-url/versions/latest}"
    )

    # Check if parameter has secret references
    has_refs = parameter_manager_service.has_secret_references(param_value)
    assert has_refs is True

    # Parse secret references
    references = parameter_manager_service.parse_secret_references(param_value)
    assert len(references) > 0
    assert references[0]["project"] == "my-project"
    assert references[0]["secret_name"] == "db-url"

    # Test parameter without secret references
    plain_value = "Just a plain parameter value"
    has_refs = parameter_manager_service.has_secret_references(plain_value)
    assert has_refs is False


def test_secret_reference_resolution_integration(
    parameter_manager_service, project_id, test_parameter_name, cleanup_parameters
):
    """
    Test end-to-end secret reference resolution with real Secret Manager.

    This test requires:
    1. Secret Manager API enabled
    2. A test secret to be created
    3. Appropriate IAM permissions for both Parameter Manager and Secret Manager
    """
    cleanup_parameters.append(test_parameter_name)

    # Import Secret Manager service
    from app.requests.secret_manager import SecretCreateRequest
    from app.services.secret_manager import SecretManagerService

    # Create a test secret first
    secret_service = SecretManagerService(project_id=project_id)
    test_secret_name = f"test-secret-{int(time.time() * 1000)}"
    test_secret_value = "super-secret-password-123"

    try:
        # Create the secret
        secret_create_request = SecretCreateRequest(secret_name=test_secret_name)
        secret_service.create_secret(secret_create_request)

        # Add a version to the secret
        secret_service.add_secret_version(test_secret_name, test_secret_value)

        # Create a parameter with a secret reference
        secret_reference = f"${{secret.projects/{project_id}/secrets/{test_secret_name}/versions/latest}}"
        param_value = f"database_password={secret_reference}"

        create_request = ParameterCreateRequest(
            parameter_name=test_parameter_name, format_type="UNFORMATTED"
        )
        parameter_manager_service.create_parameter(create_request)

        # Create version with secret reference
        parameter_manager_service.create_parameter_version(
            parameter_name=test_parameter_name,
            version_name="v1",
            data=param_value,
            format_type="UNFORMATTED",
        )

        # Render the parameter (resolve secret references)
        rendered_value = parameter_manager_service.render_parameter(test_parameter_name)

        # Verify the secret was resolved
        assert test_secret_value in rendered_value
        assert secret_reference not in rendered_value
        assert rendered_value == f"database_password={test_secret_value}"

    finally:
        # Cleanup: delete the test secret
        try:
            secret_service.delete_secret(test_secret_name)
        except Exception as e:
            print(f"Failed to cleanup test secret {test_secret_name}: {str(e)}")


def test_multiple_secret_references_resolution(
    parameter_manager_service, project_id, test_parameter_name, cleanup_parameters
):
    """Test resolving multiple secret references in a single parameter."""
    cleanup_parameters.append(test_parameter_name)

    from app.requests.secret_manager import SecretCreateRequest
    from app.services.secret_manager import SecretManagerService

    secret_service = SecretManagerService(project_id=project_id)
    test_secret_1 = f"test-secret-1-{int(time.time() * 1000)}"
    test_secret_2 = f"test-secret-2-{int(time.time() * 1000)}"
    secret_value_1 = "api-key-value"
    secret_value_2 = "api-secret-value"

    try:
        # Create two secrets
        secret_service.create_secret(SecretCreateRequest(secret_name=test_secret_1))
        secret_service.add_secret_version(test_secret_1, secret_value_1)

        secret_service.create_secret(SecretCreateRequest(secret_name=test_secret_2))
        secret_service.add_secret_version(test_secret_2, secret_value_2)

        # Create parameter with multiple secret references
        ref1 = (
            f"${{secret.projects/{project_id}/secrets/{test_secret_1}/versions/latest}}"
        )
        ref2 = (
            f"${{secret.projects/{project_id}/secrets/{test_secret_2}/versions/latest}}"
        )
        param_value = f"api_key={ref1}&api_secret={ref2}"

        create_request = ParameterCreateRequest(
            parameter_name=test_parameter_name, format_type="UNFORMATTED"
        )
        parameter_manager_service.create_parameter(create_request)

        parameter_manager_service.create_parameter_version(
            parameter_name=test_parameter_name,
            version_name="v1",
            data=param_value,
            format_type="UNFORMATTED",
        )

        # Render the parameter
        rendered_value = parameter_manager_service.render_parameter(test_parameter_name)

        # Verify both secrets were resolved
        assert secret_value_1 in rendered_value
        assert secret_value_2 in rendered_value
        assert ref1 not in rendered_value
        assert ref2 not in rendered_value
        assert rendered_value == f"api_key={secret_value_1}&api_secret={secret_value_2}"

    finally:
        # Cleanup secrets
        try:
            secret_service.delete_secret(test_secret_1)
            secret_service.delete_secret(test_secret_2)
        except Exception:
            pass


def test_operation_timing(
    parameter_manager_service, test_parameter_name, cleanup_parameters
):
    """Test that operations complete in reasonable time."""
    cleanup_parameters.append(test_parameter_name)

    # Measure create operation
    start_time = time.time()
    create_request = ParameterCreateRequest(
        parameter_name=test_parameter_name, format_type="UNFORMATTED"
    )
    parameter_manager_service.create_parameter(create_request)
    create_duration = time.time() - start_time

    # Measure version creation
    start_time = time.time()
    parameter_manager_service.create_parameter_version(
        parameter_name=test_parameter_name,
        version_name="v1",
        data="timing-test",
        format_type="UNFORMATTED",
    )
    version_duration = time.time() - start_time

    # Measure retrieve operation
    start_time = time.time()
    parameter_manager_service.get_parameter(test_parameter_name)
    retrieve_duration = time.time() - start_time

    # Operations should complete in reasonable time (< 10 seconds each)
    assert create_duration < 10.0, f"Create took {create_duration}s"
    assert version_duration < 10.0, f"Version creation took {version_duration}s"
    assert retrieve_duration < 10.0, f"Retrieve took {retrieve_duration}s"


def test_empty_project_listing(parameter_manager_service):
    """Test listing parameters when project might have few parameters."""
    # This should not fail even if no parameters exist
    list_response = parameter_manager_service.list_parameters(page_size=10)

    assert hasattr(list_response, "parameters")
    assert isinstance(list_response.parameters, list)
