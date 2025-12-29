import functions_framework
from cloudevents.http.event import CloudEvent
from app.helpers.logger import get_logger
from app.helpers.environment import env

logger = get_logger("spartan.lazaro.main")
from config.app import config

@functions_framework.cloud_event
def main(cloud_event: CloudEvent) -> None:
    try:

        # Process event
        logger.info(
            "Spartan Received Cloud Event",
            extra={
                "event_type": cloud_event["type"],
                "event_source": cloud_event["source"],
                "event_id": cloud_event["id"],
                "app_environment": env("APP_ENVIRONMENT", "unknown"),
                "log_level": env("LOG_LEVEL", "INFO"),
                "log_channel": env("LOG_CHANNEL", "default"),
                "data": cloud_event.data,
            },
        )

    except Exception as e:
        logger.exception("Failed to process", extra={"error": str(e)})
        raise  # Causes Pub/Sub to retry

    # No return value needed for Pub/Sub triggers


if __name__ == "__main__":
    """
    Local testing entry point.
    Run with: python main.py
    """
    from app.helpers.context import MockCloudEvent

    # Create a mock CloudEvent for testing
    mock_event_data = MockCloudEvent().to_dict()

    # Create CloudEvent from mock data
    test_event = CloudEvent(
        attributes={
            "specversion": mock_event_data["specversion"],
            "type": mock_event_data["type"],
            "source": mock_event_data["source"],
            "id": mock_event_data["id"],
        },
        data=mock_event_data["data"],
    )

    # Test the function locally
    print("=" * 60)
    print("Testing Cloud Function locally with mock GCP CloudEvent")
    print("=" * 60)

    try:
        main(test_event)
        print("\n✓ Function executed successfully")
    except Exception as e:
        print(f"\n✗ Function failed: {e}")
        raise
