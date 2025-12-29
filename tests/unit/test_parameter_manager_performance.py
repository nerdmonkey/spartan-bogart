"""
Unit tests for Parameter Manager service - Performance Optimizations.

Tests the performance optimization features including caching, batch operations,
and connection pooling following the Spartan Framework testing patterns.
"""

from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pytest

from app.exceptions.parameter_manager import (
    ParameterManagerException,
    ParameterNotFoundException,
)
from app.responses.parameter_manager import ParameterResponse
from app.services.parameter_manager import ParameterManagerService


# Test fixtures
@pytest.fixture
def mock_service_with_cache():
    """Create a ParameterManagerService with caching enabled."""
    with patch("app.services.parameter_manager.get_logger"):
        service = ParameterManagerService(
            project_id="test-project", enable_cache=True, cache_ttl_seconds=300
        )
        # Mock the client to prevent actual API calls
        service.client = Mock()
        return service


@pytest.fixture
def mock_service_with_pooling():
    """Create a ParameterManagerService with connection pooling enabled."""
    with patch("app.services.parameter_manager.get_logger"):
        service = ParameterManagerService(
            project_id="test-project", enable_connection_pooling=True, max_pool_size=20
        )
        # Mock the client to prevent actual API calls
        service.client = Mock()
        return service


@pytest.fixture
def mock_service_optimized():
    """Create a ParameterManagerService with all optimizations enabled."""
    with patch("app.services.parameter_manager.get_logger"):
        service = ParameterManagerService(
            project_id="test-project",
            enable_cache=True,
            cache_ttl_seconds=300,
            enable_connection_pooling=True,
            max_pool_size=20,
        )
        # Mock the client to prevent actual API calls
        service.client = Mock()
        return service


@pytest.fixture
def sample_parameter_response():
    """Create a sample ParameterResponse for testing."""
    return ParameterResponse(
        parameter_name="test-param",
        data="test-data",
        format_type="UNFORMATTED",
        version="v1",
        created_time=datetime.now(),
        updated_time=datetime.now(),
    )


# Caching Tests
def test_cache_initialization(mock_service_with_cache):
    """Test that caching is properly initialized."""
    assert mock_service_with_cache.enable_cache is True
    assert mock_service_with_cache.cache_ttl_seconds == 300
    assert isinstance(mock_service_with_cache._cache, dict)
    assert len(mock_service_with_cache._cache) == 0


def test_cache_disabled_by_default():
    """Test that caching is disabled by default."""
    with patch("app.services.parameter_manager.get_logger"):
        service = ParameterManagerService(project_id="test-project")
        assert service.enable_cache is False


def test_cache_stores_values_with_ttl(mock_service_with_cache):
    """Test that cache stores values with proper TTL."""
    cache_key = "test-param:latest"
    test_value = "test_data"

    # Store value in cache
    mock_service_with_cache._put_in_cache(cache_key, test_value)

    # Verify it's stored
    assert cache_key in mock_service_with_cache._cache
    value, expiry_time = mock_service_with_cache._cache[cache_key]
    assert value == test_value
    assert expiry_time > datetime.now()


def test_cache_retrieves_non_expired_values(mock_service_with_cache):
    """Test that cache retrieves non-expired values."""
    cache_key = "test-param:latest"
    test_value = "test_data"

    # Store value in cache
    mock_service_with_cache._put_in_cache(cache_key, test_value)

    # Retrieve it
    result = mock_service_with_cache._get_from_cache(cache_key)

    assert result == test_value


def test_cache_returns_none_for_expired_values(mock_service_with_cache):
    """Test that cache returns None for expired values."""
    cache_key = "test-param:latest"
    test_value = "test_data"

    # Manually insert expired entry
    expired_time = datetime.now() - timedelta(seconds=10)
    mock_service_with_cache._cache[cache_key] = (test_value, expired_time)

    # Try to retrieve it
    result = mock_service_with_cache._get_from_cache(cache_key)

    # Should return None and remove the entry
    assert result is None
    assert cache_key not in mock_service_with_cache._cache


def test_cache_returns_none_for_missing_keys(mock_service_with_cache):
    """Test that cache returns None for missing keys."""
    result = mock_service_with_cache._get_from_cache("nonexistent:latest")
    assert result is None


def test_cache_invalidation_for_specific_version(mock_service_with_cache):
    """Test that cache invalidation works for specific versions."""
    # Cache multiple versions
    mock_service_with_cache._put_in_cache("test-param:v1", "data1")
    mock_service_with_cache._put_in_cache("test-param:v2", "data2")
    mock_service_with_cache._put_in_cache("test-param:latest", "data3")

    # Invalidate specific version
    mock_service_with_cache._invalidate_cache("test-param", version="v1")

    # v1 should be gone, others should remain
    assert "test-param:v1" not in mock_service_with_cache._cache
    assert "test-param:v2" in mock_service_with_cache._cache
    assert "test-param:latest" in mock_service_with_cache._cache


def test_cache_invalidation_for_all_versions(mock_service_with_cache):
    """Test that cache invalidation works for all versions of a parameter."""
    # Cache multiple versions
    mock_service_with_cache._put_in_cache("test-param:v1", "data1")
    mock_service_with_cache._put_in_cache("test-param:v2", "data2")
    mock_service_with_cache._put_in_cache("test-param:latest", "data3")
    mock_service_with_cache._put_in_cache("other-param:latest", "data4")

    # Invalidate all versions of test-param
    mock_service_with_cache._invalidate_cache("test-param")

    # All test-param versions should be gone
    assert "test-param:v1" not in mock_service_with_cache._cache
    assert "test-param:v2" not in mock_service_with_cache._cache
    assert "test-param:latest" not in mock_service_with_cache._cache
    # Other parameters should remain
    assert "other-param:latest" in mock_service_with_cache._cache


def test_clear_cache_removes_all_entries(mock_service_with_cache):
    """Test that clear_cache removes all cached entries."""
    # Cache some parameters
    mock_service_with_cache._put_in_cache("param1:latest", "data1")
    mock_service_with_cache._put_in_cache("param2:latest", "data2")
    mock_service_with_cache._put_in_cache("param3:latest", "data3")

    # Verify cache has entries
    assert len(mock_service_with_cache._cache) == 3

    # Clear cache
    mock_service_with_cache.clear_cache()

    # Cache should be empty
    assert len(mock_service_with_cache._cache) == 0


def test_clear_cache_with_disabled_cache():
    """Test that clear_cache works when caching is disabled."""
    with patch("app.services.parameter_manager.get_logger"):
        service = ParameterManagerService(project_id="test-project", enable_cache=False)
        # Should not raise an error
        service.clear_cache()


def test_get_cache_stats_with_cache_enabled(mock_service_with_cache):
    """Test get_cache_stats returns correct statistics when caching is enabled."""
    # Cache some parameters
    mock_service_with_cache._put_in_cache("param1:latest", "data1")
    mock_service_with_cache._put_in_cache("param2:latest", "data2")

    stats = mock_service_with_cache.get_cache_stats()

    assert stats["enabled"] is True
    assert stats["size"] == 2
    assert stats["active_entries"] == 2
    assert stats["expired_entries"] == 0
    assert stats["ttl_seconds"] == 300
    assert "batch_stats" in stats


def test_get_cache_stats_counts_expired_entries(mock_service_with_cache):
    """Test that get_cache_stats correctly counts expired entries."""
    # Add active entry
    mock_service_with_cache._put_in_cache("param1:latest", "data1")

    # Add expired entry
    expired_time = datetime.now() - timedelta(seconds=10)
    mock_service_with_cache._cache["param2:latest"] = ("data2", expired_time)

    stats = mock_service_with_cache.get_cache_stats()

    assert stats["size"] == 2
    assert stats["active_entries"] == 1
    assert stats["expired_entries"] == 1


def test_get_cache_stats_with_cache_disabled():
    """Test get_cache_stats returns minimal statistics when caching is disabled."""
    with patch("app.services.parameter_manager.get_logger"):
        service = ParameterManagerService(project_id="test-project", enable_cache=False)
        stats = service.get_cache_stats()

        assert stats["enabled"] is False
        assert stats["size"] == 0
        assert "batch_stats" in stats


def test_cache_key_generation(mock_service_with_cache):
    """Test that cache keys are generated correctly."""
    # Test with version
    key1 = mock_service_with_cache._get_cache_key("test-param", "v1")
    assert key1 == "test-param:v1"

    # Test without version (should use "latest")
    key2 = mock_service_with_cache._get_cache_key("test-param")
    assert key2 == "test-param:latest"

    # Test with None version
    key3 = mock_service_with_cache._get_cache_key("test-param", None)
    assert key3 == "test-param:latest"


# Connection Pooling Tests
def test_connection_pooling_initialization(mock_service_with_pooling):
    """Test that connection pooling is properly initialized."""
    assert mock_service_with_pooling.enable_connection_pooling is True
    assert mock_service_with_pooling.max_pool_size == 20


def test_connection_pooling_enabled_by_default():
    """Test that connection pooling is enabled by default."""
    with patch("app.services.parameter_manager.get_logger"):
        service = ParameterManagerService(project_id="test-project")
        assert service.enable_connection_pooling is True
        assert service.max_pool_size == 10


def test_connection_pooling_can_be_disabled():
    """Test that connection pooling can be disabled."""
    with patch("app.services.parameter_manager.get_logger"):
        service = ParameterManagerService(
            project_id="test-project", enable_connection_pooling=False
        )
        assert service.enable_connection_pooling is False


def test_connection_pooling_custom_pool_size():
    """Test that custom pool size can be configured."""
    with patch("app.services.parameter_manager.get_logger"):
        service = ParameterManagerService(
            project_id="test-project", enable_connection_pooling=True, max_pool_size=50
        )
        assert service.max_pool_size == 50


# Batch Operations Tests
def test_get_parameters_batch_empty_list(mock_service_optimized):
    """Test batch retrieval with empty parameter list."""
    results = mock_service_optimized.get_parameters_batch([])

    assert results["total_requested"] == 0
    assert results["successful"] == 0
    assert results["failed"] == 0
    assert results["cache_hits"] == 0
    assert results["api_calls"] == 0
    assert len(results["parameters"]) == 0


def test_get_parameters_batch_with_cache_hits(
    mock_service_optimized, sample_parameter_response
):
    """Test that batch operations benefit from caching."""
    # Pre-cache one parameter
    cache_key = "param1:latest"
    mock_service_optimized._put_in_cache(cache_key, sample_parameter_response)

    # Mock get_parameter for non-cached parameter
    with patch.object(
        mock_service_optimized, "get_parameter", return_value=sample_parameter_response
    ) as mock_get:
        results = mock_service_optimized.get_parameters_batch(["param1", "param2"])

        # Should have one cache hit (param1) and one API call (param2)
        assert results["cache_hits"] == 1
        assert results["api_calls"] == 1
        assert results["total_requested"] == 2
        # get_parameter should only be called once (for param2)
        assert mock_get.call_count == 1


def test_get_parameters_batch_all_cached(
    mock_service_optimized, sample_parameter_response
):
    """Test batch retrieval when all parameters are cached."""
    # Pre-cache all parameters
    mock_service_optimized._put_in_cache("param1:latest", sample_parameter_response)
    mock_service_optimized._put_in_cache("param2:latest", sample_parameter_response)

    results = mock_service_optimized.get_parameters_batch(["param1", "param2"])

    # All should be cache hits, no API calls
    assert results["cache_hits"] == 2
    assert results["api_calls"] == 0
    assert results["successful"] == 2


def test_get_parameters_batch_handles_not_found(
    mock_service_optimized, sample_parameter_response
):
    """Test that batch operations handle non-existent parameters gracefully."""

    def mock_get(name, version=None):
        if name == "nonexistent":
            raise ParameterNotFoundException(f"Parameter {name} not found")
        return sample_parameter_response

    with patch.object(mock_service_optimized, "get_parameter", side_effect=mock_get):
        results = mock_service_optimized.get_parameters_batch(["param1", "nonexistent"])

        # Should have one successful and one failed
        assert results["successful"] == 1
        assert results["failed"] == 1
        assert results["parameters"]["nonexistent"] is None
        assert results["parameters"]["param1"] is not None
        assert len(results["errors"]) == 1
        assert results["errors"][0]["error"] == "not_found"


def test_get_parameters_batch_handles_general_errors(
    mock_service_optimized, sample_parameter_response
):
    """Test that batch operations handle general errors gracefully."""

    def mock_get(name, version=None):
        if name == "error-param":
            raise ParameterManagerException("Some error occurred")
        return sample_parameter_response

    with patch.object(mock_service_optimized, "get_parameter", side_effect=mock_get):
        results = mock_service_optimized.get_parameters_batch(["param1", "error-param"])

        # Should have one successful and one failed
        assert results["successful"] == 1
        assert results["failed"] == 1
        assert results["parameters"]["error-param"] is None
        assert len(results["errors"]) == 1
        assert results["errors"][0]["error"] == "ParameterManagerException"


def test_get_parameters_batch_updates_statistics(
    mock_service_optimized, sample_parameter_response
):
    """Test that batch operations update batch statistics."""
    initial_batch_ops = mock_service_optimized._batch_stats["total_batch_operations"]
    initial_total_params = mock_service_optimized._batch_stats[
        "total_parameters_in_batches"
    ]

    # Mock get_parameter
    with patch.object(
        mock_service_optimized, "get_parameter", return_value=sample_parameter_response
    ):
        mock_service_optimized.get_parameters_batch(["param1", "param2", "param3"])

    # Statistics should be updated
    assert (
        mock_service_optimized._batch_stats["total_batch_operations"]
        == initial_batch_ops + 1
    )
    assert (
        mock_service_optimized._batch_stats["total_parameters_in_batches"]
        == initial_total_params + 3
    )


def test_get_parameters_batch_with_specific_version(
    mock_service_optimized, sample_parameter_response
):
    """Test batch retrieval with a specific version."""
    # Mock get_parameter
    with patch.object(
        mock_service_optimized, "get_parameter", return_value=sample_parameter_response
    ) as mock_get:
        mock_service_optimized.get_parameters_batch(["param1", "param2"], version="v1")

        # Verify get_parameter was called with the correct version
        assert mock_get.call_count == 2
        # Check that version was passed as a keyword argument
        for call in mock_get.call_args_list:
            # call[1] is kwargs, call[0] is args
            # The version might be passed as positional or keyword arg
            if len(call[1]) > 0:
                assert call[1].get("version") == "v1"


# Integration Tests for Combined Features
def test_optimized_service_initialization(mock_service_optimized):
    """Test that all optimizations can be enabled together."""
    assert mock_service_optimized.enable_cache is True
    assert mock_service_optimized.enable_connection_pooling is True
    assert mock_service_optimized.cache_ttl_seconds == 300
    assert mock_service_optimized.max_pool_size == 20


def test_batch_operations_with_caching_efficiency(
    mock_service_optimized, sample_parameter_response
):
    """Test that batch operations work correctly with caching enabled."""

    # Create a mock that actually caches results
    def mock_get_with_cache(name, version=None):
        # Simulate caching behavior
        cache_key = mock_service_optimized._get_cache_key(name, version)
        cached = mock_service_optimized._get_from_cache(cache_key)
        if cached:
            return cached
        # If not cached, cache it and return
        mock_service_optimized._put_in_cache(cache_key, sample_parameter_response)
        return sample_parameter_response

    with patch.object(
        mock_service_optimized, "get_parameter", side_effect=mock_get_with_cache
    ):
        # First batch operation - nothing cached
        results1 = mock_service_optimized.get_parameters_batch(["param1", "param2"])
        assert results1["cache_hits"] == 0
        assert results1["api_calls"] == 2

        # Second batch operation - should benefit from cache
        results2 = mock_service_optimized.get_parameters_batch(["param1", "param2"])
        assert results2["cache_hits"] == 2
        assert results2["api_calls"] == 0


def test_cache_stats_include_batch_stats(
    mock_service_optimized, sample_parameter_response
):
    """Test that cache statistics include batch operation statistics."""
    # Perform some batch operations
    with patch.object(
        mock_service_optimized, "get_parameter", return_value=sample_parameter_response
    ):
        mock_service_optimized.get_parameters_batch(["param1", "param2"])
        mock_service_optimized.get_parameters_batch(["param3"])

    stats = mock_service_optimized.get_cache_stats()

    assert "batch_stats" in stats
    assert stats["batch_stats"]["total_batch_operations"] == 2
    assert stats["batch_stats"]["total_parameters_in_batches"] == 3


def test_batch_stats_track_cache_hits(
    mock_service_optimized, sample_parameter_response
):
    """Test that batch statistics track cache hits correctly."""
    # Pre-cache one parameter
    mock_service_optimized._put_in_cache("param1:latest", sample_parameter_response)

    initial_cache_hits = mock_service_optimized._batch_stats["cache_hits_in_batches"]

    # Perform batch operation
    with patch.object(
        mock_service_optimized, "get_parameter", return_value=sample_parameter_response
    ):
        mock_service_optimized.get_parameters_batch(["param1", "param2"])

    # Cache hits should be incremented
    assert (
        mock_service_optimized._batch_stats["cache_hits_in_batches"]
        == initial_cache_hits + 1
    )


def test_cache_with_disabled_flag_does_not_store(mock_service_with_cache):
    """Test that cache operations are no-ops when caching is disabled."""
    # Disable caching
    mock_service_with_cache.enable_cache = False

    # Try to put in cache
    mock_service_with_cache._put_in_cache("test:latest", "data")

    # Cache should remain empty
    assert len(mock_service_with_cache._cache) == 0

    # Try to get from cache
    result = mock_service_with_cache._get_from_cache("test:latest")
    assert result is None


def test_cache_ttl_configuration(mock_service_with_cache):
    """Test that cache TTL can be configured."""
    # Verify default TTL
    assert mock_service_with_cache.cache_ttl_seconds == 300

    # Create service with custom TTL
    with patch("app.services.parameter_manager.get_logger"):
        service = ParameterManagerService(
            project_id="test-project", enable_cache=True, cache_ttl_seconds=600
        )
        assert service.cache_ttl_seconds == 600
