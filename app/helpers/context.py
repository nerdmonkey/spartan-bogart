import json


class MockLambdaContext:
    """
    MockLambdaContext is a mock implementation of the AWS Lambda context object.

    Attributes:
        function_name (str): The name of the Lambda function.
        function_version (str): The version of the Lambda function.
        invoked_function_arn (str): The ARN of the invoked Lambda function.
        memory_limit_in_mb (int): The memory limit configured for the Lambda function.
        aws_request_id (str): The AWS request ID for the Lambda invocation.
        log_group_name (str): The log group name for the Lambda function.
        log_stream_name (str): The log stream name for the Lambda function.

    Methods:
        get_remaining_time_in_millis() -> int:
            Returns the remaining time in milliseconds before the Lambda
            function times out.
    """

    def __init__(self):
        self.function_name = "mock_function_name"
        self.function_version = "$LATEST"
        self.invoked_function_arn = (
            "arn:aws:lambda:us-west-2:123456789012:function:mock_function"
        )
        self.memory_limit_in_mb = 512
        self.aws_request_id = "mock_aws_request_id"
        self.log_group_name = "/aws/lambda/mock_function_name"
        self.log_stream_name = "2024/10/20/[$LATEST]mock_log_stream"

    def get_remaining_time_in_millis(self) -> int:
        return 300000


class MockLambdaEvent:
    """
    A mock class to simulate an AWS Lambda event.

    Attributes:
        event (dict): A dictionary representing the mock event data with
            predefined key-value pairs.
    """

    def __init__(self):
        self.event = {
            "key1": "value1",
            "key2": "value2",
            "key3": "value3",
        }

    def to_dict(self):
        """
        Convert the MockLambdaEvent to a dictionary.

        Returns:
            dict: The dictionary representation of the event.
        """
        return self.event

    def to_json(self):
        """
        Convert the MockLambdaEvent to a JSON string.

        Returns:
            str: The JSON string representation of the event.
        """
        return json.dumps(self.event)
