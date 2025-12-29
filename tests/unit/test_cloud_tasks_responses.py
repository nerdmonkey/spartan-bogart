from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.responses.cloud_tasks import (
    QueueCreateResponse,
    QueueListResponse,
    QueueResponse,
    TaskCreateResponse,
    TaskListResponse,
    TaskOperationResponse,
    TaskResponse,
)


def test_task_response_valid():
    """Test valid TaskResponse creation."""
    response = TaskResponse(
        task_name="test-task",
        queue_name="test-queue",
        payload={"message": "Hello World"},
        schedule_time=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
        created_time=datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc),
        http_method="POST",
        relative_uri="/process-task",
        headers={"Content-Type": "application/json"},
        dispatch_count=1,
        response_count=1,
        first_attempt_time=datetime(2024, 1, 1, 12, 5, 0, tzinfo=timezone.utc),
        last_attempt_time=datetime(2024, 1, 1, 12, 5, 0, tzinfo=timezone.utc),
    )

    assert response.task_name == "test-task"
    assert response.queue_name == "test-queue"
    assert response.payload == {"message": "Hello World"}
    assert response.http_method == "POST"
    assert response.relative_uri == "/process-task"
    assert response.headers == {"Content-Type": "application/json"}
    assert response.dispatch_count == 1
    assert response.response_count == 1


def test_task_response_minimal():
    """Test TaskResponse with minimal required fields."""
    response = TaskResponse(
        task_name="test-task",
        queue_name="test-queue",
        payload={"data": "test"},
        created_time=datetime.now(timezone.utc),
        http_method="GET",
        relative_uri="/test",
    )

    assert response.task_name == "test-task"
    assert response.queue_name == "test-queue"
    assert response.payload == {"data": "test"}
    assert response.schedule_time is None
    assert response.headers is None
    assert response.dispatch_count == 0  # Default value
    assert response.response_count == 0  # Default value
    assert response.first_attempt_time is None
    assert response.last_attempt_time is None


def test_task_response_empty_task_name():
    """Test TaskResponse with empty task name."""
    with pytest.raises(ValidationError, match="Task name is required"):
        TaskResponse(
            task_name="",
            queue_name="test-queue",
            payload={"data": "test"},
            created_time=datetime.now(timezone.utc),
            http_method="GET",
            relative_uri="/test",
        )


def test_task_response_whitespace_task_name():
    """Test TaskResponse with whitespace task name."""
    with pytest.raises(ValidationError, match="Task name is required"):
        TaskResponse(
            task_name="   ",
            queue_name="test-queue",
            payload={"data": "test"},
            created_time=datetime.now(timezone.utc),
            http_method="GET",
            relative_uri="/test",
        )


def test_task_create_response_valid():
    """Test valid TaskCreateResponse creation."""
    response = TaskCreateResponse(
        task_name="projects/test-project/locations/us-central1/queues/test-queue/tasks/test-task",
        queue_name="test-queue",
        schedule_time=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
        created_time=datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc),
        relative_uri="/process-task",
    )

    assert "test-task" in response.task_name
    assert response.queue_name == "test-queue"
    assert response.relative_uri == "/process-task"


def test_task_create_response_minimal():
    """Test TaskCreateResponse with minimal fields."""
    response = TaskCreateResponse(
        task_name="test-task",
        queue_name="test-queue",
        created_time=datetime.now(timezone.utc),
        relative_uri="/test",
    )

    assert response.task_name == "test-task"
    assert response.queue_name == "test-queue"
    assert response.schedule_time is None
    assert response.relative_uri == "/test"


def test_queue_response_valid():
    """Test valid QueueResponse creation."""
    response = QueueResponse(
        queue_name="test-queue",
        state="RUNNING",
        max_concurrent_dispatches=10,
        max_dispatches_per_second=5.0,
        max_retry_duration=300,
        max_attempts=3,
        purge_time=datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc),
        stats_approximate_tasks=25,
    )

    assert response.queue_name == "test-queue"
    assert response.state == "RUNNING"
    assert response.max_concurrent_dispatches == 10
    assert response.max_dispatches_per_second == 5.0
    assert response.max_retry_duration == 300
    assert response.max_attempts == 3
    assert response.stats_approximate_tasks == 25


def test_queue_response_minimal():
    """Test QueueResponse with minimal fields."""
    response = QueueResponse(queue_name="test-queue", state="PAUSED")

    assert response.queue_name == "test-queue"
    assert response.state == "PAUSED"
    assert response.max_concurrent_dispatches is None
    assert response.max_dispatches_per_second is None
    assert response.max_retry_duration is None
    assert response.max_attempts is None
    assert response.purge_time is None
    assert response.stats_approximate_tasks == 0  # Default value


def test_queue_create_response_valid():
    """Test valid QueueCreateResponse creation."""
    response = QueueCreateResponse(
        queue_name="test-queue",
        state="RUNNING",
        created_time=datetime.now(timezone.utc),
    )

    assert response.queue_name == "test-queue"
    assert response.state == "RUNNING"
    assert isinstance(response.created_time, datetime)


def test_task_list_response_valid():
    """Test valid TaskListResponse creation."""
    task1 = TaskResponse(
        task_name="task1",
        queue_name="test-queue",
        payload={"id": 1},
        created_time=datetime.now(timezone.utc),
        http_method="POST",
        relative_uri="/task1",
    )

    task2 = TaskResponse(
        task_name="task2",
        queue_name="test-queue",
        payload={"id": 2},
        created_time=datetime.now(timezone.utc),
        http_method="GET",
        relative_uri="/task2",
    )

    response = TaskListResponse(
        tasks=[task1, task2], next_page_token="next-token", total_size=100
    )

    assert len(response.tasks) == 2
    assert response.tasks[0].task_name == "task1"
    assert response.tasks[1].task_name == "task2"
    assert response.next_page_token == "next-token"
    assert response.total_size == 100


def test_task_list_response_empty():
    """Test TaskListResponse with empty task list."""
    response = TaskListResponse(tasks=[])

    assert len(response.tasks) == 0
    assert response.next_page_token is None
    assert response.total_size is None


def test_queue_list_response_valid():
    """Test valid QueueListResponse creation."""
    queue1 = QueueResponse(queue_name="queue1", state="RUNNING")
    queue2 = QueueResponse(queue_name="queue2", state="PAUSED")

    response = QueueListResponse(queues=[queue1, queue2], next_page_token="next-token")

    assert len(response.queues) == 2
    assert response.queues[0].queue_name == "queue1"
    assert response.queues[1].queue_name == "queue2"
    assert response.next_page_token == "next-token"


def test_queue_list_response_empty():
    """Test QueueListResponse with empty queue list."""
    response = QueueListResponse(queues=[])

    assert len(response.queues) == 0
    assert response.next_page_token is None


def test_task_operation_response_success():
    """Test TaskOperationResponse for successful operation."""
    response = TaskOperationResponse(
        success=True, message="Task deleted successfully", task_name="test-task"
    )

    assert response.success is True
    assert response.message == "Task deleted successfully"
    assert response.task_name == "test-task"


def test_task_operation_response_failure():
    """Test TaskOperationResponse for failed operation."""
    response = TaskOperationResponse(success=False, message="Operation failed")

    assert response.success is False
    assert response.message == "Operation failed"
    assert response.task_name is None


def test_task_operation_response_minimal():
    """Test TaskOperationResponse with minimal fields."""
    response = TaskOperationResponse(success=True, message="Success")

    assert response.success is True
    assert response.message == "Success"
    assert response.task_name is None
