import pytest

from app.exceptions.cloud_tasks import (
    CloudTasksException,
    InvalidTaskPayloadException,
    QueueNotFoundException,
    TaskCreationException,
    TaskNotFoundException,
    TaskSchedulingException,
)


def test_cloud_tasks_exception_default_message():
    """Test CloudTasksException with default message."""
    exception = CloudTasksException()

    assert str(exception) == "Cloud Tasks operation failed"
    assert exception.message == "Cloud Tasks operation failed"


def test_cloud_tasks_exception_custom_message():
    """Test CloudTasksException with custom message."""
    custom_message = "Custom error occurred"
    exception = CloudTasksException(custom_message)

    assert str(exception) == custom_message
    assert exception.message == custom_message


def test_task_creation_exception_default_message():
    """Test TaskCreationException with default message."""
    exception = TaskCreationException()

    assert str(exception) == "Failed to create task"
    assert exception.message == "Failed to create task"


def test_task_creation_exception_custom_message():
    """Test TaskCreationException with custom message."""
    custom_message = "Task creation failed due to invalid queue"
    exception = TaskCreationException(custom_message)

    assert str(exception) == custom_message
    assert exception.message == custom_message


def test_task_creation_exception_inheritance():
    """Test TaskCreationException inherits from CloudTasksException."""
    exception = TaskCreationException()

    assert isinstance(exception, CloudTasksException)
    assert isinstance(exception, Exception)


def test_task_not_found_exception_default_message():
    """Test TaskNotFoundException with default message."""
    exception = TaskNotFoundException()

    assert str(exception) == "Task not found"
    assert exception.message == "Task not found"


def test_task_not_found_exception_custom_message():
    """Test TaskNotFoundException with custom message."""
    custom_message = "Task 'test-task' not found in queue 'test-queue'"
    exception = TaskNotFoundException(custom_message)

    assert str(exception) == custom_message
    assert exception.message == custom_message


def test_task_not_found_exception_inheritance():
    """Test TaskNotFoundException inherits from CloudTasksException."""
    exception = TaskNotFoundException()

    assert isinstance(exception, CloudTasksException)
    assert isinstance(exception, Exception)


def test_queue_not_found_exception_default_message():
    """Test QueueNotFoundException with default message."""
    exception = QueueNotFoundException()

    assert str(exception) == "Queue not found"
    assert exception.message == "Queue not found"


def test_queue_not_found_exception_custom_message():
    """Test QueueNotFoundException with custom message."""
    custom_message = "Queue 'test-queue' not found in project 'test-project'"
    exception = QueueNotFoundException(custom_message)

    assert str(exception) == custom_message
    assert exception.message == custom_message


def test_queue_not_found_exception_inheritance():
    """Test QueueNotFoundException inherits from CloudTasksException."""
    exception = QueueNotFoundException()

    assert isinstance(exception, CloudTasksException)
    assert isinstance(exception, Exception)


def test_invalid_task_payload_exception_default_message():
    """Test InvalidTaskPayloadException with default message."""
    exception = InvalidTaskPayloadException()

    assert str(exception) == "Invalid task payload"
    assert exception.message == "Invalid task payload"


def test_invalid_task_payload_exception_custom_message():
    """Test InvalidTaskPayloadException with custom message."""
    custom_message = "Task payload must be a valid JSON object"
    exception = InvalidTaskPayloadException(custom_message)

    assert str(exception) == custom_message
    assert exception.message == custom_message


def test_invalid_task_payload_exception_inheritance():
    """Test InvalidTaskPayloadException inherits from CloudTasksException."""
    exception = InvalidTaskPayloadException()

    assert isinstance(exception, CloudTasksException)
    assert isinstance(exception, Exception)


def test_task_scheduling_exception_default_message():
    """Test TaskSchedulingException with default message."""
    exception = TaskSchedulingException()

    assert str(exception) == "Failed to schedule task"
    assert exception.message == "Failed to schedule task"


def test_task_scheduling_exception_custom_message():
    """Test TaskSchedulingException with custom message."""
    custom_message = "Task scheduling failed due to invalid schedule time"
    exception = TaskSchedulingException(custom_message)

    assert str(exception) == custom_message
    assert exception.message == custom_message


def test_task_scheduling_exception_inheritance():
    """Test TaskSchedulingException inherits from CloudTasksException."""
    exception = TaskSchedulingException()

    assert isinstance(exception, CloudTasksException)
    assert isinstance(exception, Exception)


def test_exception_can_be_raised():
    """Test that exceptions can be raised and caught."""
    with pytest.raises(CloudTasksException):
        raise CloudTasksException("Test exception")

    with pytest.raises(TaskCreationException):
        raise TaskCreationException("Test task creation exception")

    with pytest.raises(TaskNotFoundException):
        raise TaskNotFoundException("Test task not found exception")

    with pytest.raises(QueueNotFoundException):
        raise QueueNotFoundException("Test queue not found exception")

    with pytest.raises(InvalidTaskPayloadException):
        raise InvalidTaskPayloadException("Test invalid payload exception")

    with pytest.raises(TaskSchedulingException):
        raise TaskSchedulingException("Test scheduling exception")


def test_exception_hierarchy():
    """Test that all exceptions can be caught as CloudTasksException."""
    exceptions = [
        TaskCreationException(),
        TaskNotFoundException(),
        QueueNotFoundException(),
        InvalidTaskPayloadException(),
        TaskSchedulingException(),
    ]

    for exception in exceptions:
        with pytest.raises(CloudTasksException):
            raise exception
