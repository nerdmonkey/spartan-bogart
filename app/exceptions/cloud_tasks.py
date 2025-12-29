class CloudTasksException(Exception):
    """Base exception for Cloud Tasks operations."""

    def __init__(self, message="Cloud Tasks operation failed"):
        self.message = message
        super().__init__(self.message)


class TaskCreationException(CloudTasksException):
    """Exception raised when task creation fails."""

    def __init__(self, message="Failed to create task"):
        self.message = message
        super().__init__(self.message)


class TaskNotFoundException(CloudTasksException):
    """Exception raised when a task is not found."""

    def __init__(self, message="Task not found"):
        self.message = message
        super().__init__(self.message)


class QueueNotFoundException(CloudTasksException):
    """Exception raised when a queue is not found."""

    def __init__(self, message="Queue not found"):
        self.message = message
        super().__init__(self.message)


class InvalidTaskPayloadException(CloudTasksException):
    """Exception raised when task payload is invalid."""

    def __init__(self, message="Invalid task payload"):
        self.message = message
        super().__init__(self.message)


class TaskSchedulingException(CloudTasksException):
    """Exception raised when task scheduling fails."""

    def __init__(self, message="Failed to schedule task"):
        self.message = message
        super().__init__(self.message)
