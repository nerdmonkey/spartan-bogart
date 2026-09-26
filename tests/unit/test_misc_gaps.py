import sys
import types
from datetime import datetime

import boto3
import pytest


# app.services.tracer transitively imports app.services.tracing.cloud, which
# imports aws_xray_sdk.core at module load time. Stub it so importing here
# never opens a real UDP socket (blocked by the test-wide socket guard) even
# when this file runs in isolation before any other module has done so.
if "aws_xray_sdk.core" not in sys.modules:
    _fake_core = types.ModuleType("aws_xray_sdk.core")
    _fake_core.xray_recorder = types.SimpleNamespace(
        put_annotation=lambda *a, **k: None,
        begin_segment=lambda *a, **k: None,
        end_segment=lambda *a, **k: None,
        begin_subsegment=lambda *a, **k: None,
        end_subsegment=lambda *a, **k: None,
    )
    sys.modules["aws_xray_sdk.core"] = _fake_core
    sys.modules["aws_xray_sdk"] = types.ModuleType("aws_xray_sdk")
    sys.modules["aws_xray_sdk"].core = _fake_core


def test_logger_service_get_logger_defaults_and_named(monkeypatch):
    from app.services.logger import LoggerService, get_logger

    LoggerService.get_logger.cache_clear()
    monkeypatch.setattr(
        "app.services.logger.env",
        lambda k=None, d=None: {"LOG_LEVEL": "INFO"}.get(k, d),
    )

    default_logger = LoggerService.get_logger()
    assert default_logger is not None

    named_logger = get_logger("custom-service")
    assert named_logger is not None


def test_tracer_service_module_level_helpers(monkeypatch):
    from app.services import tracer as tracer_mod

    class FakeTracer:
        def capture_lambda_handler(self, handler):
            return handler

        def capture_method(self, method):
            return method

    tracer_mod.TracerService.get_tracer.cache_clear()
    monkeypatch.setattr(
        tracer_mod.TracerService, "get_tracer", staticmethod(lambda: FakeTracer())
    )

    def handler(e, c):
        return "handled"

    assert tracer_mod.capture_lambda_handler(handler)("e", "c") == "handled"

    def method(self):
        return "method-result"

    assert tracer_mod.capture_method(method)(None) == "method-result"
    assert tracer_mod.get_tracer() is not None


def test_tracer_service_get_tracer_real_path_returns_local(monkeypatch):
    from app.services import tracer as tracer_mod

    tracer_mod.TracerService.get_tracer.cache_clear()
    monkeypatch.setattr(
        "app.services.tracing.factory.env",
        lambda k, d=None: {"APP_ENVIRONMENT": "local"}.get(k, d),
    )

    from app.services.tracing.local import LocalTracer

    tracer = tracer_mod.TracerService.get_tracer()
    assert isinstance(tracer, LocalTracer)
    tracer_mod.TracerService.get_tracer.cache_clear()


def test_helpers_tracer_reexports_services_tracer():
    from app.helpers import tracer as helpers_tracer
    from app.services.tracer import TracerService

    assert helpers_tracer.TracerService is TracerService
    assert helpers_tracer.get_tracer is not None
    assert helpers_tracer.trace_function is not None
    assert helpers_tracer.trace_segment is not None
    assert helpers_tracer.capture_lambda_handler is not None
    assert helpers_tracer.capture_method is not None


def test_ddb_model_else_branch_stringifies_unknown_type():
    from app.models.ddb.ddb_base import DDBModel

    class WithArbitraryType(DDBModel):
        value: object

        def pk(self):
            return "PK"

        def sk(self):
            return "SK"

        @classmethod
        def from_ddb_item(cls, item):
            return cls(value=item["value"])

    class Weird:
        def __str__(self):
            return "weird-value"

    model = WithArbitraryType(value=Weird())
    item = model.to_ddb_item()
    assert item["value"] == {"S": "weird-value"}


def test_user_update_request_explicit_none_hits_allow_none_branch():
    from app.requests.user import UserUpdateRequest

    req = UserUpdateRequest(username=None, email=None)
    assert req.username is None
    assert req.email is None


def test_user_service_filter_by_date_range_list_condition():
    from app.services.user import UserService

    class FakeUser:
        def __init__(self, created_at):
            self.created_at = created_at

    svc = UserService(db=None)
    svc.filtered_users = [
        FakeUser(datetime(2024, 1, 1)),
        FakeUser(datetime(2024, 6, 1)),
        FakeUser(datetime(2024, 12, 1)),
    ]

    result = svc.filter([datetime(2024, 5, 1), datetime(2024, 7, 1)])
    assert result is svc
    assert len(svc.filtered_users) == 1
    assert svc.filtered_users[0].created_at == datetime(2024, 6, 1)


def test_user_service_filter_by_attribute_condition():
    from app.services.user import UserService

    class FakeUser:
        def __init__(self, username):
            self.username = username

    class FakeLeft:
        key = "username"

    class FakeRight:
        value = "bob"

    class FakeCondition:
        left = FakeLeft()
        right = FakeRight()

    svc = UserService(db=None)
    svc.filtered_users = [FakeUser("bob"), FakeUser("alice")]

    result = svc.filter(FakeCondition())
    assert result is svc
    assert len(svc.filtered_users) == 1
    assert svc.filtered_users[0].username == "bob"


def test_app_service_boto3_error_paths_are_swallowed(monkeypatch):
    from unittest.mock import MagicMock, patch

    from app.services.app import AppService

    with patch("app.services.app.boto3") as mock_boto3:
        mock_boto3.exceptions.Boto3Error = boto3.exceptions.Boto3Error
        dummy_resource = MagicMock()
        dummy_table = MagicMock()
        dummy_resource.Table.return_value = dummy_table
        mock_boto3.resource.return_value = dummy_resource

        svc = AppService()

        dummy_table.update_item.side_effect = boto3.exceptions.Boto3Error("fail")
        with pytest.raises(boto3.exceptions.Boto3Error):
            svc.set_state("k", "v")

        dummy_table.get_item.side_effect = boto3.exceptions.Boto3Error("fail")
        with pytest.raises(boto3.exceptions.Boto3Error):
            svc.get_state("k")

        dummy_table.delete_item.side_effect = boto3.exceptions.Boto3Error("fail")
        with pytest.raises(boto3.exceptions.Boto3Error):
            svc.remove_state("k")
