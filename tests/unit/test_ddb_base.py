from datetime import datetime

from app.models.ddb.ddb_base import DDBModel


class DummyDDBModel(DDBModel):
    name: str
    age: int
    active: bool
    created: datetime
    tags: list
    meta: dict

    def pk(self) -> str:
        return f"USER#{self.name}"

    def sk(self) -> str:
        return f"PROFILE#{self.name}"

    @classmethod
    def from_ddb_item(cls, item):
        # Minimal implementation for test
        return cls(
            name=item["name"]["S"],
            age=int(item["age"]["N"]),
            active=item["active"]["BOOL"],
            created=datetime.fromisoformat(item["created"]["S"]),
            tags=[v["S"] for v in item["tags"]["L"]],
            meta={k: v["S"] for k, v in item["meta"]["M"].items()},
        )


def test_to_ddb_item():
    model = DummyDDBModel(
        name="alice",
        age=30,
        active=True,
        created=datetime(2025, 11, 23, 12, 0, 0),
        tags=["admin", "user"],
        meta={"role": "admin", "level": "5"},
    )
    item = model.to_ddb_item()
    assert item["PK"] == {"S": "USER#alice"}
    assert item["SK"] == {"S": "PROFILE#alice"}
    assert item["name"] == {"S": "alice"}
    assert item["age"] == {"N": "30"}
    assert item["active"] == {"BOOL": True}
    assert item["created"] == {"S": "2025-11-23T12:00:00"}
    assert item["tags"] == {"L": [{"S": "admin"}, {"S": "user"}]}
    assert item["meta"] == {"M": {"role": {"S": "admin"}, "level": {"S": "5"}}}


def test_from_ddb_item():
    item = {
        "name": {"S": "bob"},
        "age": {"N": "42"},
        "active": {"BOOL": False},
        "created": {"S": "2025-11-23T13:00:00"},
        "tags": {"L": [{"S": "dev"}, {"S": "ops"}]},
        "meta": {"M": {"team": {"S": "devops"}, "rank": {"S": "senior"}}},
    }
    model = DummyDDBModel.from_ddb_item(item)
    assert model.name == "bob"
    assert model.age == 42
    assert model.active is False
    assert model.created == datetime(2025, 11, 23, 13, 0, 0)
    assert model.tags == ["dev", "ops"]
    assert model.meta == {"team": "devops", "rank": "senior"}


def test_get_entity_type():
    model = DummyDDBModel(
        name="alice",
        age=30,
        active=True,
        created=datetime(2025, 11, 23, 12, 0, 0),
        tags=[],
        meta={},
    )
    assert model.get_entity_type() == "DUMMYDDBMODEL"
