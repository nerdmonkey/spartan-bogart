"""Minimal tests to improve parameter manager service coverage."""

import pytest

from app.exceptions.parameter_manager import (
    ParameterManagerException,
    ParameterNotFoundException,
)
from app.services.parameter_manager import ParameterManagerService


def test_init_no_project_id(monkeypatch):
    """Test initialization fails without project ID."""
    monkeypatch.setattr("os.environ", {})
    monkeypatch.setattr("app.services.parameter_manager.env", lambda x: None)
    with pytest.raises(ParameterManagerException):
        ParameterManagerService()


def test_init_with_cache():
    """Test initialization with caching enabled."""
    service = ParameterManagerService(project_id="test", enable_cache=True)
    assert service.enable_cache is True


def test_clear_cache_disabled():
    """Test clear cache when caching is disabled."""
    service = ParameterManagerService(project_id="test", enable_cache=False)
    service.clear_cache()  # Should not raise


def test_get_cache_stats_disabled():
    """Test cache stats when disabled."""
    service = ParameterManagerService(project_id="test", enable_cache=False)
    stats = service.get_cache_stats()
    assert stats["enabled"] is False


def test_parameter_exists_false(monkeypatch):
    """Test parameter_exists returns False."""
    service = ParameterManagerService(project_id="test")
    monkeypatch.setattr(
        service,
        "get_parameter_metadata",
        lambda x: (_ for _ in ()).throw(ParameterNotFoundException("Not found")),
    )
    assert service.parameter_exists("nonexistent") is False


def test_parameter_exists_reraise(monkeypatch):
    """Test parameter_exists re-raises non-ParameterNotFoundException."""
    service = ParameterManagerService(project_id="test")
    monkeypatch.setattr(
        service,
        "get_parameter_metadata",
        lambda x: (_ for _ in ()).throw(Exception("Other error")),
    )
    with pytest.raises(Exception):
        service.parameter_exists("test")


def test_cache_operations():
    """Test cache operations."""
    service = ParameterManagerService(
        project_id="test", enable_cache=True, cache_ttl_seconds=1
    )

    # Test cache miss
    result = service._get_from_cache("test:latest")
    assert result is None

    # Test cache put and hit
    service._put_in_cache("test:latest", "value")
    result = service._get_from_cache("test:latest")
    assert result == "value"

    # Test cache invalidation
    service._invalidate_cache("test", "latest")
    result = service._get_from_cache("test:latest")
    assert result is None


def test_path_methods():
    """Test path generation methods."""
    service = ParameterManagerService(project_id="test-project", location="us-central1")

    assert service._get_parent_path() == "projects/test-project/locations/us-central1"
    assert (
        service._get_parameter_path("param")
        == "projects/test-project/locations/us-central1/parameters/param"
    )
    assert (
        service._get_parameter_version_path("param", "v1")
        == "projects/test-project/locations/us-central1/parameters/param/versions/v1"
    )


def test_cache_key_generation():
    """Test cache key generation."""
    service = ParameterManagerService(project_id="test")

    assert service._get_cache_key("param") == "param:latest"
    assert service._get_cache_key("param", "v1") == "param:v1"
