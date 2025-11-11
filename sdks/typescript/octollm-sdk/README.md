# OctoLLM TypeScript SDK

Official TypeScript SDK for the OctoLLM distributed AI architecture.

[![npm version](https://img.shields.io/npm/v/octollm-sdk.svg)](https://www.npmjs.com/package/octollm-sdk)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

## Overview

OctoLLM is a distributed AI architecture inspired by octopus neurobiology, featuring:

- **Central Orchestrator**: Strategic planning and coordination
- **Specialized Arms**: Domain-specific execution (Planner, Executor, Retriever, Coder, Judge, Safety Guardian)
- **Reflex Layer**: Fast preprocessing and caching
- **Distributed Memory**: Global semantic + local episodic stores

This SDK provides type-safe, production-ready clients for all OctoLLM services.

## Installation

```bash
npm install octollm-sdk
```

## Quick Start

```typescript
import { OrchestratorClient } from 'octollm-sdk';

// Initialize client
const client = new OrchestratorClient({
  apiKey: process.env.OCTOLLM_API_KEY,
  baseUrl: 'http://localhost:8000'
});

// Submit a task
const response = await client.submitTask({
  goal: 'Analyze security vulnerabilities in the web application',
  budget: {
    max_tokens: 10000,
    max_time_seconds: 120,
    max_cost_dollars: 1.0
  }
});

console.log(`Task ID: ${response.task_id}`);

// Poll for completion
const status = await client.getTask(response.task_id);
console.log(`Status: ${status.status}`);
```

## Authentication

### API Key Authentication

```typescript
const client = new OrchestratorClient({
  apiKey: 'your-api-key-here'
});
```

### Bearer Token Authentication

```typescript
const client = new OrchestratorClient({
  bearerToken: 'your-bearer-token-here'
});
```

### Environment Variables

```typescript
// Set in your environment:
// OCTOLLM_API_KEY=your-key
// OCTOLLM_BEARER_TOKEN=your-token

import { getAuthFromEnv } from 'octollm-sdk';

const { apiKey, bearerToken } = getAuthFromEnv();
const client = new OrchestratorClient({ apiKey, bearerToken });
```

## Service Clients

### Orchestrator Client (Port 8000)

Central coordinator for task execution:

```typescript
import { OrchestratorClient } from 'octollm-sdk';

const client = new OrchestratorClient({ apiKey: 'your-key' });

// Submit task
const response = await client.submitTask({
  goal: 'Task description',
  constraints: ['constraint1', 'constraint2'],
  acceptance_criteria: ['criterion1', 'criterion2'],
  budget: { max_tokens: 10000 }
});

// Get task status
const status = await client.getTask(response.task_id);

// Cancel task
await client.cancelTask(response.task_id);

// List registered arms
const { arms } = await client.listArms();
```

### Reflex Client (Port 8001)

Fast preprocessing with caching:

```typescript
import { ReflexClient } from 'octollm-sdk';

const client = new ReflexClient({ apiKey: 'your-key' });

// Preprocess input
const result = await client.preprocess({
  input: 'User input text',
  context: { source: 'web' }
});

if (result.cached) {
  console.log('Using cached response');
}

// Get cache statistics
const stats = await client.getCacheStats();
console.log(`Hit rate: ${stats.hit_rate}`);
```

### Planner Client (Port 8002)

Task decomposition:

```typescript
import { PlannerClient } from 'octollm-sdk';

const client = new PlannerClient({ apiKey: 'your-key' });

const plan = await client.plan({
  goal: 'Scan network for vulnerabilities',
  constraints: ['Use only passive scanning'],
  budget: { max_tokens: 5000 }
});

plan.subtasks.forEach(subtask => {
  console.log(`${subtask.description} -> ${subtask.assigned_arm}`);
});
```

### Executor Client (Port 8003)

Sandboxed command execution:

```typescript
import { ExecutorClient } from 'octollm-sdk';

const client = new ExecutorClient({ apiKey: 'your-key' });

const result = await client.execute({
  command: 'nmap',
  args: ['-sV', '192.168.1.1'],
  timeout: 60
});

console.log(result.stdout);
console.log(`Exit code: ${result.exit_code}`);
```

### Retriever Client (Port 8004)

Semantic search:

```typescript
import { RetrieverClient } from 'octollm-sdk';

const client = new RetrieverClient({ apiKey: 'your-key' });

const results = await client.search({
  query: 'SQL injection vulnerabilities',
  top_k: 10,
  min_score: 0.7
});

results.results.forEach(result => {
  console.log(`Score ${result.score}: ${result.content}`);
});
```

### Coder Client (Port 8005)

Code generation and manipulation:

```typescript
import { CoderClient } from 'octollm-sdk';

const client = new CoderClient({ apiKey: 'your-key' });

// Generate code
const result = await client.code({
  operation: 'generate',
  prompt: 'Write a Python function to validate email addresses',
  language: 'python'
});

console.log(result.code);
console.log(result.explanation);

// Debug code
const debugResult = await client.code({
  operation: 'debug',
  code: 'def buggy_function(): ...',
  language: 'python'
});
```

### Judge Client (Port 8006)

Output validation:

```typescript
import { JudgeClient } from 'octollm-sdk';

const client = new JudgeClient({ apiKey: 'your-key' });

const result = await client.validate({
  output: 'Generated security report',
  criteria: [
    'Must identify all high-severity vulnerabilities',
    'Must include remediation steps'
  ]
});

console.log(`Passed: ${result.passed}`);
result.criteria_results.forEach(cr => {
  console.log(`${cr.criterion}: ${cr.passed ? 'PASS' : 'FAIL'}`);
});
```

### Safety Client (Port 8007)

PII detection and content filtering:

```typescript
import { SafetyClient } from 'octollm-sdk';

const client = new SafetyClient({ apiKey: 'your-key' });

const result = await client.check({
  content: 'Contact me at john@example.com or 555-1234',
  check_pii: true,
  check_harmful: true
});

if (result.pii_detected) {
  console.log('PII entities:', result.pii_entities);
  console.log('Redacted:', result.redacted_content);
}
```

## Error Handling

The SDK provides typed exceptions for all error cases:

```typescript
import {
  OrchestratorClient,
  AuthenticationError,
  ValidationError,
  RateLimitError,
  TimeoutError,
  NotFoundError
} from 'octollm-sdk';

try {
  await client.submitTask({ goal: 'Task description' });
} catch (error) {
  if (error instanceof AuthenticationError) {
    console.error('Invalid API key');
  } else if (error instanceof ValidationError) {
    console.error('Invalid input:', error.details);
  } else if (error instanceof RateLimitError) {
    console.error(`Rate limited. Retry after ${error.retryAfter}s`);
  } else if (error instanceof TimeoutError) {
    console.error('Request timed out');
  } else if (error instanceof NotFoundError) {
    console.error('Resource not found');
  }
}
```

## Configuration Options

All clients support these configuration options:

```typescript
const client = new OrchestratorClient({
  baseUrl: 'http://localhost:8000',  // Service URL
  apiKey: 'your-key',                 // API key for authentication
  bearerToken: 'your-token',          // Bearer token (alternative)
  timeout: 30000,                     // Request timeout (ms, default: 30000)
  maxRetries: 3,                      // Max retry attempts (default: 3)
  verifySsl: true                     // Verify SSL certificates (default: true)
});
```

## Retry Logic

The SDK automatically retries failed requests with exponential backoff:

- **Retry Count**: Configurable via `maxRetries` (default: 3)
- **Backoff Strategy**: 2^attempt seconds (1s, 2s, 4s, ...)
- **Retry Conditions**:
  - Network errors
  - 5xx server errors
  - Rate limit errors (respects `Retry-After` header)

## TypeScript Support

The SDK is written in TypeScript and provides complete type definitions:

```typescript
import { TaskRequest, TaskResponse, TaskStatus } from 'octollm-sdk';

const request: TaskRequest = {
  goal: 'Task description',
  budget: {
    max_tokens: 10000,
    max_time_seconds: 120,
    max_cost_dollars: 1.0
  }
};

const response: TaskResponse = await client.submitTask(request);
const status: TaskStatus = response.status; // Typed as union
```

## Examples

See the `examples/` directory for complete usage examples:

- `basicUsage.ts` - Basic task submission and polling
- `multiServiceUsage.ts` - Using multiple specialized arms
- `errorHandling.ts` - Comprehensive error handling patterns

To run examples:

```bash
npm install
npm run build
npx ts-node examples/basicUsage.ts
```

## Development

```bash
# Install dependencies
npm install

# Build TypeScript
npm run build

# Run tests
npm test

# Run tests with coverage
npm run test:coverage

# Lint code
npm run lint

# Format code
npm run format
```

## Testing

The SDK uses Jest for testing:

```bash
# Run all tests
npm test

# Run tests in watch mode
npm run test:watch

# Generate coverage report
npm run test:coverage
```

## License

Apache License 2.0 - see [LICENSE](LICENSE) file for details.

## Support

- **Documentation**: https://github.com/yourusername/octollm/tree/main/docs
- **Issues**: https://github.com/yourusername/octollm/issues
- **Email**: support@octollm.example.com

## Related Projects

- [OctoLLM Python SDK](../python/octollm-sdk)
- [OctoLLM Architecture Documentation](../../docs)
- [OpenAPI Specifications](../../docs/api/openapi)
