
# Changelog

All notable changes to `spartan` will be documented in this file.

## [Unreleased]
### Added
- Enhance configuration and infrastructure setup for Spartan Framework.
- Add comprehensive unit tests for code formatting and linting validation.
- Add comprehensive tests for parameter management and secret resolution.
- Add unit tests for Parameter Manager requests, responses, and service.
- Add comprehensive logging tests for Secret Manager service operations.
- Add comprehensive property and unit tests for models.
- Add Cloud Tasks and Secret Manager services with comprehensive request/response models.
- Add Dockerfile and .dockerignore for containerized deployment.

### Changed
- Align code formatting and update dependencies for code standards compliance.
- Refactor code structure for improved readability and maintainability; removed redundant code blocks and optimized function calls to enhance performance; updated documentation to reflect changes and ensure clarity for future development.
- Refactor test cases for improved readability and consistency.
- Clean up whitespace, remove property tests, and optimize pytest configuration.

### Fixed
- Update archive file inclusion to add pyproject.toml and poetry.lock; retain CHANGELOG.md.
- Remove CHANGELOG.md from .gcloudignore.
- Reorganize entries for clarity and consistency in .dockerignore; ensure all relevant file types are excluded.
- Correct indentation in metadata label entries for consistency in Dockerfile.

### Refactored
- Improve code readability by reformatting method signatures and exception handling; align with code standards in secret-manager.
- Enhance exception mapping by consolidating logic into grouped methods in parameter-manager.
- Simplify exception mapping by consolidating logic into dedicated methods in parameter-manager.
- Improve string formatting for parameter paths in parameter-manager.
- Enhance service documentation, improve credential handling, and restructure initialization logic in parameter-manager.
- Clean up whitespace and improve code readability in SecretManagerService.
- Enhance service documentation, improve credential handling, and restructure initialization logic in parameter-manager.
- Remove unused import of MockCloudFunctionsContext in local testing entry point.

### Docs
- Mark final checkpoint task as complete in parameter-manager documentation.

### Test
- Add comprehensive initialization and coverage tests for parameter-manager.
- Add comprehensive property tests for version management preservation and state management in secret-manager.
- Add comprehensive property and unit tests for models in secret-manager.
- Simplify version state management property test in secret-manager.

### Feat
- Add utility methods and format conversion helpers in parameter-manager.
- Add connection pooling and batch operation statistics in parameter-manager.
- Enhance error handling and logging in ParameterManagerService.
- Implement version management methods with custom version naming in parameter-manager.
- Implement comprehensive logging and observability with operation timing in secret-manager.
- Add comprehensive error handling with exception mapping and property tests in secret-manager.
- Implement secret listing and deletion methods with comprehensive error handling; add property test for secret listing completeness in secret-manager.
- Implement version management methods with comprehensive error handling and logging; add property tests for version management preservation and state management in secret-manager.
- Implement core SecretManagerService class with initialization, secret creation, and retrieval methods; add comprehensive property tests for validation.

### Perf
- Add connection pooling and batch operation statistics in parameter-manager.

### Chore
- Align code formatting and update dependencies for code standards compliance.
