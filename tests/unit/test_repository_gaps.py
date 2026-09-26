import importlib.util
import os
from pathlib import Path
from types import SimpleNamespace


os.environ.setdefault("APP_ENVIRONMENT", "test")

base_path = Path(__file__).resolve().parents[2] / "app" / "repositories" / "base.py"
spec = importlib.util.spec_from_file_location("app_repositories_base_gaps", str(base_path))
base_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base_mod)
BaseRepository = base_mod.BaseRepository


class FakeModel:
    def __init__(self, id, name, deleted_at=None):
        self.id = id
        self.name = name
        self.deleted_at = deleted_at

    @classmethod
    def from_ddb_item(cls, item):
        pk = item.get("PK", {}).get("S", "")
        _, id = pk.split("#", 1)
        name = item.get("Name", {}).get("S")
        return cls(id=id, name=name)

    def to_ddb_item(self):
        return {"PK": {"S": f"ENTITY#{self.id}"}, "SK": {"S": "METADATA"}}


class RepoImpl(BaseRepository):
    def get_model_class(self):
        return FakeModel

    def get_entity_type(self):
        return "ENTITY"


def make_repo(client, table_name="tbl"):
    repo = RepoImpl()
    repo.dynamodb = client
    repo.table_name = table_name
    return repo


def test_get_by_id_returns_none_when_item_missing():
    repo = make_repo(SimpleNamespace(get_item=lambda **k: {}))
    assert repo.get_by_id("123") is None


def test_get_by_id_including_deleted_returns_none_when_item_missing():
    repo = make_repo(SimpleNamespace(get_item=lambda **k: {}))
    assert repo.get_by_id_including_deleted("123") is None


def test_get_by_id_including_deleted_returns_entity_when_found():
    item = {"PK": {"S": "ENTITY#5"}, "SK": {"S": "METADATA"}, "Name": {"S": "n"}}
    repo = make_repo(SimpleNamespace(get_item=lambda **k: {"Item": item}))
    entity = repo.get_by_id_including_deleted("5")
    assert entity is not None
    assert entity.id == "5"


def test_list_by_entity_type_forwards_last_evaluated_key():
    captured = {}

    def query(**k):
        captured.update(k)
        return {"Items": [], "Count": 0}

    repo = make_repo(SimpleNamespace(query=query))
    repo.list_by_entity_type(last_evaluated_key={"PK": {"S": "ENTITY#1"}})

    assert captured.get("ExclusiveStartKey") == {"PK": {"S": "ENTITY#1"}}


def test_batch_get_by_ids_empty_list_returns_empty():
    repo = make_repo(SimpleNamespace())
    assert repo.batch_get_by_ids([]) == []
