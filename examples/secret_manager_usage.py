"""
Secret Manager Service Usage Examples

This file demonstrates how to use the SecretManagerService class
following the Spartan Serverless Framework patterns.

The examples cover:
- Basic secret creation and retrieval
- Version management
- Secret listing and discovery
- Error handling
- Caching configuration
- Advanced usage patterns
"""

import os
from datetime import datetime

from app.exceptions.secret_manager import (
    SecretAccessDeniedException,
    SecretManagerException,
    SecretNotFoundException,
)
from app.helpers.logger import get_logger
from app.requests.secret_manager import SecretCreateRequest, SecretVersionCreateRequest
from app.services.secret_manager import SecretManagerService

# Initialize logger
logger = get_logger("secret_manager_examples")


def example_basic_usage():
    """
    Example 1: Basic Secret Creation and Retrieval

    Demonstrates the most common use case: creating a secret and retrieving it.
    """
    print("\n=== Example 1: Basic Secret Creation and Retrieval ===\n")

    # Initialize the service (project_id will be auto-detected from environment)
    service = SecretManagerService()

    # Create a new secret
    create_request = SecretCreateRequest(
        secret_name="database-password",
        secret_value="super-secret-password-123",
        replication_policy="automatic",
    )

    try:
        # Create the secret
        create_response = service.create_secret(create_request)
        print(f"✓ Secret created: {create_response.secret_name}")
        print(f"  Version: {create_response.version}")
        print(f"  Created: {create_response.created_time}")

        # Retrieve the secret
        secret_response = service.get_secret("database-password")
        print(f"\n✓ Secret retrieved: {secret_response.secret_name}")
        print(f"  Value: {secret_response.secret_value}")
        print(f"  Version: {secret_response.version}")

    except SecretManagerException as e:
        print(f"✗ Error: {e}")


def example_version_management():
    """
    Example 2: Secret Version Management

    Demonstrates how to manage multiple versions of a secret.
    """
    print("\n=== Example 2: Secret Version Management ===\n")

    service = SecretManagerService()

    try:
        # Add a new version to an existing secret
        version_request = SecretVersionCreateRequest(
            secret_name="database-password", secret_value="new-improved-password-456"
        )

        version_response = service.add_secret_version(version_request)
        print(f"✓ New version created: {version_response.version}")

        # List all versions
        versions_response = service.list_secret_versions("database-password")
        print(f"\n✓ Total versions: {len(versions_response.versions)}")
        for version in versions_response.versions:
            print(
                f"  - Version {version.version}: {version.state} (created: {version.created_time})"
            )

        # Retrieve a specific version
        specific_version = service.get_secret("database-password", version="1")
        print(f"\n✓ Retrieved version 1: {specific_version.secret_value}")

        # Disable a version
        disable_response = service.disable_secret_version("database-password", "1")
        print(f"\n✓ {disable_response.message}")

    except SecretManagerException as e:
        print(f"✗ Error: {e}")


def example_secret_discovery():
    """
    Example 3: Secret Discovery and Listing

    Demonstrates how to discover and list secrets in a project.
    """
    print("\n=== Example 3: Secret Discovery and Listing ===\n")

    service = SecretManagerService()

    try:
        # List all secrets
        list_response = service.list_secrets(page_size=10)
        print(f"✓ Found {len(list_response.secrets)} secrets:")

        for secret in list_response.secrets:
            print(f"\n  Secret: {secret.secret_name}")
            print(f"    Created: {secret.created_time}")
            print(f"    Versions: {secret.version_count}")
            print(f"    Replication: {secret.replication_policy}")
            if secret.labels:
                print(f"    Labels: {secret.labels}")

        # Get metadata for a specific secret (without the value)
        metadata = service.get_secret_metadata("database-password")
        print(f"\n✓ Metadata for {metadata.secret_name}:")
        print(f"  Created: {metadata.created_time}")
        print(f"  Versions: {metadata.version_count}")

    except SecretManagerException as e:
        print(f"✗ Error: {e}")


def example_error_handling():
    """
    Example 4: Error Handling

    Demonstrates proper error handling for various scenarios.
    """
    print("\n=== Example 4: Error Handling ===\n")

    service = SecretManagerService()

    # Try to access a non-existent secret
    try:
        service.get_secret("non-existent-secret")
    except SecretNotFoundException as e:
        print(f"✓ Caught expected error: {e}")

    # Try to access a disabled version
    try:
        # First disable a version
        service.disable_secret_version("database-password", "1")
        # Then try to access it
        service.get_secret("database-password", version="1")
    except SecretNotFoundException as e:
        print(f"✓ Caught expected error: {e}")

    # Handle permission denied errors
    try:
        # This would fail if credentials don't have proper permissions
        service.create_secret(
            SecretCreateRequest(secret_name="test-secret", secret_value="test-value")
        )
    except SecretAccessDeniedException as e:
        print(f"✓ Caught permission error: {e}")
    except SecretManagerException as e:
        # Secret might already exist or other error
        print(f"✓ Caught error: {e}")


def example_with_labels():
    """
    Example 5: Using Labels for Organization

    Demonstrates how to use labels to organize secrets.
    """
    print("\n=== Example 5: Using Labels for Organization ===\n")

    service = SecretManagerService()

    try:
        # Create secrets with labels
        environments = ["dev", "staging", "prod"]

        for env in environments:
            create_request = SecretCreateRequest(
                secret_name=f"api-key-{env}",
                secret_value=f"key-for-{env}-environment",
                labels={
                    "environment": env,
                    "service": "api",
                    "managed-by": "spartan-framework",
                },
            )

            response = service.create_secret(create_request)
            print(f"✓ Created secret for {env}: {response.secret_name}")

        # List all secrets and filter by labels
        list_response = service.list_secrets()
        api_secrets = [
            s
            for s in list_response.secrets
            if s.labels and s.labels.get("service") == "api"
        ]

        print(f"\n✓ Found {len(api_secrets)} API secrets:")
        for secret in api_secrets:
            env = secret.labels.get("environment", "unknown")
            print(f"  - {secret.secret_name} ({env})")

    except SecretManagerException as e:
        print(f"✗ Error: {e}")


def example_caching():
    """
    Example 6: Using Caching for Performance

    Demonstrates how to enable and use caching for improved performance.
    """
    print("\n=== Example 6: Using Caching for Performance ===\n")

    # Initialize service with caching enabled
    service = SecretManagerService(
        enable_cache=True, cache_ttl_seconds=300  # 5 minutes
    )

    try:
        # First retrieval - will hit the API
        print("First retrieval (cache miss)...")
        start_time = datetime.now()
        secret1 = service.get_secret("database-password")
        duration1 = (datetime.now() - start_time).total_seconds() * 1000
        print(f"✓ Retrieved in {duration1:.2f}ms")

        # Second retrieval - will hit the cache
        print("\nSecond retrieval (cache hit)...")
        start_time = datetime.now()
        secret2 = service.get_secret("database-password")
        duration2 = (datetime.now() - start_time).total_seconds() * 1000
        print(f"✓ Retrieved in {duration2:.2f}ms")

        print(f"\nCache speedup: {duration1/duration2:.1f}x faster")

        # Get cache statistics
        stats = service.get_cache_stats()
        print(f"\n✓ Cache statistics:")
        print(f"  Enabled: {stats['enabled']}")
        print(f"  Size: {stats['size']}")
        print(f"  TTL: {stats['ttl_seconds']}s")

        # Clear cache manually if needed
        service.clear_cache()
        print(f"\n✓ Cache cleared")

    except SecretManagerException as e:
        print(f"✗ Error: {e}")


def example_custom_credentials():
    """
    Example 7: Using Custom Credentials

    Demonstrates how to initialize the service with custom credentials.
    """
    print("\n=== Example 7: Using Custom Credentials ===\n")

    # Option 1: Using service account key file path
    try:
        service = SecretManagerService(
            project_id="my-project-id",
            credentials_path="/path/to/service-account-key.json",
        )
        print("✓ Service initialized with service account key file")
    except SecretManagerException as e:
        print(f"Note: {e}")

    # Option 2: Using credentials JSON string
    try:
        credentials_json = '{"type": "service_account", ...}'
        service = SecretManagerService(
            project_id="my-project-id", credentials=credentials_json
        )
        print("✓ Service initialized with credentials JSON")
    except SecretManagerException as e:
        print(f"Note: {e}")

    # Option 3: Using default credentials (ADC)
    try:
        service = SecretManagerService()
        print("✓ Service initialized with default credentials")
    except SecretManagerException as e:
        print(f"✗ Error: {e}")


def example_pagination():
    """
    Example 8: Handling Pagination

    Demonstrates how to handle paginated results when listing secrets.
    """
    print("\n=== Example 8: Handling Pagination ===\n")

    service = SecretManagerService()

    try:
        all_secrets = []
        page_token = None
        page_num = 1

        # Iterate through all pages
        while True:
            print(f"Fetching page {page_num}...")
            response = service.list_secrets(page_size=10, page_token=page_token)

            all_secrets.extend(response.secrets)
            print(f"✓ Retrieved {len(response.secrets)} secrets")

            # Check if there are more pages
            if not response.next_page_token:
                break

            page_token = response.next_page_token
            page_num += 1

        print(f"\n✓ Total secrets retrieved: {len(all_secrets)}")

    except SecretManagerException as e:
        print(f"✗ Error: {e}")


def example_cleanup():
    """
    Example 9: Cleanup and Secret Deletion

    Demonstrates how to properly clean up secrets.
    """
    print("\n=== Example 9: Cleanup and Secret Deletion ===\n")

    service = SecretManagerService()

    try:
        # List secrets to delete
        secrets_to_delete = [
            "database-password",
            "api-key-dev",
            "api-key-staging",
            "api-key-prod",
        ]

        for secret_name in secrets_to_delete:
            try:
                response = service.delete_secret(secret_name)
                print(f"✓ {response.message}")
            except SecretNotFoundException:
                print(f"  Secret '{secret_name}' not found (already deleted)")

        print("\n✓ Cleanup complete")

    except SecretManagerException as e:
        print(f"✗ Error: {e}")


def example_framework_integration():
    """
    Example 10: Integration with Spartan Framework

    Demonstrates how to integrate the Secret Manager service
    with other Spartan Framework components.
    """
    print("\n=== Example 10: Framework Integration ===\n")

    # The service automatically integrates with framework logging
    service = SecretManagerService()

    try:
        # All operations are automatically logged with structured logging
        secret = service.get_secret("database-password")

        # Use the secret in your application
        database_url = f"postgresql://user:{secret.secret_value}@localhost/mydb"
        print(f"✓ Database URL configured (password from Secret Manager)")

        # The service respects framework environment configuration
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        print(f"✓ Using project: {project_id}")

        # Error handling follows framework patterns
        print("✓ All operations logged with framework logger")

    except SecretManagerException as e:
        logger.error("Failed to retrieve secret", extra={"error": str(e)})
        print(f"✗ Error: {e}")


def main():
    """
    Run all examples.

    Note: These examples assume you have:
    1. Google Cloud credentials configured
    2. A Google Cloud project with Secret Manager API enabled
    3. Appropriate IAM permissions for Secret Manager operations
    """
    print("=" * 60)
    print("Secret Manager Service Usage Examples")
    print("=" * 60)

    examples = [
        ("Basic Usage", example_basic_usage),
        ("Version Management", example_version_management),
        ("Secret Discovery", example_secret_discovery),
        ("Error Handling", example_error_handling),
        ("Using Labels", example_with_labels),
        ("Caching", example_caching),
        ("Custom Credentials", example_custom_credentials),
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
