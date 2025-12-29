"""
Parameter Manager Service Usage Examples

This file demonstrates how to use the ParameterManagerService class
following the Spartan Serverless Framework patterns.

The examples cover:
- Basic parameter creation and retrieval
- Version management with custom version names
- Parameter listing and discovery
- Format types (UNFORMATTED, JSON, YAML)
- Secret Manager integration
- Error handling
- Caching configuration
- Batch operations
- Regional endpoints
- Advanced usage patterns
"""

import os
from datetime import datetime

from app.exceptions.parameter_manager import (
    ParameterAccessDeniedException,
    ParameterManagerException,
    ParameterNotFoundException,
    InvalidParameterValueException,
)
from app.helpers.logger import get_logger
from app.requests.parameter_manager import ParameterCreateRequest
from app.services.parameter_manager import ParameterManagerService

# Initialize logger
logger = get_logger("parameter_manager_examples")


def example_basic_usage():
    """
    Example 1: Basic Parameter Creation and Retrieval

    Demonstrates the most common use case: creating a parameter and retrieving it.
    """
    print("\n=== Example 1: Basic Parameter Creation and Retrieval ===\n")

    # Initialize the service (project_id will be auto-detected from environment)
    service = ParameterManagerService()

    # Create a new parameter with UNFORMATTED type (plain text)
    create_request = ParameterCreateRequest(
        parameter_name="app-timeout", format_type="UNFORMATTED"
    )

    try:
        # Create the parameter
        create_response = service.create_parameter(create_request)
        print(f"✓ Parameter created: {create_response.parameter_name}")
        print(f"  Format: {create_response.format_type}")
        print(f"  Created: {create_response.created_time}")

        # Create first version with data
        version_response = service.create_parameter_version(
            parameter_name="app-timeout",
            version_name="v1",
            data="30",
            format_type="UNFORMATTED",
        )
        print(f"\n✓ Version created: {version_response.version}")

        # Retrieve the parameter (gets latest version)
        parameter_response = service.get_parameter("app-timeout")
        print(f"\n✓ Parameter retrieved: {parameter_response.parameter_name}")
        print(f"  Value: {parameter_response.data}")
        print(f"  Version: {parameter_response.version}")

    except ParameterManagerException as e:
        print(f"✗ Error: {e}")


def example_format_types():
    """
    Example 2: Working with Different Format Types

    Demonstrates how to use UNFORMATTED, JSON, and YAML format types.
    """
    print("\n=== Example 2: Working with Different Format Types ===\n")

    service = ParameterManagerService()

    try:
        # 1. UNFORMATTED - Plain text
        print("1. Creating UNFORMATTED parameter (plain text)...")
        create_request = ParameterCreateRequest(
            parameter_name="database-host", format_type="UNFORMATTED"
        )
        service.create_parameter(create_request)
        service.create_parameter_version(
            parameter_name="database-host",
            version_name="v1",
            data="localhost:5432",
            format_type="UNFORMATTED",
        )
        print("✓ UNFORMATTED parameter created")

        # 2. JSON - Structured data
        print("\n2. Creating JSON parameter (structured data)...")
        create_request = ParameterCreateRequest(
            parameter_name="app-config", format_type="JSON"
        )
        service.create_parameter(create_request)

        config_data = {
            "timeout": 30,
            "retries": 3,
            "endpoints": ["api1.example.com", "api2.example.com"],
        }
        service.create_parameter_version(
            parameter_name="app-config",
            version_name="v1",
            data=config_data,
            format_type="JSON",
        )
        print("✓ JSON parameter created")

        # Retrieve and use JSON data
        parameter = service.get_parameter("app-config")
        print(f"  Timeout: {parameter.data['timeout']} seconds")
        print(f"  Retries: {parameter.data['retries']}")

        # 3. YAML - Structured data in YAML format
        print("\n3. Creating YAML parameter...")
        create_request = ParameterCreateRequest(
            parameter_name="deployment-config", format_type="YAML"
        )
        service.create_parameter(create_request)

        yaml_data = {
            "environment": "production",
            "replicas": 3,
            "resources": {"cpu": "500m", "memory": "512Mi"},
        }
        service.create_parameter_version(
            parameter_name="deployment-config",
            version_name="v1",
            data=yaml_data,
            format_type="YAML",
        )
        print("✓ YAML parameter created")

    except InvalidParameterValueException as e:
        print(f"✗ Validation error: {e}")
    except ParameterManagerException as e:
        print(f"✗ Error: {e}")


def example_version_management():
    """
    Example 3: Parameter Version Management with Custom Names

    Demonstrates how to manage multiple versions with custom version names.
    """
    print("\n=== Example 3: Parameter Version Management ===\n")

    service = ParameterManagerService()

    try:
        # Create parameter
        create_request = ParameterCreateRequest(
            parameter_name="api-endpoint", format_type="UNFORMATTED"
        )
        service.create_parameter(create_request)

        # Create multiple versions with semantic names
        versions = [
            ("dev", "https://dev-api.example.com"),
            ("staging", "https://staging-api.example.com"),
            ("prod-2024-01", "https://api.example.com"),
        ]

        for version_name, endpoint in versions:
            version_response = service.create_parameter_version(
                parameter_name="api-endpoint",
                version_name=version_name,
                data=endpoint,
                format_type="UNFORMATTED",
            )
            print(f"✓ Created version '{version_name}': {endpoint}")

        # List all versions
        versions_response = service.list_parameter_versions("api-endpoint")
        print(f"\n✓ Total versions: {len(versions_response.versions)}")
        for version in versions_response.versions:
            print(f"  - Version {version.version}: {version.data}")

        # Retrieve a specific version
        prod_version = service.get_parameter_version("api-endpoint", "prod-2024-01")
        print(f"\n✓ Production endpoint: {prod_version.data}")

        # Delete an old version
        delete_response = service.delete_parameter_version("api-endpoint", "dev")
        print(f"\n✓ {delete_response.message}")

    except ParameterManagerException as e:
        print(f"✗ Error: {e}")


def example_parameter_discovery():
    """
    Example 4: Parameter Discovery and Listing

    Demonstrates how to discover and list parameters in a project.
    """
    print("\n=== Example 4: Parameter Discovery and Listing ===\n")

    service = ParameterManagerService()

    try:
        # List all parameters
        list_response = service.list_parameters(page_size=10)
        print(f"✓ Found {len(list_response.parameters)} parameters:")

        for param in list_response.parameters:
            print(f"\n  Parameter: {param.parameter_name}")
            print(f"    Format: {param.format_type}")
            print(f"    Created: {param.created_time}")
            print(f"    Versions: {param.version_count}")
            if param.labels:
                print(f"    Labels: {param.labels}")

        # Get metadata for a specific parameter (without the value)
        metadata = service.get_parameter_metadata("app-config")
        print(f"\n✓ Metadata for {metadata.parameter_name}:")
        print(f"  Format: {metadata.format_type}")
        print(f"  Versions: {metadata.version_count}")

        # Check if a parameter exists
        exists = service.parameter_exists("app-config")
        print(f"\n✓ Parameter 'app-config' exists: {exists}")

    except ParameterManagerException as e:
        print(f"✗ Error: {e}")


def example_error_handling():
    """
    Example 5: Error Handling

    Demonstrates proper error handling for various scenarios.
    """
    print("\n=== Example 5: Error Handling ===\n")

    service = ParameterManagerService()

    # Try to access a non-existent parameter
    try:
        service.get_parameter("non-existent-parameter")
    except ParameterNotFoundException as e:
        print(f"✓ Caught expected error: {e}")

    # Try to create parameter with invalid JSON
    try:
        create_request = ParameterCreateRequest(
            parameter_name="invalid-json", format_type="JSON"
        )
        service.create_parameter(create_request)
        service.create_parameter_version(
            parameter_name="invalid-json",
            version_name="v1",
            data="not valid json {",
            format_type="JSON",
        )
    except InvalidParameterValueException as e:
        print(f"✓ Caught validation error: {e}")

    # Handle permission denied errors
    try:
        # This would fail if credentials don't have proper permissions
        service.create_parameter(
            ParameterCreateRequest(
                parameter_name="test-parameter", format_type="UNFORMATTED"
            )
        )
    except ParameterAccessDeniedException as e:
        print(f"✓ Caught permission error: {e}")
    except ParameterManagerException as e:
        # Parameter might already exist or other error
        print(f"✓ Caught error: {e}")


def example_with_labels():
    """
    Example 6: Using Labels for Organization

    Demonstrates how to use labels to organize parameters.
    """
    print("\n=== Example 6: Using Labels for Organization ===\n")

    service = ParameterManagerService()

    try:
        # Create parameters with labels
        environments = ["dev", "staging", "prod"]

        for env in environments:
            create_request = ParameterCreateRequest(
                parameter_name=f"database-url-{env}",
                format_type="UNFORMATTED",
                labels={
                    "environment": env,
                    "service": "database",
                    "managed-by": "spartan-framework",
                },
            )

            response = service.create_parameter(create_request)
            print(f"✓ Created parameter for {env}: {response.parameter_name}")

            # Add version with data
            service.create_parameter_version(
                parameter_name=f"database-url-{env}",
                version_name="v1",
                data=f"postgresql://{env}-db:5432/myapp",
                format_type="UNFORMATTED",
            )

        # List all parameters and filter by labels
        list_response = service.list_parameters(
            filter_expression="labels.service=database"
        )

        print(f"\n✓ Found {len(list_response.parameters)} database parameters:")
        for param in list_response.parameters:
            env = (
                param.labels.get("environment", "unknown")
                if param.labels
                else "unknown"
            )
            print(f"  - {param.parameter_name} ({env})")

    except ParameterManagerException as e:
        print(f"✗ Error: {e}")


def example_caching():
    """
    Example 7: Using Caching for Performance

    Demonstrates how to enable and use caching for improved performance.
    """
    print("\n=== Example 7: Using Caching for Performance ===\n")

    # Initialize service with caching enabled
    service = ParameterManagerService(
        enable_cache=True, cache_ttl_seconds=300  # 5 minutes
    )

    try:
        # First retrieval - will hit the API
        print("First retrieval (cache miss)...")
        start_time = datetime.now()
        param1 = service.get_parameter("app-config")
        duration1 = (datetime.now() - start_time).total_seconds() * 1000
        print(f"✓ Retrieved in {duration1:.2f}ms")

        # Second retrieval - will hit the cache
        print("\nSecond retrieval (cache hit)...")
        start_time = datetime.now()
        param2 = service.get_parameter("app-config")
        duration2 = (datetime.now() - start_time).total_seconds() * 1000
        print(f"✓ Retrieved in {duration2:.2f}ms")

        if duration1 > duration2:
            print(f"\nCache speedup: {duration1/duration2:.1f}x faster")

        # Get cache statistics
        stats = service.get_cache_stats()
        print(f"\n✓ Cache statistics:")
        print(f"  Enabled: {stats['enabled']}")
        print(f"  Size: {stats['size']}")
        print(f"  Active entries: {stats['active_entries']}")
        print(f"  TTL: {stats['ttl_seconds']}s")

        # Clear cache manually if needed
        service.clear_cache()
        print(f"\n✓ Cache cleared")

    except ParameterManagerException as e:
        print(f"✗ Error: {e}")


def example_secret_references():
    """
    Example 8: Secret Manager Integration

    Demonstrates how to use Secret Manager references within parameters.
    """
    print("\n=== Example 8: Secret Manager Integration ===\n")

    service = ParameterManagerService()

    try:
        # Create a parameter with secret references
        create_request = ParameterCreateRequest(
            parameter_name="database-connection", format_type="UNFORMATTED"
        )
        service.create_parameter(create_request)

        # Store connection string with secret reference
        connection_string = (
            "postgresql://user:${secret.projects/my-project/secrets/db-password/versions/latest}"
            "@localhost:5432/mydb"
        )

        service.create_parameter_version(
            parameter_name="database-connection",
            version_name="v1",
            data=connection_string,
            format_type="UNFORMATTED",
        )
        print("✓ Parameter with secret reference created")

        # Parse secret references
        references = service.parse_secret_references(connection_string)
        print(f"\n✓ Found {len(references)} secret reference(s):")
        for ref in references:
            print(f"  - Project: {ref['project_id']}")
            print(f"    Secret: {ref['secret_name']}")
            print(f"    Version: {ref['version']}")

        # Validate secret references
        validation = service.validate_secret_references(connection_string)
        print(f"\n✓ Validation result:")
        print(f"  Valid: {validation['valid']}")
        print(f"  Reference count: {validation['reference_count']}")

        # Render parameter (resolves secret references)
        # Note: This requires actual Secret Manager secrets to exist
        try:
            rendered_value = service.render_parameter("database-connection")
            print(f"\n✓ Rendered connection string (secrets resolved)")
        except ParameterManagerException as e:
            print(f"\nNote: Could not render (secrets may not exist): {e}")

    except ParameterManagerException as e:
        print(f"✗ Error: {e}")


def example_regional_endpoints():
    """
    Example 9: Using Regional Endpoints

    Demonstrates how to use regional endpoints for location-specific parameters.
    """
    print("\n=== Example 9: Using Regional Endpoints ===\n")

    try:
        # Create service with global location (default)
        global_service = ParameterManagerService(location="global")
        print("✓ Service initialized with global location")

        # Create service with regional location
        regional_service = ParameterManagerService(location="us-central1")
        print("✓ Service initialized with us-central1 location")

        # Create parameter in specific region
        create_request = ParameterCreateRequest(
            parameter_name="regional-config", format_type="JSON"
        )
        regional_service.create_parameter(create_request)

        regional_service.create_parameter_version(
            parameter_name="regional-config",
            version_name="v1",
            data={"region": "us-central1", "zone": "us-central1-a"},
            format_type="JSON",
        )
        print("✓ Regional parameter created in us-central1")

    except ParameterManagerException as e:
        print(f"✗ Error: {e}")


def example_batch_operations():
    """
    Example 10: Batch Operations for Efficiency

    Demonstrates how to use batch operations for improved performance.
    """
    print("\n=== Example 10: Batch Operations ===\n")

    service = ParameterManagerService(enable_cache=True, enable_connection_pooling=True)

    try:
        # Batch retrieve multiple parameters
        parameter_names = ["app-config", "database-url-prod", "api-endpoint"]

        print("Retrieving parameters in batch...")
        batch_result = service.get_parameters_batch(parameter_names)

        print(f"\n✓ Batch retrieval complete:")
        print(f"  Successful: {batch_result['successful']}")
        print(f"  Failed: {batch_result['failed']}")
        print(f"  Total time: {batch_result['total_time_ms']:.2f}ms")

        # Access retrieved parameters
        for param_name, param_data in batch_result["parameters"].items():
            print(f"\n  {param_name}:")
            print(f"    Value: {param_data.data}")
            print(f"    Version: {param_data.version}")

        # Batch create parameters
        parameters_to_create = [
            {
                "parameter_name": "feature-flag-1",
                "format_type": "JSON",
                "data": {"enabled": True},
                "version_name": "v1",
            },
            {
                "parameter_name": "feature-flag-2",
                "format_type": "JSON",
                "data": {"enabled": False},
                "version_name": "v1",
            },
        ]

        print("\n\nCreating parameters in batch...")
        create_result = service.create_parameters_batch(parameters_to_create)

        print(f"\n✓ Batch creation complete:")
        print(f"  Successful: {create_result['successful']}")
        print(f"  Failed: {create_result['failed']}")

        # Batch delete parameters
        print("\n\nDeleting parameters in batch...")
        delete_result = service.delete_parameters_batch(
            ["feature-flag-1", "feature-flag-2"]
        )

        print(f"\n✓ Batch deletion complete:")
        print(f"  Successful: {delete_result['successful']}")
        print(f"  Failed: {delete_result['failed']}")

    except ParameterManagerException as e:
        print(f"✗ Error: {e}")


def example_format_conversion():
    """
    Example 11: Format Conversion Helpers

    Demonstrates how to use format conversion helper methods.
    """
    print("\n=== Example 11: Format Conversion Helpers ===\n")

    service = ParameterManagerService()

    try:
        # Convert Python dict to JSON string
        config_dict = {
            "timeout": 30,
            "retries": 3,
            "endpoints": ["api1.example.com", "api2.example.com"],
        }

        json_str = service.convert_to_json(config_dict)
        print("✓ Converted dict to JSON:")
        print(f"  {json_str}")

        # Convert Python dict to YAML string
        yaml_str = service.convert_to_yaml(config_dict)
        print("\n✓ Converted dict to YAML:")
        print(f"  {yaml_str}")

        # Parse JSON string back to dict
        parsed_json = service.parse_json(json_str)
        print(f"\n✓ Parsed JSON back to dict:")
        print(f"  Timeout: {parsed_json['timeout']}")

        # Parse YAML string back to dict
        parsed_yaml = service.parse_yaml(yaml_str)
        print(f"\n✓ Parsed YAML back to dict:")
        print(f"  Retries: {parsed_yaml['retries']}")

    except InvalidParameterValueException as e:
        print(f"✗ Validation error: {e}")
    except ParameterManagerException as e:
        print(f"✗ Error: {e}")


def example_pagination():
    """
    Example 12: Handling Pagination

    Demonstrates how to handle paginated results when listing parameters.
    """
    print("\n=== Example 12: Handling Pagination ===\n")

    service = ParameterManagerService()

    try:
        all_parameters = []
        page_token = None
        page_num = 1

        # Iterate through all pages
        while True:
            print(f"Fetching page {page_num}...")
            response = service.list_parameters(page_size=10, page_token=page_token)

            all_parameters.extend(response.parameters)
            print(f"✓ Retrieved {len(response.parameters)} parameters")

            # Check if there are more pages
            if not response.next_page_token:
                break

            page_token = response.next_page_token
            page_num += 1

        print(f"\n✓ Total parameters retrieved: {len(all_parameters)}")

    except ParameterManagerException as e:
        print(f"✗ Error: {e}")


def example_cleanup():
    """
    Example 13: Cleanup and Parameter Deletion

    Demonstrates how to properly clean up parameters.
    """
    print("\n=== Example 13: Cleanup and Parameter Deletion ===\n")

    service = ParameterManagerService()

    try:
        # List parameters to delete
        parameters_to_delete = [
            "app-timeout",
            "database-host",
            "app-config",
            "deployment-config",
            "api-endpoint",
        ]

        for param_name in parameters_to_delete:
            try:
                response = service.delete_parameter(param_name)
                print(f"✓ {response.message}")
            except ParameterNotFoundException:
                print(f"  Parameter '{param_name}' not found (already deleted)")

        print("\n✓ Cleanup complete")

    except ParameterManagerException as e:
        print(f"✗ Error: {e}")


def example_framework_integration():
    """
    Example 14: Integration with Spartan Framework

    Demonstrates how to integrate the Parameter Manager service
    with other Spartan Framework components.
    """
    print("\n=== Example 14: Framework Integration ===\n")

    # The service automatically integrates with framework logging
    service = ParameterManagerService()

    try:
        # All operations are automatically logged with structured logging
        parameter = service.get_parameter("app-config")

        # Use the parameter in your application
        if isinstance(parameter.data, dict):
            timeout = parameter.data.get("timeout", 30)
            print(f"✓ Application timeout configured: {timeout}s")

        # The service respects framework environment configuration
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        print(f"✓ Using project: {project_id}")

        # Error handling follows framework patterns
        print("✓ All operations logged with framework logger")

        # Parameters can be used with other framework services
        print("✓ Ready for integration with other Spartan services")

    except ParameterManagerException as e:
        logger.error("Failed to retrieve parameter", extra={"error": str(e)})
        print(f"✗ Error: {e}")


def main():
    """
    Run all examples.

    Note: These examples assume you have:
    1. Google Cloud credentials configured
    2. A Google Cloud project with Parameter Manager API enabled
    3. Appropriate IAM permissions for Parameter Manager operations
    4. (Optional) Secret Manager secrets for secret reference examples
    """
    print("=" * 60)
    print("Parameter Manager Service Usage Examples")
    print("=" * 60)

    examples = [
        ("Basic Usage", example_basic_usage),
        ("Format Types", example_format_types),
        ("Version Management", example_version_management),
        ("Parameter Discovery", example_parameter_discovery),
        ("Error Handling", example_error_handling),
        ("Using Labels", example_with_labels),
        ("Caching", example_caching),
        ("Secret References", example_secret_references),
        ("Regional Endpoints", example_regional_endpoints),
        ("Batch Operations", example_batch_operations),
        ("Format Conversion", example_format_conversion),
        ("Pagination", example_pagination),
        ("Cleanup", example_cleanup),
        ("Framework Integration", example_framework_integration),
    ]

    for name, example_func in examples:
        try:
            example_func()
        except Exception as e:
            print(f"\n✗ Example '{name}' failed: {e}")

        print("\n" + "-" * 60)

    print("\n✓ All examples completed!")


if __name__ == "__main__":
    main()
