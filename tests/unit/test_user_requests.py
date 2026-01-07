import pytest
from pydantic import ValidationError

from app.requests.user import UserCreateRequest, UserUpdateRequest


def test_user_create_valid():
    req = UserCreateRequest(username="alice", email="alice@example.com", password="pw")
    assert req.username == "alice"
    assert req.email == "alice@example.com"
    assert req.password == "pw"


def test_user_create_invalid_username():
    with pytest.raises(ValidationError):
        UserCreateRequest(username="", email="a@b.com", password="pw")
    with pytest.raises(ValidationError):
        UserCreateRequest(username="ab", email="a@b.com", password="pw")
    with pytest.raises(ValidationError):
        UserCreateRequest(username="x" * 51, email="a@b.com", password="pw")


def test_user_create_invalid_email():
    with pytest.raises(ValidationError):
        UserCreateRequest(username="alice", email="", password="pw")


def test_user_update_valid():
    req = UserUpdateRequest(username="bob", email="bob@example.com", password="pw")
    assert req.username == "bob"
    assert req.email == "bob@example.com"
    assert req.password == "pw"


def test_user_update_optional_fields():
    req = UserUpdateRequest()
    assert req.username is None
    assert req.email is None
    assert req.password is None


def test_user_update_invalid_username():
    with pytest.raises(ValidationError):
        UserUpdateRequest(username="ab")
    with pytest.raises(ValidationError):
        UserUpdateRequest(username="x" * 21)
    with pytest.raises(ValidationError):
        UserUpdateRequest(username="   ")


def test_user_update_invalid_email():
    with pytest.raises(ValidationError):
        UserUpdateRequest(email="")
