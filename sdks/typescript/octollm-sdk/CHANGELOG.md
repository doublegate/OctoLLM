# Changelog

All notable changes to the OctoLLM TypeScript SDK will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.4.0] - 2025-11-11

### Added - Sprint 0.5: Complete TypeScript SDK Implementation

#### Core Infrastructure
- **BaseClient**: HTTP client with automatic retry logic using axios-retry
  - Exponential backoff strategy (2^attempt seconds)
  - Configurable timeout, max retries, SSL verification
  - Request counting and tracking
  - Comprehensive error handling with typed exceptions

#### Service Clients (8 total)
- **OrchestratorClient** (port 8000): Task submission, status tracking, arm management
- **ReflexClient** (port 8001): Fast preprocessing with caching
- **PlannerClient** (port 8002): Task decomposition into subtasks
- **ExecutorClient** (port 8003): Sandboxed command execution
- **RetrieverClient** (port 8004): Semantic + full-text hybrid search
- **CoderClient** (port 8005): Code generation, debugging, refactoring
- **JudgeClient** (port 8006): Output validation against criteria
- **SafetyClient** (port 8007): PII detection and content filtering

#### Type Definitions
- 50+ TypeScript interfaces for all API request/response models
- Strongly-typed enums for task status, processing steps, PII types
- Complete JSON schema support
- Full IntelliSense and autocomplete support

#### Authentication
- API key authentication (X-API-Key header)
- Bearer token authentication (Authorization header)
- Environment variable support (OCTOLLM_API_KEY, OCTOLLM_BEARER_TOKEN)
- Helper functions for credential management

#### Error Handling
- 9 custom exception classes:
  - `OctoLLMError` (base)
  - `AuthenticationError`, `AuthorizationError`
  - `ValidationError`, `NotFoundError`
  - `RateLimitError`, `ServiceUnavailableError`
  - `TimeoutError`, `APIError`
- Error metadata: status code, error code, request ID, details
- Automatic retry on rate limits (respects Retry-After header)

#### Examples
- `basicUsage.ts`: Task submission and polling (150 lines)
- `multiServiceUsage.ts`: Multi-arm workflow demonstration (200 lines)
- `errorHandling.ts`: Comprehensive error handling patterns (180 lines)

#### Testing
- Jest configuration with TypeScript support
- Unit tests for BaseClient, auth helpers, and exceptions
- 80% coverage thresholds configured
- Test structure ready for expansion

#### Documentation
- Comprehensive README.md with:
  - Quick start guide
  - Authentication methods
  - All service client examples
  - Error handling patterns
  - Configuration options
  - TypeScript usage examples
- Inline JSDoc comments on all public methods
- Type annotations for IDE support

#### Development Tools
- TypeScript 5.3 configuration
- ESLint with TypeScript plugin
- Prettier formatting
- Jest testing framework
- npm scripts for build, test, lint, format

#### Package Configuration
- npm package.json with proper metadata
- Apache 2.0 LICENSE
- .npmignore for clean package distribution
- .gitignore for development artifacts

### Statistics
- **Total Files**: 24
- **Total Lines**: ~2,066 lines of TypeScript code
- **Service Clients**: 8
- **Type Definitions**: 50+
- **Examples**: 3
- **Tests**: 3 test suites

### Dependencies
- axios ^1.6.0 (HTTP client)
- axios-retry ^4.0.0 (automatic retry logic)

### Dev Dependencies
- typescript ^5.3.0
- jest ^29.5.0
- ts-jest ^29.1.0
- eslint ^8.0.0
- prettier ^3.0.0

## [Unreleased]

### Planned
- Additional integration tests
- Mock server for testing
- More comprehensive examples
- Performance benchmarks
- API client generation from OpenAPI specs
- WebSocket support for real-time updates
