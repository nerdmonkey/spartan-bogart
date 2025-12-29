from datetime import datetime, timezone
from unittest.mock import Mock, patch

import pytest
from google.cloud import tasks_v2

from app.exceptions.cloud_tasks import (
    CloudTasksException,
    InvalidTaskPayloadException,
    QueueNotFoundException,
    TaskCreationException,
    TaskNotFoundException,
)
from app.requests.cloud_tasks import QueueCreateRequest, TaskCreateRequest
from app.services.cloud_tasks import CloudTasksService


@pytest.fixture
def mock_cloud_tasks_client():
    """Mock the Google Cloud Tasks client."""
    with patch(
        "app.services.cloud_tasks.tasks_v2.CloudTasksClient"
    ) as mock_client_class:
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        yield mock_client


@pytest.fixture
def mock_env():
    """Mock environment variables."""
    with patch("app.services.cloud_tasks.env") as mock_env_func:
        mock_env_func.side_effect = lambda key, default=None: {
            "GCP_PROJECT_ID": "test-project",
            "GCP_LOCATION": "us-central1",
            "CLOUD_TASKS_BASE_URL": "https://test-function.cloudfunctions.net",
            "SERVICE_NAME": "test-service",
        }.get(key, default)
        yield mock_env_func


@pytest.fixture
def cloud_tasks_service(mock_cloud_tasks_client, mock_env):
    """Create a CloudTasksService instance with mocked dependencies."""
    return CloudTasksService()


@pytest.fixture
def sample_task_request():
    """Create a sample task request."""
    return TaskCreateRequest(
        queue_name="test-queue",
        task_name="test-task",
        payload={"message": "Hello World", "user_id": 123},
        http_method="POST",
        relative_uri="/process-task",
        headers={"Authorization": "Bearer token"},
    )


@pytest.fixture
def sample_queue_request():
    """Create a sample queue request."""
    return QueueCreateRequest(
        queue_name="test-queue",
        max_concurrent_dispatches=10,
        max_dispatches_per_second=5.0,
        max_retry_duration=300,
        max_attempts=3,
    )


def test_cloud_tasks_service_initialization(mock_cloud_tasks_client, mock_env):
    """Test CloudTasksService initialization."""
    service = CloudTasksService()

    assert service.project_id == "test-project"
    assert service.location == "us-central1"
    assert service.parent == "projects/test-project/locations/us-central1"
    assert service.client is not None


def test_cloud_tasks_service_initialization_with_params(mock_cloud_tasks_client):
    """Test CloudTasksService initialization with custom parameters."""
    service = CloudTasksService(project_id="custom-project", location="europe-west1")

    assert service.project_id == "custom-project"
    assert service.location == "europe-west1"
    assert service.parent == "projects/custom-project/locations/europe-west1"


def test_cloud_tasks_service_initialization_missing_project_id():
    """Test CloudTasksService initialization fails without project ID."""
    with patch("app.services.cloud_tasks.env") as mock_env_func:
        mock_env_func.return_value = None

        with pytest.raises(CloudTasksException, match="GCP_PROJECT_ID is required"):
            CloudTasksService()


def test_create_task_success(cloud_tasks_service, sample_task_request):
    """Test successful task creation."""
    # Mock the response
    mock_response = Mock()
    mock_response.name = (
        "projects/test-project/locations/us-central1/queues/test-queue/tasks/test-task"
    )
    mock_response.schedule_time = None

    cloud_tasks_service.client.create_task.return_value = mock_response

    response = cloud_tasks_service.create_task(sample_task_request)

    assert response.task_name == mock_response.name
    assert response.queue_name == "test-queue"
    assert response.relative_uri == "/process-task"
    assert isinstance(response.created_time, datetime)

    # Verify the client was called correctly
    cloud_tasks_service.client.create_task.assert_called_once()
    call_args = cloud_tasks_service.client.create_task.call_args

    assert (
        call_args[1]["parent"]
        == "projects/test-project/locations/us-central1/queues/test-queue"
    )
    assert "task" in call_args[1]

    task = call_args[1]["task"]
    assert "http_request" in task
    assert task["http_request"]["http_method"] == tasks_v2.HttpMethod.POST
    assert (
        task["http_request"]["url"]
        == "https://test-function.cloudfunctions.net/process-task"
    )


def test_create_task_with_schedule_time(cloud_tasks_service, sample_task_request):
    """Test task creation with schedule time."""
    schedule_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    sample_task_request.schedule_time = schedule_time

    mock_response = Mock()
    mock_response.name = (
        "projects/test-project/locations/us-central1/queues/test-queue/tasks/test-task"
    )

    # Mock schedule_time on response
    mock_timestamp = Mock()
    mock_timestamp.ToDatetime.return_value = schedule_time
    mock_response.schedule_time = mock_timestamp

    cloud_tasks_service.client.create_task.return_value = mock_response

    response = cloud_tasks_service.create_task(sample_task_request)

    assert response.schedule_time == schedule_time

    # Verify schedule_time was set in the task
    call_args = cloud_tasks_service.client.create_task.call_args
    task = call_args[1]["task"]
    assert "schedule_time" in task


def test_create_task_invalid_payload(cloud_tasks_service):
    """Test task creation with invalid payload."""
    # Test with string payload (should fail validation at request level)
    with pytest.raises(ValueError, match="Input should be a valid dictionary"):
        TaskCreateRequest(
            queue_name="test-queue",
            payload="invalid-payload",  # Should be dict
            relative_uri="/test",
        )


def test_create_task_queue_not_found(cloud_tasks_service, sample_task_request):
    """Test task creation when queue doesn't exist."""
    cloud_tasks_service.client.create_task.side_effect = Exception(
        "NOT_FOUND: Queue not found"
    )

    with pytest.raises(QueueNotFoundException, match="Queue 'test-queue' not found"):
        cloud_tasks_service.create_task(sample_task_request)


def test_create_task_invalid_argument(cloud_tasks_service, sample_task_request):
    """Test task creation with invalid arguments."""
    cloud_tasks_service.client.create_task.side_effect = Exception(
        "INVALID_ARGUMENT: Invalid task"
    )

    with pytest.raises(InvalidTaskPayloadException, match="Invalid task configuration"):
        cloud_tasks_service.create_task(sample_task_request)


def test_create_task_general_error(cloud_tasks_service, sample_task_request):
    """Test task creation with general error."""
    cloud_tasks_service.client.create_task.side_effect = Exception("Some other error")

    with pytest.raises(TaskCreationException, match="Failed to create task"):
        cloud_tasks_service.create_task(sample_task_request)


def test_get_task_success(cloud_tasks_service):
    """Test successful task retrieval."""
    mock_task = Mock()
    mock_task.name = (
        "projects/test-project/locations/us-central1/queues/test-queue/tasks/test-task"
    )
    mock_task.http_request.body = b'{"message": "test"}'
    mock_task.http_request.http_method.name = "POST"
    mock_task.http_request.url = "https://example.com/test"
    mock_task.http_request.headers = {"Content-Type": "application/json"}
    mock_task.schedule_time = None
    mock_task.create_time = None
    mock_task.dispatch_count = 0
    mock_task.response_count = 0
    mock_task.first_attempt = None
    mock_task.last_attempt = None

    cloud_tasks_service.client.get_task.return_value = mock_task

    response = cloud_tasks_service.get_task("test-queue", "test-task")

    assert response.task_name == "test-task"
    assert response.queue_name == "test-queue"
    assert response.payload == {"message": "test"}
    assert response.http_method == "POST"

    cloud_tasks_service.client.get_task.assert_called_once_with(
        name="projects/test-project/locations/us-central1/queues/test-queue/tasks/test-task"
    )


def test_get_task_not_found(cloud_tasks_service):
    """Test task retrieval when task doesn't exist."""
    cloud_tasks_service.client.get_task.side_effect = Exception(
        "NOT_FOUND: Task not found"
    )

    with pytest.raises(
        TaskNotFoundException, match="Task 'test-task' not found in queue 'test-queue'"
    ):
        cloud_tasks_service.get_task("test-queue", "test-task")


def test_list_tasks_success(cloud_tasks_service):
    """Test successful task listing."""
    mock_task1 = Mock()
    mock_task1.name = (
        "projects/test-project/locations/us-central1/queues/test-queue/tasks/task1"
    )
    mock_task1.http_request.body = b'{"id": 1}'
    mock_task1.http_request.http_method.name = "POST"
    mock_task1.http_request.url = "https://example.com/task1"
    mock_task1.http_request.headers = {}
    mock_task1.schedule_time = None
    mock_task1.create_time = None
    mock_task1.dispatch_count = 0
    mock_task1.response_count = 0
    mock_task1.first_attempt = None
    mock_task1.last_attempt = None

    mock_task2 = Mock()
    mock_task2.name = (
        "projects/test-project/locations/us-central1/queues/test-queue/tasks/task2"
    )
    mock_task2.http_request.body = b'{"id": 2}'
    mock_task2.http_request.http_method.name = "GET"
    mock_task2.http_request.url = "https://example.com/task2"
    mock_task2.http_request.headers = {}
    mock_task2.schedule_time = None
    mock_task2.create_time = None
    mock_task2.dispatch_count = 1
    mock_task2.response_count = 1
    mock_task2.first_attempt = None
    mock_task2.last_attempt = None

    mock_response = Mock()
    mock_response.tasks = [mock_task1, mock_task2]
    mock_response.next_page_token = "next-token"

    cloud_tasks_service.client.list_tasks.return_value = mock_response

    response = cloud_tasks_service.list_tasks("test-queue", page_size=50)

    assert len(response.tasks) == 2
    assert response.tasks[0].task_name == "task1"
    assert response.tasks[1].task_name == "task2"
    assert response.next_page_token == "next-token"

    cloud_tasks_service.client.list_tasks.assert_called_once_with(
        parent="projects/test-project/locations/us-central1/queues/test-queue",
        page_size=50,
    )


def test_delete_task_success(cloud_tasks_service):
    """Test successful task deletion."""
    response = cloud_tasks_service.delete_task("test-queue", "test-task")

    assert response.success is True
    assert "deleted successfully" in response.message
    assert response.task_name == "test-task"

    cloud_tasks_service.client.delete_task.assert_called_once_with(
        name="projects/test-project/locations/us-central1/queues/test-queue/tasks/test-task"
    )


def test_delete_task_not_found(cloud_tasks_service):
    """Test task deletion when task doesn't exist."""
    cloud_tasks_service.client.delete_task.side_effect = Exception(
        "NOT_FOUND: Task not found"
    )

    with pytest.raises(
        TaskNotFoundException, match="Task 'test-task' not found in queue 'test-queue'"
    ):
        cloud_tasks_service.delete_task("test-queue", "test-task")


def test_run_task_success(cloud_tasks_service):
    """Test successful task execution."""
    response = cloud_tasks_service.run_task("test-queue", "test-task")

    assert response.success is True
    assert "executed successfully" in response.message
    assert response.task_name == "test-task"

    cloud_tasks_service.client.run_task.assert_called_once_with(
        name="projects/test-project/locations/us-central1/queues/test-queue/tasks/test-task"
    )


def test_create_queue_success(cloud_tasks_service, sample_queue_request):
    """Test successful queue creation."""
    mock_response = Mock()
    mock_response.name = "projects/test-project/locations/us-central1/queues/test-queue"

    cloud_tasks_service.client.create_queue.return_value = mock_response

    response = cloud_tasks_service.create_queue(sample_queue_request)

    assert response.queue_name == "test-queue"
    assert response.state == "RUNNING"
    assert isinstance(response.created_time, datetime)

    # Verify the client was called correctly
    cloud_tasks_service.client.create_queue.assert_called_once()
    call_args = cloud_tasks_service.client.create_queue.call_args

    assert call_args[1]["parent"] == "projects/test-project/locations/us-central1"

    queue = call_args[1]["queue"]
    assert (
        queue["name"] == "projects/test-project/locations/us-central1/queues/test-queue"
    )
    assert "rate_limits" in queue
    assert "retry_config" in queue


def test_get_queue_success(cloud_tasks_service):
    """Test successful queue retrieval."""
    mock_queue = Mock()
    mock_queue.name = "projects/test-project/locations/us-central1/queues/test-queue"
    mock_queue.state.name = "RUNNING"
    mock_queue.rate_limits = None
    mock_queue.retry_config = None
    mock_queue.purge_time = None
    mock_queue.stats = None

    cloud_tasks_service.client.get_queue.return_value = mock_queue

    response = cloud_tasks_service.get_queue("test-queue")

    assert response.queue_name == "test-queue"
    assert response.state == "RUNNING"

    cloud_tasks_service.client.get_queue.assert_called_once_with(
        name="projects/test-project/locations/us-central1/queues/test-queue"
    )


def test_get_queue_not_found(cloud_tasks_service):
    """Test queue retrieval when queue doesn't exist."""
    cloud_tasks_service.client.get_queue.side_effect = Exception(
        "NOT_FOUND: Queue not found"
    )

    with pytest.raises(QueueNotFoundException, match="Queue 'test-queue' not found"):
        cloud_tasks_service.get_queue("test-queue")


def test_list_queues_success(cloud_tasks_service):
    """Test successful queue listing."""
    mock_queue1 = Mock()
    mock_queue1.name = "projects/test-project/locations/us-central1/queues/queue1"
    mock_queue1.state.name = "RUNNING"
    mock_queue1.rate_limits = None
    mock_queue1.retry_config = None
    mock_queue1.purge_time = None
    mock_queue1.stats = None

    mock_queue2 = Mock()
    mock_queue2.name = "projects/test-project/locations/us-central1/queues/queue2"
    mock_queue2.state.name = "PAUSED"
    mock_queue2.rate_limits = None
    mock_queue2.retry_config = None
    mock_queue2.purge_time = None
    mock_queue2.stats = None

    mock_response = Mock()
    mock_response.queues = [mock_queue1, mock_queue2]
    mock_response.next_page_token = None

    cloud_tasks_service.client.list_queues.return_value = mock_response

    response = cloud_tasks_service.list_queues()

    assert len(response.queues) == 2
    assert response.queues[0].queue_name == "queue1"
    assert response.queues[0].state == "RUNNING"
    assert response.queues[1].queue_name == "queue2"
    assert response.queues[1].state == "PAUSED"
    assert response.next_page_token is None


def test_delete_queue_success(cloud_tasks_service):
    """Test successful queue deletion."""
    response = cloud_tasks_service.delete_queue("test-queue")

    assert response.success is True
    assert "deleted successfully" in response.message

    cloud_tasks_service.client.delete_queue.assert_called_once_with(
        name="projects/test-project/locations/us-central1/queues/test-queue"
    )


def test_purge_queue_success(cloud_tasks_service):
    """Test successful queue purging."""
    response = cloud_tasks_service.purge_queue("test-queue")

    assert response.success is True
    assert "purged successfully" in response.message

    cloud_tasks_service.client.purge_queue.assert_called_once_with(
        name="projects/test-project/locations/us-central1/queues/test-queue"
    )


def test_construct_task_url_with_base_url(cloud_tasks_service):
    """Test URL construction with base URL."""
    url = cloud_tasks_service._construct_task_url("/test-endpoint")

    assert url == "https://test-function.cloudfunctions.net/test-endpoint"


def test_construct_task_url_without_base_url():
    """Test URL construction without base URL."""
    with patch("app.services.cloud_tasks.env") as mock_env_func:
        mock_env_func.side_effect = lambda key, default=None: {
            "GCP_PROJECT_ID": "test-project",
            "GCP_LOCATION": "us-central1",
            "SERVICE_NAME": "test-service",
        }.get(key, default)

        with patch("app.services.cloud_tasks.tasks_v2.CloudTasksClient"):
            service = CloudTasksService()
            url = service._construct_task_url("/test-endpoint")

            expected = "https://us-central1-test-project.cloudfunctions.net/test-service/test-endpoint"
            assert url == expected


def test_convert_task_to_response_with_minimal_data(cloud_tasks_service):
    """Test task conversion with minimal data."""
    mock_task = Mock()
    mock_task.name = (
        "projects/test-project/locations/us-central1/queues/test-queue/tasks/test-task"
    )
    mock_task.http_request.body = b'{"test": "data"}'
    mock_task.http_request.http_method.name = "POST"
    mock_task.http_request.url = "https://example.com/test"
    mock_task.http_request.headers = {}
    mock_task.schedule_time = None
    mock_task.create_time = None
    mock_task.dispatch_count = 0
    mock_task.response_count = 0
    mock_task.first_attempt = None
    mock_task.last_attempt = None

    response = cloud_tasks_service._convert_task_to_response(mock_task, "test-queue")

    assert response.task_name == "test-task"
    assert response.queue_name == "test-queue"
    assert response.payload == {"test": "data"}
    assert response.http_method == "POST"
    assert response.relative_uri == "/test"
    assert response.dispatch_count == 0
    assert response.response_count == 0


def test_convert_queue_to_response_with_minimal_data(cloud_tasks_service):
    """Test queue conversion with minimal data."""
    mock_queue = Mock()
    mock_queue.name = "projects/test-project/locations/us-central1/queues/test-queue"
    mock_queue.state.name = "RUNNING"
    mock_queue.rate_limits = None
    mock_queue.retry_config = None
    mock_queue.purge_time = None
    mock_queue.stats = None

    response = cloud_tasks_service._convert_queue_to_response(mock_queue)

    assert response.queue_name == "test-queue"
    assert response.state == "RUNNING"
    assert response.max_concurrent_dispatches is None
    assert response.max_dispatches_per_second is None
    assert response.max_retry_duration is None
    assert response.max_attempts is None
    assert response.purge_time is None
    assert response.stats_approximate_tasks == 0
