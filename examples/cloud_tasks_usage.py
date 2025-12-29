"""
Example usage of the Cloud Tasks Service in Spartan Framework.

This example demonstrates how to use the CloudTasksService to:
1. Create and manage queues
2. Create and manage tasks
3. Handle errors and exceptions

Make sure to set the following environment variables:
- GCP_PROJECT_ID: Your Google Cloud Project ID
- GCP_LOCATION: Your preferred GCP location (e.g., us-central1)
- CLOUD_TASKS_BASE_URL: Base URL for your Cloud Function (optional)
"""

import asyncio
from datetime import datetime, timezone, timedelta

from app.services.cloud_tasks import CloudTasksService
from app.requests.cloud_tasks import TaskCreateRequest, QueueCreateRequest
from app.exceptions.cloud_tasks import (
    CloudTasksException,
    QueueNotFoundException,
    TaskNotFoundException,
)


def main():
    """Main example function demonstrating Cloud Tasks usage."""

    # Initialize the Cloud Tasks service
    # It will use environment variables for project_id and location
    try:
        cloud_tasks = CloudTasksService()
        print(
            f"✓ Cloud Tasks service initialized for project: {cloud_tasks.project_id}"
        )
    except CloudTasksException as e:
        print(f"✗ Failed to initialize Cloud Tasks service: {e}")
        return

    # Example 1: Create a queue
    print("\n" + "=" * 50)
    print("1. Creating a Cloud Tasks Queue")
    print("=" * 50)

    queue_request = QueueCreateRequest(
        queue_name="example-queue",
        max_concurrent_dispatches=10,
        max_dispatches_per_second=5.0,
        max_retry_duration=300,  # 5 minutes
        max_attempts=3,
    )

    try:
        queue_response = cloud_tasks.create_queue(queue_request)
        print(f"✓ Queue created: {queue_response.queue_name}")
        print(f"  State: {queue_response.state}")
        print(f"  Created at: {queue_response.created_time}")
    except CloudTasksException as e:
        print(f"✗ Failed to create queue: {e}")
        # Queue might already exist, continue with examples

    # Example 2: Create an immediate task
    print("\n" + "=" * 50)
    print("2. Creating an Immediate Task")
    print("=" * 50)

    immediate_task = TaskCreateRequest(
        queue_name="example-queue",
        task_name="immediate-task-001",
        payload={
            "user_id": 12345,
            "action": "send_welcome_email",
            "email": "user@example.com",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
        http_method="POST",
        relative_uri="/process-user-action",
        headers={
            "Authorization": "Bearer your-token-here",
            "Content-Type": "application/json",
        },
    )

    try:
        task_response = cloud_tasks.create_task(immediate_task)
        print(f"✓ Immediate task created: {task_response.task_name}")
        print(f"  Queue: {task_response.queue_name}")
        print(f"  URI: {task_response.relative_uri}")
        print(f"  Created at: {task_response.created_time}")
    except CloudTasksException as e:
        print(f"✗ Failed to create immediate task: {e}")

    # Example 3: Create a scheduled task
    print("\n" + "=" * 50)
    print("3. Creating a Scheduled Task")
    print("=" * 50)

    # Schedule task for 1 hour from now
    schedule_time = datetime.now(timezone.utc) + timedelta(hours=1)

    scheduled_task = TaskCreateRequest(
        queue_name="example-queue",
        task_name="scheduled-task-001",
        payload={
            "reminder_id": 67890,
            "user_id": 12345,
            "message": "Don't forget about your appointment tomorrow!",
            "scheduled_for": schedule_time.isoformat(),
        },
        schedule_time=schedule_time,
        http_method="POST",
        relative_uri="/send-reminder",
    )

    try:
        scheduled_response = cloud_tasks.create_task(scheduled_task)
        print(f"✓ Scheduled task created: {scheduled_response.task_name}")
        print(f"  Scheduled for: {scheduled_response.schedule_time}")
        print(f"  Created at: {scheduled_response.created_time}")
    except CloudTasksException as e:
        print(f"✗ Failed to create scheduled task: {e}")

    # Example 4: List tasks in the queue
    print("\n" + "=" * 50)
    print("4. Listing Tasks in Queue")
    print("=" * 50)

    try:
        task_list = cloud_tasks.list_tasks("example-queue", page_size=10)
        print(f"✓ Found {len(task_list.tasks)} tasks in queue")

        for i, task in enumerate(task_list.tasks, 1):
            print(f"  {i}. {task.task_name}")
            print(f"     Method: {task.http_method}")
            print(f"     URI: {task.relative_uri}")
            print(f"     Dispatches: {task.dispatch_count}")
            if task.schedule_time:
                print(f"     Scheduled: {task.schedule_time}")
            print()

        if task_list.next_page_token:
            print(f"  Next page token: {task_list.next_page_token}")

    except QueueNotFoundException as e:
        print(f"✗ Queue not found: {e}")
    except CloudTasksException as e:
        print(f"✗ Failed to list tasks: {e}")

    # Example 5: Get queue information
    print("\n" + "=" * 50)
    print("5. Getting Queue Information")
    print("=" * 50)

    try:
        queue_info = cloud_tasks.get_queue("example-queue")
        print(f"✓ Queue information:")
        print(f"  Name: {queue_info.queue_name}")
        print(f"  State: {queue_info.state}")
        print(f"  Approximate tasks: {queue_info.stats_approximate_tasks}")

        if queue_info.max_concurrent_dispatches:
            print(
                f"  Max concurrent dispatches: {queue_info.max_concurrent_dispatches}"
            )
        if queue_info.max_dispatches_per_second:
            print(
                f"  Max dispatches per second: {queue_info.max_dispatches_per_second}"
            )
        if queue_info.max_retry_duration:
            print(f"  Max retry duration: {queue_info.max_retry_duration}s")
        if queue_info.max_attempts:
            print(f"  Max attempts: {queue_info.max_attempts}")

    except QueueNotFoundException as e:
        print(f"✗ Queue not found: {e}")
    except CloudTasksException as e:
        print(f"✗ Failed to get queue info: {e}")

    # Example 6: List all queues
    print("\n" + "=" * 50)
    print("6. Listing All Queues")
    print("=" * 50)

    try:
        queue_list = cloud_tasks.list_queues()
        print(f"✓ Found {len(queue_list.queues)} queues")

        for i, queue in enumerate(queue_list.queues, 1):
            print(f"  {i}. {queue.queue_name} ({queue.state})")
            print(f"     Tasks: ~{queue.stats_approximate_tasks}")

    except CloudTasksException as e:
        print(f"✗ Failed to list queues: {e}")

    # Example 7: Error handling demonstration
    print("\n" + "=" * 50)
    print("7. Error Handling Examples")
    print("=" * 50)

    # Try to get a non-existent task
    try:
        cloud_tasks.get_task("example-queue", "non-existent-task")
    except TaskNotFoundException as e:
        print(f"✓ Correctly caught TaskNotFoundException: {e}")
    except CloudTasksException as e:
        print(f"✗ Unexpected error: {e}")

    # Try to create a task with invalid payload
    try:
        invalid_task = TaskCreateRequest(
            queue_name="example-queue",
            payload="invalid-payload",  # Should be dict
            relative_uri="/test",
        )
        cloud_tasks.create_task(invalid_task)
    except Exception as e:
        print(f"✓ Correctly caught validation error: {e}")

    print("\n" + "=" * 50)
    print("Example completed!")
    print("=" * 50)


if __name__ == "__main__":
    main()
