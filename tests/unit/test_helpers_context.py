import json

from app.helpers.context import MockLambdaContext, MockLambdaEvent


def test_mock_lambda_context_attributes():
    ctx = MockLambdaContext()
    assert ctx.function_name == "mock_function_name"
    assert ctx.function_version == "$LATEST"
    assert ctx.invoked_function_arn.startswith("arn:aws:lambda")
    assert ctx.memory_limit_in_mb == 512
    assert ctx.aws_request_id == "mock_aws_request_id"
    assert ctx.log_group_name == "/aws/lambda/mock_function_name"
    assert ctx.log_stream_name.startswith("2024/10/20")
    assert ctx.get_remaining_time_in_millis() == 300000


def test_mock_lambda_event_to_dict_and_json():
    event = MockLambdaEvent()
    d = event.to_dict()
    assert d == {"key1": "value1", "key2": "value2", "key3": "value3"}
    j = event.to_json()
    assert json.loads(j) == d
