import json
from datetime import datetime, timezone
from typing import Optional

from google.cloud import tasks_v2
from google.protobuf import timestamp_pb2

from app.exceptions.cloud_tasks import (
    CloudTasksException,
    InvalidTaskPayloadException,
    QueueNotFoundException,
    TaskCreationException,
    TaskNotFoundException,
)
from app.helpers.environment import env
from app.helpers.logger import get_logger
from app.requests.cloud_tasks import QueueCreateRequest, TaskCreateRequest
from app.responses.cloud_tasks import (
    QueueCreateResponse,
    QueueListResponse,
    QueueResponse,
    TaskCreateResponse,
    TaskListResponse,
    TaskOperationResponse,
    TaskResponse,
)


class CloudTasksService:
    """
    Service class for managing Google Cloud Tasks operations.

    This service provides methods to create, manage, and monitor Cloud Tasks
    and queues following the Spartan Framework patterns.
    """

    def __init__(
        self, project_id: Optional[str] = None, location: Optional[str] = None
    ):
        """
        Initialize the CloudTasksService.

        Args:
            project_id (Optional[str]): GCP project ID. If not provided,
                uses environment variable.
            location (Optional[str]): GCP location/region. If not provided,
                uses environment variable.
        """
        self.logger = get_logger("spartan.cloud_tasks.service")
        self.project_id = project_id or env("GCP_PROJECT_ID")
        self.location = location or env("GCP_LOCATION", "us-central1")

        if not self.project_id:
            raise CloudTasksException("GCP_PROJECT_ID is required")

        try:
            self.client = tasks_v2.CloudTasksClient()
            self.parent = f"projects/{self.project_id}/locations/{self.location}"

            self.logger.info(
                "CloudTasksService initialized",
                extra={"project_id": self.project_id, "location": self.location},
            )
        except Exception as e:
            self.logger.error(
                "Failed to initialize Cloud Tasks client",
                extra={
                    "error": str(e),
                    "project_id": self.project_id,
                    "location": self.location,
                },
            )
            raise CloudTasksException(
                f"Failed to initialize Cloud Tasks client: {str(e)}"
            )

    def create_task(self, task_request: TaskCreateRequest) -> TaskCreateResponse:
        """
        Create a new Cloud Task.

        Args:
            task_request (TaskCreateRequest): The task creation request.

        Returns:
            TaskCreateResponse: The response data of the created task.

        Raises:
            TaskCreationException: If task creation fails.
            InvalidTaskPayloadException: If the task payload is invalid.
        """
        try:
            # Validate payload
            if not isinstance(task_request.payload, dict):
                raise InvalidTaskPayloadException("Task payload must be a dictionary")

            # Construct the queue path
            queue_path = f"{self.parent}/queues/{task_request.queue_name}"

            # Create the task
            task = {
                "http_request": {
                    "http_method": getattr(
                        tasks_v2.HttpMethod, task_request.http_method
                    ),
                    "url": self._construct_task_url(task_request.relative_uri),
                    "body": json.dumps(task_request.payload).encode(),
                    "headers": {
                        "Content-Type": "application/json",
                        **(task_request.headers or {}),
                    },
                }
            }

            # Add task name if provided
            if task_request.task_name:
                task["name"] = f"{queue_path}/tasks/{task_request.task_name}"

            # Add schedule time if provided
            if task_request.schedule_time:
                timestamp = timestamp_pb2.Timestamp()
                timestamp.FromDatetime(
                    task_request.schedule_time.replace(tzinfo=timezone.utc)
                )
                task["schedule_time"] = timestamp

            # Create the task
            response = self.client.create_task(parent=queue_path, task=task)

            created_time = datetime.now(timezone.utc)
            schedule_time = None

            if hasattr(response, "schedule_time") and response.schedule_time:
                schedule_time = response.schedule_time.ToDatetime()

            self.logger.info(
                "Task created successfully",
                extra={
                    "task_name": response.name,
                    "queue_name": task_request.queue_name,
                    "relative_uri": task_request.relative_uri,
                },
            )

            return TaskCreateResponse(
                task_name=response.name,
                queue_name=task_request.queue_name,
                schedule_time=schedule_time,
                created_time=created_time,
                relative_uri=task_request.relative_uri,
            )

        except Exception as e:
            self.logger.error(
                "Failed to create task",
                extra={
                    "error": str(e),
                    "queue_name": task_request.queue_name,
                    "relative_uri": task_request.relative_uri,
                },
            )

            if "NOT_FOUND" in str(e):
                raise QueueNotFoundException(
                    f"Queue '{task_request.queue_name}' not found"
                )
            elif "INVALID_ARGUMENT" in str(e):
                raise InvalidTaskPayloadException(
                    f"Invalid task configuration: {str(e)}"
                )
            else:
                raise TaskCreationException(f"Failed to create task: {str(e)}")

    def get_task(self, queue_name: str, task_name: str) -> TaskResponse:
        """
        Retrieve a task by its name.

        Args:
            queue_name (str): The name of the queue.
            task_name (str): The name of the task.

        Returns:
            TaskResponse: The task information.

        Raises:
            TaskNotFoundException: If the task is not found.
        """
        try:
            task_path = f"{self.parent}/queues/{queue_name}/tasks/{task_name}"
            task = self.client.get_task(name=task_path)

            return self._convert_task_to_response(task, queue_name)

        except Exception as e:
            self.logger.error(
                "Failed to get task",
                extra={
                    "error": str(e),
                    "queue_name": queue_name,
                    "task_name": task_name,
                },
            )

            if "NOT_FOUND" in str(e):
                raise TaskNotFoundException(
                    f"Task '{task_name}' not found in queue '{queue_name}'"
                )
            else:
                raise CloudTasksException(f"Failed to get task: {str(e)}")

    def list_tasks(
        self, queue_name: str, page_size: int = 100, page_token: Optional[str] = None
    ) -> TaskListResponse:
        """
        List tasks in a queue.

        Args:
            queue_name (str): The name of the queue.
            page_size (int): Maximum number of tasks to return.
            page_token (Optional[str]): Token for pagination.

        Returns:
            TaskListResponse: List of tasks with pagination info.

        Raises:
            QueueNotFoundException: If the queue is not found.
        """
        try:
            queue_path = f"{self.parent}/queues/{queue_name}"

            request = {"parent": queue_path, "page_size": page_size}

            if page_token:
                request["page_token"] = page_token

            response = self.client.list_tasks(**request)

            tasks = [
                self._convert_task_to_response(task, queue_name)
                for task in response.tasks
            ]

            return TaskListResponse(
                tasks=tasks,
                next_page_token=(
                    response.next_page_token if response.next_page_token else None
                ),
            )

        except Exception as e:
            self.logger.error(
                "Failed to list tasks",
                extra={"error": str(e), "queue_name": queue_name},
            )

            if "NOT_FOUND" in str(e):
                raise QueueNotFoundException(f"Queue '{queue_name}' not found")
            else:
                raise CloudTasksException(f"Failed to list tasks: {str(e)}")

    def delete_task(self, queue_name: str, task_name: str) -> TaskOperationResponse:
        """
        Delete a task.

        Args:
            queue_name (str): The name of the queue.
            task_name (str): The name of the task.

        Returns:
            TaskOperationResponse: Operation result.

        Raises:
            TaskNotFoundException: If the task is not found.
        """
        try:
            task_path = f"{self.parent}/queues/{queue_name}/tasks/{task_name}"
            self.client.delete_task(name=task_path)

            self.logger.info(
                "Task deleted successfully",
                extra={"task_name": task_name, "queue_name": queue_name},
            )

            return TaskOperationResponse(
                success=True,
                message=f"Task '{task_name}' deleted successfully",
                task_name=task_name,
            )

        except Exception as e:
            self.logger.error(
                "Failed to delete task",
                extra={
                    "error": str(e),
                    "queue_name": queue_name,
                    "task_name": task_name,
                },
            )

            if "NOT_FOUND" in str(e):
                raise TaskNotFoundException(
                    f"Task '{task_name}' not found in queue '{queue_name}'"
                )
            else:
                raise CloudTasksException(f"Failed to delete task: {str(e)}")

    def run_task(self, queue_name: str, task_name: str) -> TaskOperationResponse:
        """
        Force run a task immediately.

        Args:
            queue_name (str): The name of the queue.
            task_name (str): The name of the task.

        Returns:
            TaskOperationResponse: Operation result.

        Raises:
            TaskNotFoundException: If the task is not found.
        """
        try:
            task_path = f"{self.parent}/queues/{queue_name}/tasks/{task_name}"
            self.client.run_task(name=task_path)

            self.logger.info(
                "Task executed successfully",
                extra={"task_name": task_name, "queue_name": queue_name},
            )

            return TaskOperationResponse(
                success=True,
                message=f"Task '{task_name}' executed successfully",
                task_name=task_name,
            )

        except Exception as e:
            self.logger.error(
                "Failed to run task",
                extra={
                    "error": str(e),
                    "queue_name": queue_name,
                    "task_name": task_name,
                },
            )

            if "NOT_FOUND" in str(e):
                raise TaskNotFoundException(
                    f"Task '{task_name}' not found in queue '{queue_name}'"
                )
            else:
                raise CloudTasksException(f"Failed to run task: {str(e)}")

    def create_queue(self, queue_request: QueueCreateRequest) -> QueueCreateResponse:
        """
        Create a new Cloud Tasks queue.

        Args:
            queue_request (QueueCreateRequest): The queue creation request.

        Returns:
            QueueCreateResponse: The response data of the created queue.

        Raises:
            CloudTasksException: If queue creation fails.
        """
        try:
            queue = {"name": f"{self.parent}/queues/{queue_request.queue_name}"}

            # Add rate limits if provided
            if any(
                [
                    queue_request.max_concurrent_dispatches,
                    queue_request.max_dispatches_per_second,
                ]
            ):
                queue["rate_limits"] = {}

                if queue_request.max_concurrent_dispatches:
                    queue["rate_limits"][
                        "max_concurrent_dispatches"
                    ] = queue_request.max_concurrent_dispatches

                if queue_request.max_dispatches_per_second:
                    queue["rate_limits"][
                        "max_dispatches_per_second"
                    ] = queue_request.max_dispatches_per_second

            # Add retry config if provided
            if any([queue_request.max_retry_duration, queue_request.max_attempts]):
                queue["retry_config"] = {}

                if queue_request.max_retry_duration:
                    queue["retry_config"][
                        "max_retry_duration"
                    ] = f"{queue_request.max_retry_duration}s"

                if queue_request.max_attempts:
                    queue["retry_config"]["max_attempts"] = queue_request.max_attempts

            self.client.create_queue(parent=self.parent, queue=queue)

            self.logger.info(
                "Queue created successfully",
                extra={"queue_name": queue_request.queue_name},
            )

            return QueueCreateResponse(
                queue_name=queue_request.queue_name,
                state="RUNNING",
                created_time=datetime.now(timezone.utc),
            )

        except Exception as e:
            self.logger.error(
                "Failed to create queue",
                extra={"error": str(e), "queue_name": queue_request.queue_name},
            )
            raise CloudTasksException(f"Failed to create queue: {str(e)}")

    def get_queue(self, queue_name: str) -> QueueResponse:
        """
        Get information about a queue.

        Args:
            queue_name (str): The name of the queue.

        Returns:
            QueueResponse: The queue information.

        Raises:
            QueueNotFoundException: If the queue is not found.
        """
        try:
            queue_path = f"{self.parent}/queues/{queue_name}"
            queue = self.client.get_queue(name=queue_path)

            return self._convert_queue_to_response(queue)

        except Exception as e:
            self.logger.error(
                "Failed to get queue", extra={"error": str(e), "queue_name": queue_name}
            )

            if "NOT_FOUND" in str(e):
                raise QueueNotFoundException(f"Queue '{queue_name}' not found")
            else:
                raise CloudTasksException(f"Failed to get queue: {str(e)}")

    def list_queues(
        self, page_size: int = 100, page_token: Optional[str] = None
    ) -> QueueListResponse:
        """
        List all queues in the project.

        Args:
            page_size (int): Maximum number of queues to return.
            page_token (Optional[str]): Token for pagination.

        Returns:
            QueueListResponse: List of queues with pagination info.
        """
        try:
            request = {"parent": self.parent, "page_size": page_size}

            if page_token:
                request["page_token"] = page_token

            response = self.client.list_queues(**request)

            queues = [
                self._convert_queue_to_response(queue) for queue in response.queues
            ]

            return QueueListResponse(
                queues=queues,
                next_page_token=(
                    response.next_page_token if response.next_page_token else None
                ),
            )

        except Exception as e:
            self.logger.error("Failed to list queues", extra={"error": str(e)})
            raise CloudTasksException(f"Failed to list queues: {str(e)}")

    def delete_queue(self, queue_name: str) -> TaskOperationResponse:
        """
        Delete a queue.

        Args:
            queue_name (str): The name of the queue.

        Returns:
            TaskOperationResponse: Operation result.

        Raises:
            QueueNotFoundException: If the queue is not found.
        """
        try:
            queue_path = f"{self.parent}/queues/{queue_name}"
            self.client.delete_queue(name=queue_path)

            self.logger.info(
                "Queue deleted successfully", extra={"queue_name": queue_name}
            )

            return TaskOperationResponse(
                success=True, message=f"Queue '{queue_name}' deleted successfully"
            )

        except Exception as e:
            self.logger.error(
                "Failed to delete queue",
                extra={"error": str(e), "queue_name": queue_name},
            )

            if "NOT_FOUND" in str(e):
                raise QueueNotFoundException(f"Queue '{queue_name}' not found")
            else:
                raise CloudTasksException(f"Failed to delete queue: {str(e)}")

    def purge_queue(self, queue_name: str) -> TaskOperationResponse:
        """
        Purge all tasks from a queue.

        Args:
            queue_name (str): The name of the queue.

        Returns:
            TaskOperationResponse: Operation result.

        Raises:
            QueueNotFoundException: If the queue is not found.
        """
        try:
            queue_path = f"{self.parent}/queues/{queue_name}"
            self.client.purge_queue(name=queue_path)

            self.logger.info(
                "Queue purged successfully", extra={"queue_name": queue_name}
            )

            return TaskOperationResponse(
                success=True, message=f"Queue '{queue_name}' purged successfully"
            )

        except Exception as e:
            self.logger.error(
                "Failed to purge queue",
                extra={"error": str(e), "queue_name": queue_name},
            )

            if "NOT_FOUND" in str(e):
                raise QueueNotFoundException(f"Queue '{queue_name}' not found")
            else:
                raise CloudTasksException(f"Failed to purge queue: {str(e)}")

    def _construct_task_url(self, relative_uri: str) -> str:
        """
        Construct the full URL for a task.

        Args:
            relative_uri (str): The relative URI path.

        Returns:
            str: The full URL for the task.
        """
        base_url = env("CLOUD_TASKS_BASE_URL")
        if not base_url:
            # Default to Cloud Functions URL pattern
            service_name = env("SERVICE_NAME", "spartan-function")
            base_url = (
                f"https://{self.location}-{self.project_id}"
                f".cloudfunctions.net/{service_name}"
            )

        return f"{base_url.rstrip('/')}{relative_uri}"

    def _extract_task_payload(self, task) -> dict:
        """Extract and parse payload from task."""
        payload = {}
        if hasattr(task, "http_request") and task.http_request.body:
            try:
                payload = json.loads(task.http_request.body.decode())
            except (json.JSONDecodeError, UnicodeDecodeError):
                payload = {"raw_body": task.http_request.body.decode(errors="ignore")}
        return payload

    def _extract_task_http_info(self, task) -> tuple:
        """Extract HTTP method, URI, and headers from task."""
        http_method = "POST"
        relative_uri = "/"
        headers = {}

        if hasattr(task, "http_request"):
            if task.http_request.http_method:
                http_method = task.http_request.http_method.name
            if task.http_request.url:
                # Extract relative URI from full URL
                url_parts = task.http_request.url.split("/", 3)
                relative_uri = "/" + url_parts[3] if len(url_parts) > 3 else "/"
            if task.http_request.headers:
                headers = dict(task.http_request.headers)

        return http_method, relative_uri, headers

    def _extract_task_attempt_info(self, task) -> tuple:
        """Extract attempt information from task."""
        dispatch_count = 0
        response_count = 0
        first_attempt_time = None
        last_attempt_time = None

        if hasattr(task, "dispatch_count"):
            dispatch_count = task.dispatch_count
        if hasattr(task, "response_count"):
            response_count = task.response_count
        if hasattr(task, "first_attempt") and task.first_attempt:
            if hasattr(task.first_attempt, "schedule_time"):
                first_attempt_time = task.first_attempt.schedule_time.ToDatetime()
        if hasattr(task, "last_attempt") and task.last_attempt:
            if hasattr(task.last_attempt, "schedule_time"):
                last_attempt_time = task.last_attempt.schedule_time.ToDatetime()

        return dispatch_count, response_count, first_attempt_time, last_attempt_time

    def _convert_task_to_response(self, task, queue_name: str) -> TaskResponse:
        """
        Convert a Cloud Tasks task to TaskResponse.

        Args:
            task: The Cloud Tasks task object.
            queue_name (str): The name of the queue.

        Returns:
            TaskResponse: The converted task response.
        """
        # Extract task name from full path
        task_name = task.name.split("/")[-1] if task.name else ""

        # Parse payload
        payload = self._extract_task_payload(task)

        # Extract schedule time
        schedule_time = None
        if hasattr(task, "schedule_time") and task.schedule_time:
            schedule_time = task.schedule_time.ToDatetime()

        # Extract creation time
        created_time = datetime.now(timezone.utc)
        if hasattr(task, "create_time") and task.create_time:
            created_time = task.create_time.ToDatetime()

        # Extract HTTP method, URI, and headers
        http_method, relative_uri, headers = self._extract_task_http_info(task)

        # Extract attempt information
        (
            dispatch_count,
            response_count,
            first_attempt_time,
            last_attempt_time,
        ) = self._extract_task_attempt_info(task)

        return TaskResponse(
            task_name=task_name,
            queue_name=queue_name,
            payload=payload,
            schedule_time=schedule_time,
            created_time=created_time,
            http_method=http_method,
            relative_uri=relative_uri,
            headers=headers,
            dispatch_count=dispatch_count,
            response_count=response_count,
            first_attempt_time=first_attempt_time,
            last_attempt_time=last_attempt_time,
        )

    def _extract_queue_rate_limits(self, queue) -> tuple:
        """Extract rate limits from queue."""
        max_concurrent_dispatches = None
        max_dispatches_per_second = None
        if hasattr(queue, "rate_limits") and queue.rate_limits:
            if hasattr(queue.rate_limits, "max_concurrent_dispatches"):
                max_concurrent_dispatches = queue.rate_limits.max_concurrent_dispatches
            if hasattr(queue.rate_limits, "max_dispatches_per_second"):
                max_dispatches_per_second = queue.rate_limits.max_dispatches_per_second
        return max_concurrent_dispatches, max_dispatches_per_second

    def _extract_queue_retry_config(self, queue) -> tuple:
        """Extract retry configuration from queue."""
        max_retry_duration = None
        max_attempts = None
        if hasattr(queue, "retry_config") and queue.retry_config:
            if hasattr(queue.retry_config, "max_retry_duration"):
                # Convert duration string to seconds
                duration_str = queue.retry_config.max_retry_duration
                if duration_str.endswith("s"):
                    max_retry_duration = int(duration_str[:-1])
            if hasattr(queue.retry_config, "max_attempts"):
                max_attempts = queue.retry_config.max_attempts
        return max_retry_duration, max_attempts

    def _convert_queue_to_response(self, queue) -> QueueResponse:
        """
        Convert a Cloud Tasks queue to QueueResponse.

        Args:
            queue: The Cloud Tasks queue object.

        Returns:
            QueueResponse: The converted queue response.
        """
        # Extract queue name from full path
        queue_name = queue.name.split("/")[-1] if queue.name else ""

        # Extract state
        state = "UNKNOWN"
        if hasattr(queue, "state"):
            state = queue.state.name

        # Extract rate limits
        (
            max_concurrent_dispatches,
            max_dispatches_per_second,
        ) = self._extract_queue_rate_limits(queue)

        # Extract retry config
        max_retry_duration, max_attempts = self._extract_queue_retry_config(queue)

        # Extract purge time
        purge_time = None
        if hasattr(queue, "purge_time") and queue.purge_time:
            purge_time = queue.purge_time.ToDatetime()

        # Extract stats
        stats_approximate_tasks = 0
        if hasattr(queue, "stats") and queue.stats:
            if hasattr(queue.stats, "tasks_count"):
                stats_approximate_tasks = queue.stats.tasks_count

        return QueueResponse(
            queue_name=queue_name,
            state=state,
            max_concurrent_dispatches=max_concurrent_dispatches,
            max_dispatches_per_second=max_dispatches_per_second,
            max_retry_duration=max_retry_duration,
            max_attempts=max_attempts,
            purge_time=purge_time,
            stats_approximate_tasks=stats_approximate_tasks,
        )
