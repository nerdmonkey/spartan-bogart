from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, field_validator


class TaskResponse(BaseModel):
    """
    Pydantic model representing a Cloud Task response.

    Attributes:
        task_name (str): The full name of the task.
        queue_name (str): The name of the queue containing the task.
        payload (Dict): The task payload data.
        schedule_time (Optional[datetime]): When the task is scheduled to execute.
        created_time (datetime): When the task was created.
        http_method (str): HTTP method for the task.
        relative_uri (str): The relative URI path for the task handler.
        headers (Optional[Dict[str, str]]): HTTP headers for the task.
        dispatch_count (int): Number of times the task has been dispatched.
        response_count (int): Number of times the task has received a response.
        first_attempt_time (Optional[datetime]): Time of the first attempt.
        last_attempt_time (Optional[datetime]): Time of the last attempt.
    """

    task_name: str
    queue_name: str
    payload: Dict
    schedule_time: Optional[datetime] = None
    created_time: datetime
    http_method: str
    relative_uri: str
    headers: Optional[Dict[str, str]] = None
    dispatch_count: int = 0
    response_count: int = 0
    first_attempt_time: Optional[datetime] = None
    last_attempt_time: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

    @field_validator("task_name", mode="before")
    def validate_task_name(cls, value):
        if not value or not value.strip():
            raise ValueError("Task name is required")
        return value.strip()


class TaskCreateResponse(BaseModel):
    """
    Pydantic model representing a response for creating a Cloud Task.

    Attributes:
        task_name (str): The full name of the created task.
        queue_name (str): The name of the queue containing the task.
        schedule_time (Optional[datetime]): When the task is scheduled to execute.
        created_time (datetime): When the task was created.
        relative_uri (str): The relative URI path for the task handler.
    """

    task_name: str
    queue_name: str
    schedule_time: Optional[datetime] = None
    created_time: datetime
    relative_uri: str


class QueueResponse(BaseModel):
    """
    Pydantic model representing a Cloud Tasks queue response.

    Attributes:
        queue_name (str): The name of the queue.
        state (str): The current state of the queue (RUNNING, PAUSED, DISABLED).
        max_concurrent_dispatches (Optional[int]): Maximum concurrent dispatches.
        max_dispatches_per_second (Optional[float]): Maximum dispatch rate.
        max_retry_duration (Optional[int]): Maximum retry duration in seconds.
        max_attempts (Optional[int]): Maximum retry attempts.
        purge_time (Optional[datetime]): Last time the queue was purged.
        stats_approximate_tasks (int): Approximate number of tasks in the queue.
    """

    queue_name: str
    state: str
    max_concurrent_dispatches: Optional[int] = None
    max_dispatches_per_second: Optional[float] = None
    max_retry_duration: Optional[int] = None
    max_attempts: Optional[int] = None
    purge_time: Optional[datetime] = None
    stats_approximate_tasks: int = 0

    model_config = ConfigDict(from_attributes=True)


class QueueCreateResponse(BaseModel):
    """
    Pydantic model representing a response for creating a Cloud Tasks queue.

    Attributes:
        queue_name (str): The name of the created queue.
        state (str): The initial state of the queue.
        created_time (datetime): When the queue was created.
    """

    queue_name: str
    state: str
    created_time: datetime


class TaskListResponse(BaseModel):
    """
    Pydantic model representing a paginated response for a list of tasks.

    Attributes:
        tasks (List[TaskResponse]): The list of tasks.
        next_page_token (Optional[str]): Token for the next page of results.
        total_size (Optional[int]): Total number of tasks (if available).
    """

    tasks: List[TaskResponse]
    next_page_token: Optional[str] = None
    total_size: Optional[int] = None


class QueueListResponse(BaseModel):
    """
    Pydantic model representing a paginated response for a list of queues.

    Attributes:
        queues (List[QueueResponse]): The list of queues.
        next_page_token (Optional[str]): Token for the next page of results.
    """

    queues: List[QueueResponse]
    next_page_token: Optional[str] = None


class TaskOperationResponse(BaseModel):
    """
    Pydantic model representing a response for task operations (delete, run, etc.).

    Attributes:
        success (bool): Whether the operation was successful.
        message (str): Operation result message.
        task_name (Optional[str]): The name of the affected task.
    """

    success: bool
    message: str
    task_name: Optional[str] = None
