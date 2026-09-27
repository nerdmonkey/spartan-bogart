"""Manual demo script for StandardLoggerService features: PII redaction, environment
metadata inclusion, and log sampling. Not a Lambda handler — run directly with
`python docs/examples/pii-logging-demo.py` to eyeball CloudWatch-style log output.

Moved out of handlers/inference.py so the starter handler stays a clean example.
"""

from app.helpers.logger import get_logger


logger = get_logger("spartan.pii-logging-demo")


def run_demo() -> None:
    # PII sanitization: password/api_key/token/secret/credentials fields should be
    # redacted in the emitted log record; normal_field should pass through untouched.
    logger.info(
        "Testing PII sanitization",
        extra={
            "username": "test_user",
            "password": "super_secret_password",
            "api_key": "sk-1234567890abcdef",
            "token": "jwt_token_here",
            "secret": "should_be_redacted",
            "normal_field": "this_should_appear",
        },
    )

    # Environment metadata inclusion
    logger.info("Testing environment metadata inclusion")

    # Log sampling: with LOG_SAMPLE_RATE < 1.0, only a fraction of these should emit.
    for i in range(10):
        logger.info(f"Batch log message {i + 1} - testing sampling rate")

    logger.info("This is an info message")
    logger.debug("This is a debug message")
    logger.error(
        "This is an error message",
        extra={
            "error_code": 500,
            "details": "An error occurred",
            "credentials": "should_be_redacted",
        },
    )
    logger.warning("This is a warning message")


if __name__ == "__main__":
    run_demo()
