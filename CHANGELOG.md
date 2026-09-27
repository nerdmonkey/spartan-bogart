# Changelog

All notable changes to `spartan` will be documented in this file.

## [Unreleased]

### Added
- Nothing yet.

## [0.2.0] - 2026-09-27

### Added
- Added `set_level` method to `StandardLoggerService` for dynamic log level changes.
- Added `get_logger` method to `StandardLoggerService` for accessing the underlying logger instance.
- Improved docstrings and maintainability in `StandardLoggerService`.
- Added `docs/examples/pii-logging-demo.py` — standalone demo of PII redaction, environment
  metadata, and log sampling, moved out of the starter handler.

### Changed
- Refactored `StandardLoggerService` to better align with helpers.logger structure and Python logging best practices.
- Regenerated `requirements.txt` and `requirements-dev.txt` from the poetry lockfile — fixes missing
  `jsonpickle` and `pytest-xdist`, and a stale `moto` pin below the `pyproject.toml` constraint. (#6, #7)
- Simplified `handlers/inference.py` to a minimal starter handler; its PII/sampling demo logging moved
  to `docs/examples/pii-logging-demo.py`.

## [2025-06-08]
### Added
- Enhanced logging methods with docstrings for improved clarity and documentation. ([44b92ff])
- Implemented `Secret`, `AppSettings`, `DatabaseSettings`, and `LogSettings` classes for loading secrets and dynamic configuration. ([620c738])

### Changed
- Updated boto, boto3, botocore, and s3transfer versions for improved compatibility and features. ([ea68512])
- Updated `test_log_levels` to use `stacklevel` parameter for improved logging accuracy. ([6fae1f7])
- Enhanced logging functionality: added `stacklevel` parameter to log methods for improved traceability and updated response body in main function to reflect correct service name. ([77c91e3])
- Removed Python version constraints from requirements.txt for improved compatibility. ([f42fd9e])
- Refactored environment variable function and updated logger initialization: formatted the env function parameters for better readability and changed logger name in inference handler to match the service. ([77e7bf7])
- Updated environment variables and logger configuration: changed LOG_FILE to LOG_DIR in .env.example, and modified FileLogger to use LOG_DIR from environment settings. ([fbd54e4])
- Refactored logger imports and formatting: streamlined import statements, adjusted timestamp handling in FileLogger, and improved code readability in various modules. ([e9755a5])
- Enhanced logging functionality: added extra data handling in BothLogger and StreamLogger, updated inference handler logging messages, and improved error handling in main function. ([ef73954])
- Refactored logging setup: removed environment parameter, implemented BothLogger and StreamLogger, and replaced predict handler with inference handler. ([de7155c])

## [2025-06-09]
### Added
- Add unit tests for BothLogger and StreamLogger with mock implementations. ([a9d0a3f] by Sydel Palinlin)
