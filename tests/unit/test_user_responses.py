from app.responses.user import (
    PaginatedUserResponse,
    Pagination,
    ProfileResponse,
    SingleUserResponse,
    UserCreateResponse,
    UserResponse,
    UserUpdateResponse,
)


def test_profile_response_optional():
    pr = ProfileResponse(given_name="A", family_name="B")
    assert pr.given_name == "A"
    assert pr.family_name == "B"
    pr2 = ProfileResponse()
    assert pr2.given_name is None
    assert pr2.family_name is None


def test_user_response_id_conversion():
    ur = UserResponse(id=123, username="u", email="e")
    assert ur.id == "123"
    ur2 = UserResponse(id="abc", username="u", email="e")
    assert ur2.id == "abc"


def test_single_user_response():
    ur = UserResponse(id=1, username="u", email="e")
    resp = SingleUserResponse(data=ur, status_code=200)
    assert resp.data.username == "u"
    assert resp.status_code == 200


def test_pagination_and_paginated_user_response():
    pag = Pagination(
        current_page=1,
        last_page=2,
        first_item=1,
        last_item=10,
        items_per_page=10,
        total=20,
    )
    ur = UserResponse(id=1, username="u", email="e")
    resp = PaginatedUserResponse(data=[ur], meta=pag, status_code=200)
    assert resp.data[0].username == "u"
    assert resp.meta.total == 20
    assert resp.status_code == 200


def test_user_create_update_response():
    cr = UserCreateResponse(
        id=1, username="u", email="e", created_at="now", updated_at="now"
    )
    assert cr.id == 1
    assert cr.username == "u"
    assert cr.email == "e"
    ur = UserUpdateResponse(
        id=2, username="u2", email="e2", created_at="now", updated_at="now"
    )
    assert ur.id == 2
    assert ur.username == "u2"
    assert ur.email == "e2"
