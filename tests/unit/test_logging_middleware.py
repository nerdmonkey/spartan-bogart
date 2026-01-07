"""Unit tests for logging middleware using pytest-mock conventions"""

from unittest.mock import Mock

import pytest

from app.middlewares.logging import standard_logger


class MockContext:
    """Mock AWS Lambda context object"""

    def __init__(self):
        self.function_name = "test_function"
        self.function_version = "1.0"
        self.invoked_function_arn = (
            "arn:aws:lambda:us-east-1:123456789012:function:test"
        )
        self.memory_limit_in_mb = 128
        self.aws_request_id = "test-request-id"


class MockEvent(dict):
    """Mock AWS Lambda event object - inherits from dict for JSON serialization"""

    def __init__(self):
        super().__init__()
        self.update({"headers": {"Authorization": "Bearer token"}})

    @property
    def headers(self):
        return self.get("headers", {})


def test_standard_logger_success(mocker):
    """Test successful logging operation with proper mocking"""
    # Mock the get_logger function that standard_logger uses
    mock_logger = Mock()
    mocker.patch("app.middlewares.logging.get_logger", return_value=mock_logger)

    # Mock environment functions
    mocker.patch("app.middlewares.logging.env", return_value="test")

    # Create mock handler
    mock_handler = Mock(return_value={"statusCode": 200, "body": "success"})

    # Create wrapped handler
    wrapped_handler = standard_logger(mock_handler)

    # Execute
    result = wrapped_handler(MockEvent(), MockContext())

    # Verify result
    assert result["statusCode"] == 200
    assert result["body"] == "success"

    # Verify logger was called
    assert mock_logger.info.call_count >= 2  # Input and output logs
    mock_handler.assert_called_once()


def test_standard_logger_exception(mocker):
    """Test exception handling in logging middleware"""
    # Mock the get_logger function
    mock_logger = Mock()
    mocker.patch("app.middlewares.logging.get_logger", return_value=mock_logger)

    # Mock environment functions
    mocker.patch("app.middlewares.logging.env", return_value="test")

    # Create mock handler that raises exception
    mock_handler = Mock(side_effect=Exception("Test error"))

    # Create wrapped handler
    wrapped_handler = standard_logger(mock_handler)

    # Execute and expect exception to be re-raised
    with pytest.raises(Exception, match="Test error"):
        wrapped_handler(MockEvent(), MockContext())

    # Verify error was logged
    mock_logger.error.assert_called_once()
    error_call = mock_logger.error.call_args
    assert "Error in Lambda function" in error_call[0][0]


def test_standard_logger_input_output_logging(mocker):
    """Test that input and output data are logged"""
    # Mock the get_logger function
    mock_logger = Mock()
    mocker.patch("app.middlewares.logging.get_logger", return_value=mock_logger)

    # Mock environment functions
    mocker.patch("app.middlewares.logging.env", return_value="test")

    # Create test data - use dict instead of MockEvent for cleaner testing
    test_event = {"test": "input_data"}
    test_response = {"statusCode": 200, "body": "test_output"}

    mock_handler = Mock(return_value=test_response)
    wrapped_handler = standard_logger(mock_handler)

    # Execute
    result = wrapped_handler(test_event, MockContext())

    # Verify result
    assert result == test_response

    # Verify input and output logging
    assert mock_logger.info.call_count == 2

    # Check input log
    input_call = mock_logger.info.call_args_list[0]
    assert "Input Data" in input_call[0][0]
    assert "input_data" in input_call[1]["extra"]
    assert input_call[1]["extra"]["input_data"] == test_event

    # Check output log
    output_call = mock_logger.info.call_args_list[1]
    assert "Output Data" in output_call[0][0]
    assert "output_data" in output_call[1]["extra"]
    assert output_call[1]["extra"]["output_data"] == test_response


def test_standard_logger_lambda_context_logging(mocker):
    """Test that Lambda context information is included in logs"""
    # Mock the get_logger function
    mock_logger = Mock()
    mocker.patch("app.middlewares.logging.get_logger", return_value=mock_logger)

    # Mock environment functions
    mocker.patch("app.middlewares.logging.env", return_value="test")

    # Create context with specific values
    context = MockContext()
    context.aws_request_id = "test-request-123"
    context.function_name = "test-function-name"

    mock_handler = Mock(return_value={"statusCode": 200})
    wrapped_handler = standard_logger(mock_handler)

    # Execute
    wrapped_handler(MockEvent(), context)

    # Verify lambda function info is logged
    input_call = mock_logger.info.call_args_list[0]
    lambda_function = input_call[1]["extra"]["lambda_function"]

    assert lambda_function["aws_request_id"] == "test-request-123"
    assert lambda_function["name"] == "test-function-name"
    assert lambda_function["version"] == "1.0"
    assert lambda_function["memory_size"] == 128


def test_standard_logger_debug_mode(mocker):
    """Test debug mode behavior with local environment"""
    # Mock the get_logger function
    mock_logger = Mock()
    mocker.patch("app.middlewares.logging.get_logger", return_value=mock_logger)

    # Mock environment to return local and debug
    mock_env = Mock()
    mock_env.side_effect = lambda key: {
        "APP_ENVIRONMENT": "local",
        "APP_DEBUG": "true",
    }.get(key, "")
    mocker.patch("app.middlewares.logging.env", mock_env)

    # Mock print function
    mock_print = mocker.patch("builtins.print")

    mock_handler = Mock(return_value={"statusCode": 200})
    wrapped_handler = standard_logger(mock_handler)

    # Execute
    wrapped_handler(MockEvent(), MockContext())

    # Verify print was called for debug output
    assert mock_print.call_count == 2  # Input and output debug prints

    # Verify normal logging still works
    assert mock_logger.info.call_count == 2


def test_standard_logger_custom_logger(mocker):
    """Test using a custom logger parameter"""
    # Create custom mock logger
    custom_logger = Mock()

    # Mock environment functions
    mocker.patch("app.middlewares.logging.env", return_value="test")

    mock_handler = Mock(return_value={"statusCode": 200})

    # Use custom logger
    wrapped_handler = standard_logger(mock_handler, logger=custom_logger)

    # Execute
    wrapped_handler(MockEvent(), MockContext())

    # Verify custom logger was used
    assert custom_logger.info.call_count == 2
    assert custom_logger.error.call_count == 0


def test_standard_logger_data_size_calculation(mocker):
    """Test that data size is calculated and logged"""
    # Mock the get_logger function
    mock_logger = Mock()
    mocker.patch("app.middlewares.logging.get_logger", return_value=mock_logger)

    # Mock environment functions
    mocker.patch("app.middlewares.logging.env", return_value="test")

    # Create test data with known size - use dict for predictable serialization
    test_event = {"data": "x" * 100}  # Predictable size
    test_response = {"result": "y" * 50}

    mock_handler = Mock(return_value=test_response)
    wrapped_handler = standard_logger(mock_handler)

    # Execute
    wrapped_handler(test_event, MockContext())

    # Verify size calculations are logged
    input_call = mock_logger.info.call_args_list[0]
    output_call = mock_logger.info.call_args_list[1]

    assert "input_data_size" in input_call[1]["extra"]
    assert "output_data_size" in output_call[1]["extra"]

    # Size should be greater than 0
    assert input_call[1]["extra"]["input_data_size"] > 0
    assert output_call[1]["extra"]["output_data_size"] > 0
