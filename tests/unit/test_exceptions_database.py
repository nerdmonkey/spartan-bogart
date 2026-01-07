def test_database_internal_error_can_be_raised_and_caught():
    from app.exceptions.database import DatabaseInternalError

    try:
        raise DatabaseInternalError("fail")
    except DatabaseInternalError as e:
        assert str(e) == "fail"
