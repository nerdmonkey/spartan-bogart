from typing import Any, Dict

from app.helpers.logger import get_logger


logger = get_logger("spartan.inference")


def main(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    logger.info(
        f"Event: {event}, Context: {getattr(context, '__dict__', str(context))}"
    )

    return {"statusCode": 200, "body": "Hello Spartan!"}


if __name__ == "__main__":
    from app.helpers.context import MockLambdaContext, MockLambdaEvent

    event = MockLambdaEvent()
    context = MockLambdaContext()

    try:
        logger.info("Handler Response", extra={"response": main(event, context)})
    except Exception as e:
        logger.exception("Unhandled exception in main", extra={"error": str(e)})
