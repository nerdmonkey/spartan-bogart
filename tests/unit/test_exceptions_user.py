import pytest

from app.exceptions.user import (
    DuplicateUserError,
    InternalServerErrorException,
    InvalidSortFieldException,
    InvalidSortTypeException,
    UnauthorizedException,
    UserNotFoundException,
)


def test_user_not_found_exception():
    with pytest.raises(UserNotFoundException) as exc:
        raise UserNotFoundException()
    assert str(exc.value) == "User not found"
    e = UserNotFoundException("custom")
    assert str(e) == "custom"


def test_duplicate_user_error():
    e = DuplicateUserError()
    assert isinstance(e, DuplicateUserError)


def test_internal_server_error_exception():
    with pytest.raises(InternalServerErrorException) as exc:
        raise InternalServerErrorException()
    assert str(exc.value) == "Internal server error"
    e = InternalServerErrorException("custom")
    assert str(e) == "custom"


def test_unauthorized_exception():
    with pytest.raises(UnauthorizedException) as exc:
        raise UnauthorizedException()
    assert str(exc.value) == "Unauthorized access"
    e = UnauthorizedException("custom")
    assert str(e) == "custom"


def test_invalid_sort_field_exception():
    with pytest.raises(InvalidSortFieldException) as exc:
        raise InvalidSortFieldException()
    assert str(exc.value) == "Invalid sort field"
    e = InvalidSortFieldException("custom")
    assert str(e) == "custom"


def test_invalid_sort_type_exception():
    with pytest.raises(InvalidSortTypeException) as exc:
        raise InvalidSortTypeException()
    assert str(exc.value) == "Invalid sort type"
    e = InvalidSortTypeException("custom")
    assert str(e) == "custom"
