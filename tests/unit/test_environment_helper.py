from app.helpers.environment import EnvironmentVariables


BASE_KWARGS = dict(
    APP_NAME="svc",
    APP_ENVIRONMENT="test",
    APP_DEBUG=False,
    ALLOWED_ORIGINS="*",
    LOG_LEVEL="INFO",
    LOG_CHANNEL="file",
    LOG_DIR="storage/logs",
    DB_TYPE="sqlite",
    DB_DRIVER="",
    DB_HOST="localhost",
    DB_NAME="db",
    DB_USERNAME="user",
    DB_PASSWORD="pw",
    DDB_TYPE="local",
    DDB_TABLE_NAME="Table",
)


def test_db_ssl_verify_cert_true_string_variants():
    for value in ("true", "1", "yes", "TRUE", "Yes"):
        settings = EnvironmentVariables(**BASE_KWARGS, DB_SSL_VERIFY_CERT=value)
        assert settings.DB_SSL_VERIFY_CERT is True


def test_db_ssl_verify_cert_false_string_variants():
    for value in ("false", "0", "no", "FALSE", "No"):
        settings = EnvironmentVariables(**BASE_KWARGS, DB_SSL_VERIFY_CERT=value)
        assert settings.DB_SSL_VERIFY_CERT is False


def test_db_ssl_verify_cert_unrecognized_string_becomes_none():
    settings = EnvironmentVariables(**BASE_KWARGS, DB_SSL_VERIFY_CERT="maybe")
    assert settings.DB_SSL_VERIFY_CERT is None


def test_db_ssl_verify_cert_none_stays_none():
    settings = EnvironmentVariables(**BASE_KWARGS, DB_SSL_VERIFY_CERT=None)
    assert settings.DB_SSL_VERIFY_CERT is None


def test_db_ssl_verify_cert_empty_string_becomes_none():
    settings = EnvironmentVariables(**BASE_KWARGS, DB_SSL_VERIFY_CERT="")
    assert settings.DB_SSL_VERIFY_CERT is None


def test_db_ssl_verify_cert_non_string_truthy_coerced_to_bool():
    settings = EnvironmentVariables(**BASE_KWARGS, DB_SSL_VERIFY_CERT=1)
    assert settings.DB_SSL_VERIFY_CERT is True

    settings2 = EnvironmentVariables(**BASE_KWARGS, DB_SSL_VERIFY_CERT=0)
    assert settings2.DB_SSL_VERIFY_CERT is False
