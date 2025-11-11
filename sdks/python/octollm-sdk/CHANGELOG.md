# Changelog

All notable changes to the OctoLLM Python SDK will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.4.0] - 2025-11-11

### Added
- **Complete SDK Implementation**: Full implementation of all 8 service clients
  - `OrchestratorClient`: Central brain for task coordination
  - `ReflexClient`: Fast preprocessing and cache management
  - `PlannerClient`: Task decomposition and planning
  - `ExecutorClient`: Sandboxed command execution
  - `RetrieverClient`: Knowledge base search
  - `CoderClient`: Code generation and debugging
  - `JudgeClient`: Output validation
  - `SafetyGuardianClient`: PII detection and content filtering

- **Comprehensive Models**: 29+ Pydantic models for type-safe API interactions
  - All request/response models match OpenAPI 3.0 specifications
  - Full validation with field constraints
  - Clear documentation for all fields

- **Robust HTTP Client**: Base client with advanced features
  - Automatic retry with exponential backoff
  - Request ID tracking for distributed tracing
  - Timeout configuration (per-request and global)
  - Custom exception hierarchy for clear error handling

- **Authentication Support**
  - API key authentication (X-API-Key header)
  - Bearer token authentication (JWT)
  - Environment variable configuration
  - Configuration object with `OctoLLMConfig`

- **Examples**: 4 comprehensive example files
  - `basic_usage.py`: Simple task submission and polling
  - `async_usage.py`: Concurrent task execution
  - `error_handling.py`: Comprehensive error handling patterns
  - `authentication.py`: All authentication methods

- **Documentation**
  - Comprehensive docstrings for all classes and methods
  - Type hints throughout codebase
  - README with quick start and usage guide

### Changed
- Updated version from 0.3.0 to 0.4.0
- Enhanced `__init__.py` to export all service clients and models
- Improved error messages with request ID tracking

## [0.3.0] - 2025-11-11

### Added
- Initial SDK skeleton
- Basic package structure
- Project configuration (pyproject.toml)
- Development dependencies

## [0.2.0] - 2025-11-10

### Added
- Project initialization
- Repository structure

## [0.1.0] - 2025-11-10

### Added
- Initial project concept
