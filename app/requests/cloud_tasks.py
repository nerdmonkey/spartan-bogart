from datetime import datetime
from typing import Dict, Optional

from pydantic import BaseModel, ConfigDict, field_validator


class TaskCreateRequest(BaseModel):
    """
    Data model for creating a new Cloud Task.

    Attributes:
        queue_name (str): The name of the Cloud Tasks queue.
        task_name (Optional[str]): Optional task name. If not provided,
            Cloud Tasks will generate one.
        payload (Dict): The task payload data.
        schedule_time (Optional[datetime]): When to execute the task.
            If not provided, executes immediately.
        http_method (str): HTTP method for the task (GET, POST, PUT, DELETE).
        relative_uri (str): The relative URI path for the task handler.
        headers (Optional[Dict[str, str]]): Optional HTTP headers for the task.
    """

    queue_name: str
    task_name: Optional[str] = None
    payload: Dict
    schedule_time: Optional[datetime] = None
    http_method: str = "POST"
    relative_uri: str
    headers: Optional[Dict[str, str]] = None

    model_config = ConfigDict(from_attributes=True)

    @field_validator("queue_name", mode="before")
    def validate_queue_name(cls, value):
        if not value or not value.strip():
            raise ValueError("Queue name is required")

        if len(value) > 100:
            raise ValueError("Queue name must be at most 100 characters long")

        return value.strip()

    @field_validator("http_method", mode="before")
    def validate_http_method(cls, value):
        allowed_methods = ["GET", "POST", "PUT", "DELETE", "PATCH"]
        if value.upper() not in allowed_methods:
            raise ValueError(f"HTTP method must be one of {allowed_methods}")

        return value.upper()

    @field_validator("relative_uri", mode="before")
    def validate_relative_uri(cls, value):
        if not value or not value.strip():
            raise ValueError("Relative URI is required")

        if not value.startswith("/"):
            value = "/" + value

        return value

    @field_validator("task_name", mode="before")
    def validate_task_name(cls, value):
        if value is None:
            return value

        if not value.strip():
            return None

        if len(value) > 500:
            raise ValueError("Task name must be at most 500 characters long")

        return value.strip()


class TaskUpdateRequest(BaseModel):
    """
    Data model for updating a Cloud Task.

    Attributes:
        schedule_time (Optional[datetime]): New schedule time for the task.
        payload (Optional[Dict]): Updated task payload.
        headers (Optional[Dict[str, str]]): Updated HTTP headers.
    """

    schedule_time: Optional[datetime] = None
    payload: Optional[Dict] = None
    headers: Optional[Dict[str, str]] = None

    model_config = ConfigDict(from_attributes=True)


class QueueCreateRequest(BaseModel):
    """
    Data model for creating a Cloud Tasks queue.

    Attributes:
        queue_name (str): The name of the queue to create.
        max_concurrent_dispatches (Optional[int]): Maximum number of
            concurrent task dispatches.
        max_dispatches_per_second (Optional[float]): Maximum task
            dispatch rate.
        max_retry_duration (Optional[int]): Maximum retry duration
            in seconds.
        max_attempts (Optional[int]): Maximum number of retry attempts.
    """

    queue_name: str
    max_concurrent_dispatches: Optional[int] = None
    max_dispatches_per_second: Optional[float] = None
    max_retry_duration: Optional[int] = None
    max_attempts: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)

    @field_validator("queue_name", mode="before")
    def validate_queue_name(cls, value):
        if not value or not value.strip():
            raise ValueError("Queue name is required")

        if len(value) > 100:
            raise ValueError("Queue name must be at most 100 characters long")

        return value.strip()

    @field_validator("max_concurrent_dispatches", mode="before")
    def validate_max_concurrent_dispatches(cls, value):
        if value is not None and value <= 0:
            raise ValueError("Max concurrent dispatches must be positive")

        return value

    @field_validator("max_dispatches_per_second", mode="before")
    def validate_max_dispatches_per_second(cls, value):
        if value is not None and value <= 0:
            raise ValueError("Max dispatches per second must be positive")

        return value

    @field_validator("max_retry_duration", mode="before")
    def validate_max_retry_duration(cls, value):
        if value is not None and value <= 0:
            raise ValueError("Max retry duration must be positive")

        return value

    @field_validator("max_attempts", mode="before")
    def validate_max_attempts(cls, value):
        if value is not None and value <= 0:
            raise ValueError("Max attempts must be positive")

        return value
