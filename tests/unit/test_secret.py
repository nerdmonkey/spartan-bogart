import json
from types import SimpleNamespace

import pytest

from app.helpers.secret import Secret


def test_secret_without_id_defaults():
    s = Secret()
    # no data loaded, should return default when using call
    assert s("missing", "default") == "default"

    # attribute access should raise AttributeError
    with pytest.raises(AttributeError):
        _ = s.somekey


def test_secret_load_success(mocker):
    secret_payload = {"username": "admin", "password": "s3cr3t"}
    response = {"SecretString": json.dumps(secret_payload)}

    # fake boto3 client that returns our response
    fake_client = SimpleNamespace(get_secret_value=lambda SecretId: response)
    mocker.patch("boto3.client", return_value=fake_client)

    s = Secret("my-secret-id")

    # access via call and attribute
    assert s("username") == "admin"
    assert s.username == "admin"
    # missing key returns provided default
    assert s("nope", "fallback") == "fallback"


def test_secret_load_exception(mocker):
    # client that raises when fetching the secret
    class BadClient:
        def get_secret_value(self, SecretId):
            raise Exception("nope")

    mocker.patch("boto3.client", return_value=BadClient())

    s = Secret("bad-id")

    # should fall back to empty data and return defaults
    assert s("any", "def") == "def"
    with pytest.raises(AttributeError):
        _ = s.username
