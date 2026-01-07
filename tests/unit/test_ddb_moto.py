"""
Unit test that mocks boto3 and the environment for DynamoDB client/resource
initialization. This replaces the previous moto-based test so tests can run
without relying on moto being installed.
"""

from types import SimpleNamespace

import app.helpers.ddb as ddb_mod


def test_get_dynamodb_clients_with_mocked_boto3(mocker):
    # Prepare fake settings used by get_dynamodb_clients
    settings = SimpleNamespace(
        DDB_TYPE="local",
        DDB_TABLE_NAME="tbl",
        APP_RUNTIME="lambda",
        DDB_MAX_POOL_CONNECTIONS=5,
        DDB_MAX_RETRY_ATTEMPTS=2,
        DDB_READ_TIMEOUT=30,
        DDB_CONNECT_TIMEOUT=5,
        DDB_REGION="us-east-1",
    )

    # Patch env() to return our settings
    mocker.patch("app.helpers.ddb.env", return_value=settings)

    # Fake DynamoDB resource and client
    fake_table = SimpleNamespace(name="tbl")
    fake_resource = SimpleNamespace(Table=lambda name: fake_table)
    fake_client = SimpleNamespace(
        describe_table=lambda TableName: {"Table": {"TableStatus": "ACTIVE"}}
    )

    mocker.patch("app.helpers.ddb.boto3.resource", return_value=fake_resource)
    mocker.patch("app.helpers.ddb.boto3.client", return_value=fake_client)

    # Ensure lru_cache is cleared so patched functions are used
    try:
        ddb_mod.get_dynamodb_clients.cache_clear()
    except Exception:
        # If not cached yet, ignore
        pass

    resource, client, table = ddb_mod.get_dynamodb_clients()

    assert resource is fake_resource
    assert client is fake_client
    assert table is fake_table
