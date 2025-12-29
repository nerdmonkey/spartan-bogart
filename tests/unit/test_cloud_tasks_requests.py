from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.requests.cloud_tasks import (
    QueueCreateRequest,
    TaskCreateRequest,
    TaskUpdateRequest,
)


def test_task_create_request_valid():
    """Test valid TaskCreateRequest creation."""
    request = TaskCreateRequest(
        queue_name="test-queue",
        task_name="test-task",
        payload={"message": "Hello World", "user_id": 123},
        schedule_time=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
        http_method="POST",
        relative_uri="/process-task",
        headers={"Authorization": "Bearer token"},
    )

    assert request.queue_name == "test-queue"
    assert request.task_name == "test-task"
    assert request.payload == {"message": "Hello World", "user_id": 123}
    assert request.http_method == "POST"
    assert request.relative_uri == "/process-task"
    assert request.headers == {"Authorization": "Bearer token"}


def test_task_create_request_minimal():
    """Test TaskCreateRequest with minimal required fields."""
    request = TaskCreateRequest(
        queue_name="test-queue", payload={"data": "test"}, relative_uri="/test"
    )

    assert request.queue_name == "test-queue"
    assert request.task_name is None
    assert request.payload == {"data": "test"}
    assert request.schedule_time is None
    assert request.http_method == "POST"  # Default value
    assert request.relative_uri == "/test"
    assert request.headers is None


def test_task_create_request_empty_queue_name():
    """Test TaskCreateRequest with empty queue name."""
    with pytest.raises(ValidationError, match="Queue name is required"):
        TaskCreateRequest(queue_name="", payload={"data": "test"}, relative_uri="/test")


def test_task_create_request_whitespace_queue_name():
    """Test TaskCreateRequest with whitespace queue name."""
    with pytest.raises(ValidationError, match="Queue name is required"):
        TaskCreateRequest(
            queue_name="   ", payload={"data": "test"}, relative_uri="/test"
        )


def test_task_create_request_long_queue_name():
    """Test TaskCreateRequest with queue name too long."""
    long_name = "a" * 101
    with pytest.raises(
        ValidationError, match="Queue name must be at most 100 characters long"
    ):
        TaskCreateRequest(
            queue_name=long_name, payload={"data": "test"}, relative_uri="/test"
        )


def test_task_create_request_invalid_http_method():
    """Test TaskCreateRequest with invalid HTTP method."""
    with pytest.raises(ValidationError, match="HTTP method must be one of"):
        TaskCreateRequest(
            queue_name="test-queue",
            payload={"data": "test"},
            relative_uri="/test",
            http_method="INVALID",
        )


def test_task_create_request_http_method_case_insensitive():
    """Test TaskCreateRequest HTTP method is case insensitive."""
    request = TaskCreateRequest(
        queue_name="test-queue",
        payload={"data": "test"},
        relative_uri="/test",
        http_method="get",
    )

    assert request.http_method == "GET"


def test_task_create_request_empty_relative_uri():
    """Test TaskCreateRequest with empty relative URI."""
    with pytest.raises(ValidationError, match="Relative URI is required"):
        TaskCreateRequest(
            queue_name="test-queue", payload={"data": "test"}, relative_uri=""
        )


def test_task_create_request_relative_uri_without_slash():
    """Test TaskCreateRequest adds leading slash to relative URI."""
    request = TaskCreateRequest(
        queue_name="test-queue", payload={"data": "test"}, relative_uri="test-endpoint"
    )

    assert request.relative_uri == "/test-endpoint"


def test_task_create_request_empty_task_name():
    """Test TaskCreateRequest with empty task name becomes None."""
    request = TaskCreateRequest(
        queue_name="test-queue",
        payload={"data": "test"},
        relative_uri="/test",
        task_name="",
    )

    assert request.task_name is None


def test_task_create_request_whitespace_task_name():
    """Test TaskCreateRequest with whitespace task name becomes None."""
    request = TaskCreateRequest(
        queue_name="test-queue",
        payload={"data": "test"},
        relative_uri="/test",
        task_name="   ",
    )

    assert request.task_name is None


def test_task_create_request_long_task_name():
    """Test TaskCreateRequest with task name too long."""
    long_name = "a" * 501
    with pytest.raises(
        ValidationError, match="Task name must be at most 500 characters long"
    ):
        TaskCreateRequest(
            queue_name="test-queue",
            payload={"data": "test"},
            relative_uri="/test",
            task_name=long_name,
        )


def test_task_update_request_valid():
    """Test valid TaskUpdateRequest creation."""
    request = TaskUpdateRequest(
        schedule_time=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
        payload={"updated": "data"},
        headers={"New-Header": "value"},
    )

    assert request.schedule_time is not None
    assert request.payload == {"updated": "data"}
    assert request.headers == {"New-Header": "value"}


def test_task_update_request_empty():
    """Test TaskUpdateRequest with no fields."""
    request = TaskUpdateRequest()

    assert request.schedule_time is None
    assert request.payload is None
    assert request.headers is None


def test_queue_create_request_valid():
    """Test valid QueueCreateRequest creation."""
    request = QueueCreateRequest(
        queue_name="test-queue",
        max_concurrent_dispatches=10,
        max_dispatches_per_second=5.0,
        max_retry_duration=300,
        max_attempts=3,
    )

    assert request.queue_name == "test-queue"
    assert request.max_concurrent_dispatches == 10
    assert request.max_dispatches_per_second == 5.0
    assert request.max_retry_duration == 300
    assert request.max_attempts == 3


def test_queue_create_request_minimal():
    """Test QueueCreateRequest with minimal required fields."""
    request = QueueCreateRequest(queue_name="test-queue")

    assert request.queue_name == "test-queue"
    assert request.max_concurrent_dispatches is None
    assert request.max_dispatches_per_second is None
    assert request.max_retry_duration is None
    assert request.max_attempts is None


def test_queue_create_request_empty_queue_name():
    """Test QueueCreateRequest with empty queue name."""
    with pytest.raises(ValidationError, match="Queue name is required"):
        QueueCreateRequest(queue_name="")


def test_queue_create_request_whitespace_queue_name():
    """Test QueueCreateRequest with whitespace queue name."""
    with pytest.raises(ValidationError, match="Queue name is required"):
        QueueCreateRequest(queue_name="   ")


def test_queue_create_request_long_queue_name():
    """Test QueueCreateRequest with queue name too long."""
    long_name = "a" * 101
    with pytest.raises(
        ValidationError, match="Queue name must be at most 100 characters long"
    ):
        QueueCreateRequest(queue_name=long_name)


def test_queue_create_request_negative_max_concurrent_dispatches():
    """Test QueueCreateRequest with negative max concurrent dispatches."""
    with pytest.raises(
        ValidationError, match="Max concurrent dispatches must be positive"
    ):
        QueueCreateRequest(queue_name="test-queue", max_concurrent_dispatches=-1)


def test_queue_create_request_zero_max_concurrent_dispatches():
    """Test QueueCreateRequest with zero max concurrent dispatches."""
    with pytest.raises(
        ValidationError, match="Max concurrent dispatches must be positive"
    ):
        QueueCreateRequest(queue_name="test-queue", max_concurrent_dispatches=0)


def test_queue_create_request_negative_max_dispatches_per_second():
    """Test QueueCreateRequest with negative max dispatches per second."""
    with pytest.raises(
        ValidationError, match="Max dispatches per second must be positive"
    ):
        QueueCreateRequest(queue_name="test-queue", max_dispatches_per_second=-1.0)


def test_queue_create_request_zero_max_dispatches_per_second():
    """Test QueueCreateRequest with zero max dispatches per second."""
    with pytest.raises(
        ValidationError, match="Max dispatches per second must be positive"
    ):
        QueueCreateRequest(queue_name="test-queue", max_dispatches_per_second=0.0)


def test_queue_create_request_negative_max_retry_duration():
    """Test QueueCreateRequest with negative max retry duration."""
    with pytest.raises(ValidationError, match="Max retry duration must be positive"):
        QueueCreateRequest(queue_name="test-queue", max_retry_duration=-1)


def test_queue_create_request_zero_max_retry_duration():
    """Test QueueCreateRequest with zero max retry duration."""
    with pytest.raises(ValidationError, match="Max retry duration must be positive"):
        QueueCreateRequest(queue_name="test-queue", max_retry_duration=0)


def test_queue_create_request_negative_max_attempts():
    """Test QueueCreateRequest with negative max attempts."""
    with pytest.raises(ValidationError, match="Max attempts must be positive"):
        QueueCreateRequest(queue_name="test-queue", max_attempts=-1)


def test_queue_create_request_zero_max_attempts():
    """Test QueueCreateRequest with zero max attempts."""
    with pytest.raises(ValidationError, match="Max attempts must be positive"):
        QueueCreateRequest(queue_name="test-queue", max_attempts=0)
