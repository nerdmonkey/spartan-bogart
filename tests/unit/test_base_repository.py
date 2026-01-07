import os
from datetime import datetime
from types import SimpleNamespace

import pytest


# Prevent app.helpers.ddb from initializing real clients during module import
# by setting test environment early.
os.environ.setdefault("APP_ENVIRONMENT", "test")

# Import BaseRepository directly from its source file to avoid executing
# `app.repositories.__init__` which imports many repository modules.
import importlib.util
from pathlib import Path


base_path = Path(__file__).resolve().parents[2] / "app" / "repositories" / "base.py"
spec = importlib.util.spec_from_file_location("app_repositories_base", str(base_path))
base_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base_mod)
BaseRepository = base_mod.BaseRepository


class FakeModel:
    def __init__(self, id: str, name: str, deleted_at=None):
        self.id = id
        self.name = name
        self.deleted_at = deleted_at
        self.updated_at = None

    @classmethod
    def from_ddb_item(cls, item: dict):
        # parse PK like ENTITY#<id>
        pk = item.get("PK", {}).get("S", "")
        _, id = pk.split("#", 1)
        name = item.get("Name", {}).get("S")
        # simulate invalid item
        if name == "bad":
            raise ValueError("bad item")

        deleted = None
        if "DeletedAt" in item and item["DeletedAt"].get("S") != "NULL":
            deleted = datetime.utcnow()

        return cls(id=id, name=name, deleted_at=deleted)

    def to_ddb_item(self):
        return {
            "PK": {"S": f"ENTITY#{self.id}"},
            "SK": {"S": "METADATA"},
            "Name": {"S": self.name},
        }


class RepoImpl(BaseRepository):
    def get_model_class(self):
        return FakeModel

    def get_entity_type(self):
        return "ENTITY"


def make_repo_with_client(client, table_name="tbl"):
    repo = RepoImpl()
    repo.dynamodb = client
    repo.table_name = table_name
    return repo


def test_get_by_id_validation():
    repo = make_repo_with_client(SimpleNamespace(get_item=lambda **k: {}))
    with pytest.raises(ValueError):
        repo.get_by_id(None)
    with pytest.raises(ValueError):
        repo.get_by_id("../etc/passwd")


def test_get_by_id_success_and_deleted(mocker):
    item = {"PK": {"S": "ENTITY#123"}, "SK": {"S": "METADATA"}, "Name": {"S": "ok"}}
    client = SimpleNamespace(get_item=lambda **k: {"Item": item})
    repo = make_repo_with_client(client)

    entity = repo.get_by_id("123")
    assert entity is not None
    assert entity.id == "123"

    # If item contains DeletedAt -> get_by_id should return None
    item_deleted = {
        "PK": {"S": "ENTITY#999"},
        "SK": {"S": "METADATA"},
        "Name": {"S": "ok"},
        "DeletedAt": {"S": "2020"},
    }
    client2 = SimpleNamespace(get_item=lambda **k: {"Item": item_deleted})
    repo2 = make_repo_with_client(client2)
    assert repo2.get_by_id("999") is None


def test_save_success_and_failure(mocker):
    # success
    client = SimpleNamespace(put_item=lambda **k: None)
    repo = make_repo_with_client(client)
    entity = FakeModel("1", "n")
    assert repo.save(entity) is True

    # failure
    def bad_put(**k):
        raise Exception("boom")

    client2 = SimpleNamespace(put_item=bad_put)
    repo2 = make_repo_with_client(client2)
    assert repo2.save(entity) is False


def test_soft_delete_calls_save_and_sets_timestamps(mocker):
    # Patch get_by_id_including_deleted to return a plain object
    repo = make_repo_with_client(SimpleNamespace())

    obj = SimpleNamespace(deleted_at=None, updated_at=None)

    def fake_get(id):
        return obj

    repo.get_by_id_including_deleted = fake_get

    saved = {}

    def fake_save(entity):
        saved["entity"] = entity
        return True

    repo.save = fake_save

    assert repo.soft_delete_by_id("123") is True
    assert saved["entity"].deleted_at is not None
    assert saved["entity"].updated_at is not None


def test_list_by_entity_type_filters_and_skips_invalid(mocker):
    # prepare items: one good, one bad
    items = [
        {"PK": {"S": "ENTITY#1"}, "SK": {"S": "METADATA"}, "Name": {"S": "one"}},
        {"PK": {"S": "ENTITY#2"}, "SK": {"S": "METADATA"}, "Name": {"S": "bad"}},
    ]

    client = SimpleNamespace(query=lambda **k: {"Items": items, "Count": 2})
    repo = make_repo_with_client(client)

    out = repo.list_by_entity_type(limit=10)
    # should skip the bad item and return one entity
    assert out["count"] == 1
    assert len(out["items"]) == 1
    assert out["items"][0].id == "1"


def test_batch_get_by_ids_skips_deleted(mocker):
    items = [
        {"PK": {"S": "ENTITY#1"}, "SK": {"S": "METADATA"}, "Name": {"S": "one"}},
        {
            "PK": {"S": "ENTITY#2"},
            "SK": {"S": "METADATA"},
            "Name": {"S": "two"},
            "DeletedAt": {"S": "2020"},
        },
    ]

    def batch_get_item(RequestItems):
        return {"Responses": {"tbl": items}}

    client = SimpleNamespace(batch_get_item=batch_get_item)
    repo = make_repo_with_client(client, table_name="tbl")

    out = repo.batch_get_by_ids(["1", "2"])
    # second item is deleted and should be skipped
    assert len(out) == 1
    assert out[0].id == "1"


def test_exists_uses_get_by_id(mocker):
    repo = make_repo_with_client(SimpleNamespace())
    repo.get_by_id = lambda x: object()
    assert repo.exists("1") is True
    repo.get_by_id = lambda x: None
    assert repo.exists("1") is False


def test_list_by_entity_type_with_pagination_and_search(mocker):
    # Prepare items more than requested limit and include a bad item
    items = [
        {"PK": {"S": "ENTITY#1"}, "SK": {"S": "METADATA"}, "Name": {"S": "one"}},
        {"PK": {"S": "ENTITY#2"}, "SK": {"S": "METADATA"}, "Name": {"S": "two"}},
        {"PK": {"S": "ENTITY#3"}, "SK": {"S": "METADATA"}, "Name": {"S": "bad"}},
    ]

    def query(**k):
        return {
            "Items": items,
            "Count": 3,
            "LastEvaluatedKey": {"PK": {"S": "ENTITY#3"}},
        }

    client = SimpleNamespace(query=query)
    repo = make_repo_with_client(client)

    out = repo.list_by_entity_type(limit=1, search=None)
    # Should return only one valid entity and include last_evaluated_key from response
    assert out["count"] == 1
    assert len(out["items"]) == 1
    assert out["last_evaluated_key"] == {"PK": {"S": "ENTITY#3"}}


def test_batch_get_by_ids_batches_and_handles_parse_errors(mocker):
    # Create 150 ids to force batching (100 + 50)
    ids = [str(i) for i in range(1, 151)]

    # Prepare responses per batch: first batch returns two valid items, second returns one bad and one valid
    def batch_get_item(RequestItems):
        keys = RequestItems.get("tbl", {}).get("Keys", [])
        # decide which batch based on key content
        first_pk = keys[0]["PK"]["S"]
        if first_pk.endswith("#1"):
            # simulate many items returned for first batch
            resp_items = [
                {
                    "PK": {"S": "ENTITY#1"},
                    "SK": {"S": "METADATA"},
                    "Name": {"S": "one"},
                },
                {
                    "PK": {"S": "ENTITY#2"},
                    "SK": {"S": "METADATA"},
                    "Name": {"S": "two"},
                },
            ]
        else:
            resp_items = [
                {
                    "PK": {"S": "ENTITY#3"},
                    "SK": {"S": "METADATA"},
                    "Name": {"S": "bad"},
                },
                {
                    "PK": {"S": "ENTITY#4"},
                    "SK": {"S": "METADATA"},
                    "Name": {"S": "four"},
                },
            ]
        return {"Responses": {"tbl": resp_items}}

    client = SimpleNamespace(batch_get_item=batch_get_item)
    repo = make_repo_with_client(client, table_name="tbl")

    out = repo.batch_get_by_ids(ids)
    # Should include parsed valid items and skip the 'bad' one
    ids_out = [e.id for e in out]
    assert "1" in ids_out
    assert "2" in ids_out
    assert "4" in ids_out
    assert "3" not in ids_out


def test_get_by_id_including_deleted_handles_exceptions(mocker):
    def bad_get_item(**k):
        raise Exception("dynamodb down")

    client = SimpleNamespace(get_item=bad_get_item)
    repo = make_repo_with_client(client)

    assert repo.get_by_id_including_deleted("1") is None


def test_get_by_id_handles_dynamodb_exception(mocker):
    def bad_get_item(**k):
        raise Exception("boom")

    client = SimpleNamespace(get_item=bad_get_item)
    repo = make_repo_with_client(client)

    # get_by_id should catch exceptions and return None
    assert repo.get_by_id("1") is None


def test_delete_by_id_success_and_failure(mocker):
    client = SimpleNamespace(delete_item=lambda **k: None)
    repo = make_repo_with_client(client)
    assert repo.delete_by_id("1") is True

    def bad_delete(**k):
        raise Exception("nope")

    client2 = SimpleNamespace(delete_item=bad_delete)
    repo2 = make_repo_with_client(client2)
    assert repo2.delete_by_id("1") is False


def test_soft_delete_when_entity_missing_or_no_attr(mocker):
    # Case: get_by_id_including_deleted returns None
    repo = make_repo_with_client(SimpleNamespace())
    repo.get_by_id_including_deleted = lambda _id: None
    assert repo.soft_delete_by_id("1") is False

    # Case: entity returned but has no deleted_at attribute
    class NoDeleted:
        pass

    repo2 = make_repo_with_client(SimpleNamespace())
    repo2.get_by_id_including_deleted = lambda _id: NoDeleted()
    assert repo2.soft_delete_by_id("1") is False


def test_get_by_id_including_deleted_validation_raises():
    repo = make_repo_with_client(SimpleNamespace())
    with pytest.raises(ValueError):
        repo.get_by_id_including_deleted(None)
    with pytest.raises(ValueError):
        repo.get_by_id_including_deleted("..\\etc")


def test_list_by_entity_type_handles_query_exception(mocker):
    def bad_query(**k):
        raise Exception("boom")

    client = SimpleNamespace(query=bad_query)
    repo = make_repo_with_client(client)

    out = repo.list_by_entity_type()
    assert out == {"items": [], "last_evaluated_key": None, "count": 0}


def test_batch_get_by_ids_handles_batch_exception(mocker):
    client = SimpleNamespace(
        batch_get_item=lambda **k: (_ for _ in ()).throw(Exception("boom"))
    )
    repo = make_repo_with_client(client, table_name="tbl")
    out = repo.batch_get_by_ids(["1", "2"])
    assert out == []


def test_list_by_entity_type_builds_search_and_filters(mocker):
    captured = {}

    def query(**k):
        # capture the query params passed to dynamodb
        captured.update(k)
        # return a single valid item
        return {
            "Items": [
                {"PK": {"S": "ENTITY#1"}, "SK": {"S": "METADATA"}, "Name": {"S": "one"}}
            ],
            "Count": 1,
        }

    client = SimpleNamespace(query=query)
    repo = make_repo_with_client(client)

    out = repo.list_by_entity_type(
        limit=5,
        search="foo",
        sort_by="created_at",
        sort_order="asc",
        include_deleted=False,
    )

    # verify we got one item
    assert out["count"] == 1

    # verify query params include deletion filter and search filter
    assert "FilterExpression" in captured
    assert (
        "DeletedAt" in captured["FilterExpression"]
        or "attribute_not_exists(DeletedAt)" in captured["FilterExpression"]
    )
    # search adds contains(#name, :search)
    assert "contains(#name, :search)" in captured["FilterExpression"]
    # ExpressionAttributeNames should map #name to Name
    assert captured.get("ExpressionAttributeNames", {}).get("#name") == "Name"
    # ExpressionAttributeValues should include :search
    assert (
        captured.get("ExpressionAttributeValues", {}).get(":search", {}).get("S")
        == "foo"
    )
    # Limit should be min(limit*3, 100) => 15
    assert captured.get("Limit") == 15
    # ScanIndexForward should be True because sort_order=asc
    assert captured.get("ScanIndexForward") is True


def test_list_by_entity_type_include_deleted_true_no_deletion_filter(mocker):
    captured = {}

    def query(**k):
        captured.update(k)
        return {"Items": [], "Count": 0}

    client = SimpleNamespace(query=query)
    repo = make_repo_with_client(client)

    out = repo.list_by_entity_type(
        limit=2, search=None, sort_order="desc", include_deleted=True
    )

    # No deletion FilterExpression when include_deleted=True
    fe = captured.get("FilterExpression")
    if fe:
        assert "DeletedAt" not in fe

    # ScanIndexForward should be False for desc
    assert captured.get("ScanIndexForward") is False
