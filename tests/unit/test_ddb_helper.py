from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from botocore.exceptions import ClientError


def _settings(**overrides):
    base = dict(
        DDB_TYPE="local",
        APP_RUNTIME="lambda",
        DDB_MAX_POOL_CONNECTIONS=50,
        DDB_MAX_RETRY_ATTEMPTS=3,
        DDB_READ_TIMEOUT=60,
        DDB_CONNECT_TIMEOUT=10,
        DDB_REGION="ap-southeast-1",
        DDB_TABLE_NAME="Table",
    )
    base.update(overrides)
    return SimpleNamespace(**base)


@pytest.fixture(autouse=True)
def _clear_cache():
    from app.helpers import ddb

    def _safe_clear():
        clear = getattr(ddb.get_dynamodb_clients, "cache_clear", None)
        if clear:
            clear()

    _safe_clear()
    yield
    _safe_clear()


def test_get_dynamodb_clients_local(monkeypatch):
    from app.helpers import ddb

    monkeypatch.setattr(ddb, "env", lambda: _settings(DDB_TYPE="local"))

    fake_table = MagicMock()
    fake_resource = MagicMock()
    fake_resource.Table.return_value = fake_table
    fake_client = MagicMock()
    fake_client.describe_table.return_value = {"Table": {"TableStatus": "ACTIVE"}}

    monkeypatch.setattr(ddb.boto3, "resource", lambda *a, **k: fake_resource)
    monkeypatch.setattr(ddb.boto3, "client", lambda *a, **k: fake_client)

    resource, client, table = ddb.get_dynamodb_clients()
    assert resource is fake_resource
    assert client is fake_client
    assert table is fake_table


def test_get_dynamodb_clients_container(monkeypatch):
    from app.helpers import ddb

    monkeypatch.setattr(
        ddb, "env", lambda: _settings(DDB_TYPE="aws", APP_RUNTIME="container")
    )

    fake_table = MagicMock()
    fake_resource = MagicMock()
    fake_resource.Table.return_value = fake_table
    fake_client = MagicMock()
    fake_client.describe_table.return_value = {"Table": {"TableStatus": "ACTIVE"}}

    monkeypatch.setattr(ddb.boto3, "resource", lambda *a, **k: fake_resource)
    monkeypatch.setattr(ddb.boto3, "client", lambda *a, **k: fake_client)

    resource, client, table = ddb.get_dynamodb_clients()
    assert resource is fake_resource
    assert client is fake_client
    assert table is fake_table


def test_get_dynamodb_clients_lambda_caps_pool_connections(monkeypatch):
    from app.helpers import ddb

    monkeypatch.setattr(
        ddb,
        "env",
        lambda: _settings(
            DDB_TYPE="aws", APP_RUNTIME="lambda", DDB_MAX_POOL_CONNECTIONS=50
        ),
    )

    fake_table = MagicMock()
    fake_resource = MagicMock()
    fake_resource.Table.return_value = fake_table
    fake_client = MagicMock()
    fake_client.describe_table.return_value = {"Table": {"TableStatus": "ACTIVE"}}

    monkeypatch.setattr(ddb.boto3, "resource", lambda *a, **k: fake_resource)
    monkeypatch.setattr(ddb.boto3, "client", lambda *a, **k: fake_client)

    resource, client, table = ddb.get_dynamodb_clients()
    assert table is fake_table


def test_get_dynamodb_clients_table_not_found_is_swallowed(monkeypatch):
    from app.helpers import ddb

    monkeypatch.setattr(ddb, "env", lambda: _settings(DDB_TYPE="local"))

    fake_resource = MagicMock()
    fake_resource.Table.return_value = MagicMock()
    fake_client = MagicMock()
    fake_client.describe_table.side_effect = ClientError(
        {"Error": {"Code": "ResourceNotFoundException", "Message": "nope"}},
        "DescribeTable",
    )

    monkeypatch.setattr(ddb.boto3, "resource", lambda *a, **k: fake_resource)
    monkeypatch.setattr(ddb.boto3, "client", lambda *a, **k: fake_client)

    resource, client, table = ddb.get_dynamodb_clients()
    assert client is fake_client


def test_get_dynamodb_clients_other_client_error_reraises(monkeypatch):
    from app.helpers import ddb

    monkeypatch.setattr(ddb, "env", lambda: _settings(DDB_TYPE="local"))

    fake_resource = MagicMock()
    fake_resource.Table.return_value = MagicMock()
    fake_client = MagicMock()
    fake_client.describe_table.side_effect = ClientError(
        {"Error": {"Code": "AccessDeniedException", "Message": "nope"}},
        "DescribeTable",
    )

    monkeypatch.setattr(ddb.boto3, "resource", lambda *a, **k: fake_resource)
    monkeypatch.setattr(ddb.boto3, "client", lambda *a, **k: fake_client)

    with pytest.raises(ClientError):
        ddb.get_dynamodb_clients()


def test_get_dynamodb_clients_unexpected_error_is_logged_and_raised(monkeypatch):
    from app.helpers import ddb

    monkeypatch.setattr(ddb, "env", lambda: _settings(DDB_TYPE="local"))

    def boom(*a, **k):
        raise RuntimeError("boto3 broke")

    monkeypatch.setattr(ddb.boto3, "resource", boom)

    with pytest.raises(RuntimeError):
        ddb.get_dynamodb_clients()


def test_get_clients_lazy_initializes_once(monkeypatch):
    from app.helpers import ddb

    monkeypatch.setattr(ddb, "dynamodb_resource", None)
    monkeypatch.setattr(ddb, "dynamodb_client", None)
    monkeypatch.setattr(ddb, "table", None)
    monkeypatch.setattr(ddb, "table_name", None)

    fake_resource = MagicMock()
    fake_client = MagicMock()
    fake_table = MagicMock()

    monkeypatch.setattr(
        ddb, "get_dynamodb_clients", lambda: (fake_resource, fake_client, fake_table)
    )
    monkeypatch.setattr(ddb, "env", lambda: _settings(DDB_TABLE_NAME="MyTable"))

    resource, client, table = ddb.get_clients()
    assert resource is fake_resource
    assert client is fake_client
    assert table is fake_table
    assert ddb.table_name == "MyTable"
