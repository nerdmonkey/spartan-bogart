import sys
import types
from datetime import datetime

import pytest

from app.exceptions.user import (
    DuplicateUserError,
    InvalidSortFieldException,
    UserNotFoundException,
)
from app.requests.user import UserCreateRequest, UserUpdateRequest
from app.services.user import UserService


class Field:
    def in_(self, values):
        return ("in", self.name, values)

    def __init__(self, name):
        self.name = name

    def __eq__(self, other):
        return (self.name, other)


class FakeUser:
    id = Field("id")
    username = Field("username")
    email = Field("email")
    password = Field("password")
    created_at = Field("created_at")
    updated_at = Field("updated_at")

    def __init__(
        self, username, email, password, created_at=None, updated_at=None, id=None
    ):
        self.id = id
        self.username = username
        self.email = email
        self.password = password
        self.created_at = created_at or datetime(2024, 1, 1, 0, 0, 0)
        self.updated_at = updated_at or datetime(2024, 1, 1, 0, 0, 0)


# Patch app.models.user before importing UserService
fake_user_mod = types.ModuleType("app.models.user")
fake_user_mod.User = FakeUser
sys.modules["app.models.user"] = fake_user_mod


class FakeQuery:
    def __init__(self, users):
        self.users = users
        self._filters = []
        self._order_by = None
        self._offset = 0
        self._limit = None

    def filter(self, cond):
        # Support equality and in_ conditions
        if isinstance(cond, tuple):
            if len(cond) == 2:
                key, value = cond
                self.users = [u for u in self.users if getattr(u, key, None) == value]
            elif len(cond) == 3 and cond[0] == "in":
                _, key, values = cond
                self.users = [u for u in self.users if getattr(u, key, None) in values]
        return self

    def order_by(self, order):
        # If order is a Field, sort by its name
        if hasattr(order, "name"):
            key = order.name
            self.users = sorted(self.users, key=lambda u: getattr(u, key))
        self._order_by = order
        return self

    def offset(self, offset):
        self._offset = offset
        return self

    def limit(self, limit):
        self._limit = limit
        return self

    def all(self):
        users = self.users
        if self._order_by:
            key = getattr(self._order_by, "name", None)
            reverse = getattr(self._order_by, "reverse", False)
            if key:
                users = sorted(users, key=lambda u: getattr(u, key), reverse=reverse)
        if self._offset:
            users = users[self._offset :]
        if self._limit is not None:
            users = users[: self._limit]
        return users

    def count(self):
        return len(self.users)

    def first(self):
        return self.users[0] if self.users else None

    def filter_by(self, **kwargs):
        for k, v in kwargs.items():
            self.users = [u for u in self.users if getattr(u, k) == v]
        return self

    def in_(self, ids):
        self.users = [u for u in self.users if u.id in ids]
        return self


class FakeSession:
    def __init__(self):
        self.users = []
        self.last_id = 0

    def query(self, model):
        return FakeQuery(list(self.users))

    def add(self, user):
        self.last_id += 1
        user.id = self.last_id
        self.users.append(user)

    def commit(self):
        pass

    def refresh(self, user):
        pass

    def delete(self, user):
        self.users = [u for u in self.users if u.id != user.id]


@pytest.fixture(scope="function")
def user_service(monkeypatch):
    # Patch User in app.services.user to use FakeUser
    import app.services.user as user_mod

    monkeypatch.setattr(user_mod, "User", FakeUser)
    # Monkeypatch asc/desc to return the Field object directly
    import sqlalchemy as sa
    import sqlalchemy.sql.expression as expr

    import app.services.user as user_mod

    monkeypatch.setattr(expr, "asc", lambda col: col)
    monkeypatch.setattr(expr, "desc", lambda col: col)
    monkeypatch.setattr(sa, "asc", lambda col: col)
    monkeypatch.setattr(sa, "desc", lambda col: col)
    monkeypatch.setattr(user_mod, "asc", lambda col: col)
    monkeypatch.setattr(user_mod, "desc", lambda col: col)
    return UserService(FakeSession())


@pytest.fixture
def create_user(user_service):
    req = UserCreateRequest(username="alice", email="alice@example.com", password="pw")
    return user_service.save(req)


def test_save_and_get_by_id(user_service):
    resp = user_service.save(
        UserCreateRequest(username="bob", email="bob@example.com", password="pw")
    )
    user = user_service.get_by_id(resp.id)
    assert user.username == "bob"
    assert user.email == "bob@example.com"


def test_save_duplicate_email(user_service):
    user_service.save(
        UserCreateRequest(username="bob", email="bob@example.com", password="pw")
    )
    with pytest.raises(DuplicateUserError):
        user_service.save(
            UserCreateRequest(username="bob2", email="bob@example.com", password="pw")
        )


def test_update_user(user_service):
    resp = user_service.save(
        UserCreateRequest(username="bob", email="bob@example.com", password="pw")
    )
    updated = user_service.update(resp.id, UserUpdateRequest(username="bobby"))
    assert updated.username == "bobby"


def test_update_user_not_found(user_service):
    with pytest.raises(UserNotFoundException):
        user_service.update(999, UserUpdateRequest(username="notfound"))


def test_delete_user(user_service):
    resp = user_service.save(
        UserCreateRequest(username="bob", email="bob@example.com", password="pw")
    )
    deleted = user_service.delete(resp.id)
    assert deleted.username == "bob"
    with pytest.raises(UserNotFoundException):
        user_service.get_by_id(resp.id)


def test_find_user(user_service):
    resp = user_service.save(
        UserCreateRequest(username="bob", email="bob@example.com", password="pw")
    )
    found = user_service.find(resp.id)
    assert found.username == "bob"


def test_bulk_delete(user_service):
    # Reset session before test
    user_service.db.users.clear()
    user_service.db.last_id = 0
    ids = []
    for i in range(3):
        resp = user_service.save(
            UserCreateRequest(
                username=f"user_bulk_{i}", email=f"bulk_{i}@x.com", password="pw"
            )
        )
        ids.append(resp.id)
    deleted = user_service.bulk_delete(ids)
    assert set(deleted) == set(ids)
    assert user_service.total() == 0
    with pytest.raises(UserNotFoundException):
        user_service.bulk_delete([999])


def test_all_and_total(user_service):
    # Reset session before test
    user_service.db.users.clear()
    user_service.db.last_id = 0
    for i in range(5):
        user_service.save(
            UserCreateRequest(
                username=f"user_total_{i}", email=f"total_{i}@x.com", password="pw"
            )
        )
    users, total, last_page, first_item, last_item = user_service.all(
        page=1, items_per_page=2
    )
    assert len(users) == 2
    assert total == 5
    assert last_page == 3
    assert first_item == 1
    assert last_item == 2
    assert user_service.total() == 5


def test_all_invalid_sort_field(user_service):
    user_service.save(
        UserCreateRequest(username="bob", email="bob@example.com", password="pw")
    )
    with pytest.raises(InvalidSortFieldException):
        user_service.all(sort_by="notafield")
