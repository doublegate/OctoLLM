# Coder Arm API Reference

**Service**: Coder Arm (Code Generation & Refactoring Specialist)
**Port**: 8005
**Base URL**: `http://localhost:8005` (development), `http://coder:8005` (internal)
**Technology**: Python 3.11+ / FastAPI
**Cost Tier**: 4 (High - uses GPT-4)
**Average Latency**: 2-5 seconds

## Overview

The Coder Arm is the software engineering expert of OctoLLM. It generates, debugs, refactors, and analyzes code across multiple programming languages with episodic memory for continuous improvement. Think of it as a senior developer who learns from every interaction and applies best practices consistently.

### Capabilities

- **Code Generation**: Create new functions, classes, and modules from natural language descriptions
- **Debugging**: Identify and fix bugs in existing code
- **Refactoring**: Improve code structure, readability, and performance
- **Code Analysis**: Understand and explain complex codebases
- **Test Generation**: Create comprehensive unit and integration tests
- **Code Explanation**: Generate documentation and detailed explanations
- **Performance Optimization**: Identify bottlenecks and suggest improvements

### Key Features

- **Multi-Language Support**: Python, JavaScript, TypeScript, Go, Rust, Java
- **Episodic Memory**: Learns from previous tasks to improve future outputs
- **GPT-4 Powered**: State-of-the-art code generation quality
- **Confidence Scoring**: Returns confidence level (0.0-1.0) for code quality
- **Constraint Adherence**: Respects style guides, type hints, and custom requirements
- **Test-Driven**: Automatically generates unit tests for validation

---

## Authentication

All Coder endpoints require Bearer token authentication (inter-service communication):

```bash
curl http://coder:8005/code \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json" \
  -d '{
    "request_type": "generate",
    "language": "python",
    "instruction": "Create a function that validates email addresses",
    "constraints": ["Include type hints", "Add docstring"]
  }'
```

**Note**: The Coder is typically called by the Orchestrator or Planner, not directly by external clients. External clients should use the [Orchestrator API](./orchestrator.md).

See [Authentication Guide](../API-OVERVIEW.md#authentication--authorization) for details on capability-based tokens.

---

## Endpoints

### POST /code

Process code requests including generation, debugging, refactoring, analysis, testing, explanation, and optimization.

#### Request

**Headers**:
- `Content-Type: application/json` (required)
- `Authorization: Bearer <token>` (required)
- `X-Request-ID: <uuid>` (optional, recommended for tracing)

**Body**:

```json
{
  "request_type": "generate",
  "language": "python",
  "instruction": "Create a function that validates email addresses using regex",
  "constraints": [
    "Must support RFC 5322 standard",
    "Include docstring with examples",
    "Add type hints"
  ],
  "context": {
    "framework": "Flask",
    "python_version": "3.11"
  }
}
```

**Field Descriptions**:

| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| `request_type` | string | ✅ | One of: `generate`, `debug`, `refactor`, `analyze`, `test`, `explain`, `optimize` | Type of code operation |
| `language` | string | ✅ | - | Programming language (python, javascript, typescript, go, rust, java) |
| `instruction` | string | ✅ | 10-1000 chars | Natural language description of what to do |
| `existing_code` | string | ❌ | - | Existing code (required for debug, refactor, analyze, explain, optimize) |
| `constraints` | array | ❌ | - | Requirements (style guide, type hints, error handling, etc.) |
| `context` | object | ❌ | - | Additional context (framework, version, dependencies, etc.) |

#### Response

**Status**: 200 OK

```json
{
  "success": true,
  "code": "import re\nfrom typing import Optional\n\ndef validate_email(email: str) -> bool:\n    \"\"\"Validate email address using RFC 5322 regex.\n    \n    Args:\n        email: Email address to validate\n        \n    Returns:\n        True if valid, False otherwise\n        \n    Examples:\n        >>> validate_email('user@example.com')\n        True\n        >>> validate_email('invalid')\n        False\n    \"\"\"\n    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$'\n    return bool(re.match(pattern, email))",
  "explanation": "Created email validator using regex pattern for RFC 5322 compliance. Includes type hints (str -> bool), comprehensive docstring with Args/Returns/Examples sections, and uses standard library 're' module.",
  "language": "python",
  "tests": "def test_validate_email():\n    # Valid emails\n    assert validate_email('user@example.com') == True\n    assert validate_email('test.user+tag@sub.domain.com') == True\n    \n    # Invalid emails\n    assert validate_email('invalid') == False\n    assert validate_email('@example.com') == False\n    assert validate_email('user@') == False",
  "confidence": 0.92,
  "warnings": [
    "Regex validation is not 100% RFC 5322 compliant (full compliance requires complex parser)",
    "Does not verify domain existence (only format validation)"
  ],
  "metadata": {
    "model": "gpt-4",
    "tokens_used": 450,
    "memory_hits": 2,
    "episodic_memory_used": true
  }
}
```

**Field Descriptions**:

| Field | Type | Description |
|-------|------|-------------|
| `success` | boolean | Whether code generation succeeded |
| `code` | string | Generated or modified code |
| `explanation` | string | Explanation of approach, design decisions, and trade-offs |
| `language` | string | Programming language (echo back from request) |
| `tests` | string | Unit tests for validation (optional, depends on request_type) |
| `confidence` | number | Confidence in code quality (0.0-1.0, typically >0.80 for production) |
| `warnings` | array | Caveats, limitations, or edge cases to be aware of |
| `metadata` | object | Additional info (model used, tokens consumed, memory hits) |

#### Examples

**Example 1: Generate New Function (Bash)**

```bash
curl -X POST http://coder:8005/code \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $SERVICE_TOKEN" \
  -d '{
    "request_type": "generate",
    "language": "python",
    "instruction": "Create a function that validates email addresses using regex",
    "constraints": [
      "Must support RFC 5322 standard",
      "Include docstring with examples",
      "Add type hints"
    ]
  }'

# Response: (see above)
```

**Example 2: Debug Existing Code (Python SDK)**

```python
from octollm_sdk import CoderClient

client = CoderClient(bearer_token="service_token_abc123")

buggy_code = """
def get_item(items, index):
    return items[index]

result = get_item([1, 2, 3], 5)
"""

response = await client.process_code({
    "request_type": "debug",
    "language": "python",
    "instruction": "Fix the bug causing IndexError",
    "existing_code": buggy_code,
    "constraints": [
        "Add proper error handling",
        "Return None if index out of bounds"
    ]
})

print("=== FIXED CODE ===")
print(response.code)

print("\n=== EXPLANATION ===")
print(response.explanation)

print(f"\nConfidence: {response.confidence * 100:.1f}%")

# Output:
# === FIXED CODE ===
# from typing import Optional, List, TypeVar
#
# T = TypeVar('T')
#
# def get_item(items: List[T], index: int) -> Optional[T]:
#     """Safely retrieve item from list by index.
#
#     Args:
#         items: List to retrieve from
#         index: Index to retrieve
#
#     Returns:
#         Item at index, or None if index out of bounds
#     """
#     if 0 <= index < len(items):
#         return items[index]
#     return None
#
# result = get_item([1, 2, 3], 5)  # Returns None
#
# === EXPLANATION ===
# Fixed IndexError by adding bounds checking (0 <= index < len(items)).
# Returns None for out-of-bounds indices instead of raising exception.
# Added type hints with generics (TypeVar) for type safety.
#
# Confidence: 95.0%
```

**Example 3: Refactor to Async/Await (TypeScript SDK)**

```typescript
import { CoderClient } from 'octollm-sdk';

const client = new CoderClient({
  bearerToken: process.env.SERVICE_TOKEN
});

const oldCode = `
function fetchData(url, callback) {
  fetch(url)
    .then(res => res.json())
    .then(data => callback(null, data))
    .catch(err => callback(err, null));
}
`;

const response = await client.processCode({
  requestType: 'refactor',
  language: 'javascript',
  instruction: 'Convert to async/await and add error handling',
  existingCode: oldCode,
  constraints: [
    'Use try-catch for error handling',
    'Add JSDoc comment',
    'Return null on error instead of throwing'
  ]
});

console.log('=== REFACTORED CODE ===');
console.log(response.code);

console.log(`\nWarnings: ${response.warnings.length}`);
response.warnings.forEach(w => console.log(`  - ${w}`));

// Output:
// === REFACTORED CODE ===
// /**
//  * Fetch JSON data from URL with error handling
//  * @param {string} url - URL to fetch from
//  * @returns {Promise<Object|null>} JSON data or null on error
//  */
// async function fetchData(url) {
//   try {
//     const response = await fetch(url);
//     const data = await response.json();
//     return data;
//   } catch (error) {
//     console.error('Fetch error:', error);
//     return null;
//   }
// }
//
// Warnings: 1
//   - Consider checking response.ok before parsing JSON
```

**Example 4: Generate Unit Tests (Python SDK)**

```python
from octollm_sdk import CoderClient

client = CoderClient(bearer_token="service_token_abc123")

existing_code = """
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)
"""

response = await client.process_code({
    "request_type": "test",
    "language": "python",
    "instruction": "Generate comprehensive unit tests",
    "existing_code": existing_code,
    "constraints": [
        "Use pytest",
        "Test edge cases (n=0, n=1, negative)",
        "Test performance for n=10"
    ]
})

print(response.code)  # Generated test code

# Output:
# import pytest
# from your_module import fibonacci
#
# def test_fibonacci_base_cases():
#     assert fibonacci(0) == 0
#     assert fibonacci(1) == 1
#
# def test_fibonacci_sequence():
#     assert fibonacci(2) == 1
#     assert fibonacci(5) == 5
#     assert fibonacci(10) == 55
#
# def test_fibonacci_negative():
#     with pytest.raises(RecursionError):
#         fibonacci(-1)
#
# def test_fibonacci_performance():
#     import time
#     start = time.time()
#     fibonacci(10)
#     duration = time.time() - start
#     assert duration < 0.1  # Should complete in <100ms
```

**Example 5: Analyze Code Complexity (TypeScript SDK)**

```typescript
import { CoderClient } from 'octollm-sdk';

const client = new CoderClient({ bearerToken: '...' });

const complexCode = `
function processData(data, options) {
  if (!data) return null;
  let result = [];
  for (let i = 0; i < data.length; i++) {
    if (options.filter && !options.filter(data[i])) continue;
    let item = data[i];
    if (options.transform) item = options.transform(item);
    if (options.validate && !options.validate(item)) continue;
    result.push(item);
  }
  return options.sort ? result.sort(options.comparator) : result;
}
`;

const response = await client.processCode({
  requestType: 'analyze',
  language: 'javascript',
  instruction: 'Analyze code complexity and suggest improvements',
  existingCode: complexCode
});

console.log('=== ANALYSIS ===');
console.log(response.explanation);

console.log('\n=== SUGGESTED REFACTORING ===');
console.log(response.code);
```

**Example 6: Optimize Performance (Python SDK)**

```python
from octollm_sdk import CoderClient

client = CoderClient(bearer_token="service_token_abc123")

slow_code = """
def find_duplicates(numbers):
    duplicates = []
    for i in range(len(numbers)):
        for j in range(i + 1, len(numbers)):
            if numbers[i] == numbers[j] and numbers[i] not in duplicates:
                duplicates.append(numbers[i])
    return duplicates
"""

response = await client.process_code({
    "request_type": "optimize",
    "language": "python",
    "instruction": "Optimize for O(n) time complexity",
    "existing_code": slow_code,
    "constraints": [
        "Maintain same functionality",
        "Use appropriate data structures",
        "Add complexity analysis in docstring"
    ]
})

print("=== OPTIMIZED CODE ===")
print(response.code)

print("\n=== PERFORMANCE IMPROVEMENT ===")
print(response.explanation)

# Output shows O(n) solution using set/dict instead of O(n²) nested loops
```

#### Error Responses

**400 Bad Request** (invalid request):

```json
{
  "success": false,
  "error": "ValidationError",
  "message": "existing_code required for request_type 'debug'",
  "details": {
    "field": "existing_code",
    "request_type": "debug"
  }
}
```

**401 Unauthorized** (missing or invalid token):

```json
{
  "success": false,
  "error": "Unauthorized",
  "message": "Bearer token required for code operations"
}
```

**500 Internal Server Error** (LLM failure):

```json
{
  "success": false,
  "error": "ServiceUnavailable",
  "message": "GPT-4 API rate limit exceeded",
  "details": {
    "retry_after": 60
  }
}
```

---

### GET /capabilities

Retrieve coder capabilities and supported languages.

#### Request

**No authentication required**

#### Response

**Status**: 200 OK

```json
{
  "capabilities": [
    "code_generation",
    "debugging",
    "refactoring",
    "code_analysis",
    "test_generation"
  ],
  "supported_languages": [
    "python",
    "javascript",
    "typescript",
    "go",
    "rust",
    "java"
  ]
}
```

---

### GET /health

Health check endpoint for load balancers and monitoring systems.

#### Request

**No authentication required**

#### Response

**Status**: 200 OK

```json
{
  "status": "healthy",
  "version": "0.3.0",
  "model": "gpt-4"
}
```

---

### GET /metrics

Prometheus metrics endpoint for observability.

#### Request

**No authentication required**

#### Response

**Status**: 200 OK
**Content-Type**: text/plain

```
# HELP coder_requests_total Total number of code requests
# TYPE coder_requests_total counter
coder_requests_total{request_type="generate",language="python"} 8234
coder_requests_total{request_type="debug",language="python"} 3421
coder_requests_total{request_type="refactor",language="javascript"} 1892

# HELP coder_avg_confidence Average code confidence
# TYPE coder_avg_confidence gauge
coder_avg_confidence 0.88

# HELP coder_tokens_used_total Total LLM tokens consumed
# TYPE coder_tokens_used_total counter
coder_tokens_used_total 12450892

# HELP coder_memory_hits_total Episodic memory hits
# TYPE coder_memory_hits_total counter
coder_memory_hits_total 5234
```

---

## Data Models

### CodeRequest

```typescript
type RequestType =
  | 'generate'
  | 'debug'
  | 'refactor'
  | 'analyze'
  | 'test'
  | 'explain'
  | 'optimize';

interface CodeRequest {
  request_type: RequestType;
  language: string;             // python, javascript, typescript, go, rust, java
  instruction: string;          // 10-1000 chars
  existing_code?: string;       // Required for debug, refactor, analyze, explain, optimize
  constraints?: string[];       // Style guide, error handling, etc.
  context?: {
    [key: string]: any;
  };
}
```

### CodeResponse

```typescript
interface CodeResponse {
  success: boolean;
  code: string;                 // Generated or modified code
  explanation: string;          // Explanation of approach and decisions
  language: string;
  tests?: string;               // Unit tests (optional)
  confidence: number;           // 0.0-1.0
  warnings: string[];           // Caveats and limitations
  metadata: {
    model: string;              // e.g., "gpt-4"
    tokens_used: number;
    memory_hits: number;
    episodic_memory_used: boolean;
  };
}
```

---

## Integration Patterns

### Pattern 1: Test-Driven Development (Generate + Test)

Generate code with tests, then validate.

```python
from octollm_sdk import CoderClient, ExecutorClient

coder = CoderClient(bearer_token="service_token_abc123")
executor = ExecutorClient(bearer_token="service_token_abc123")

async def tdd_workflow(instruction: str, language: str):
    # Generate code with tests
    code_response = await coder.process_code({
        "request_type": "generate",
        "language": language,
        "instruction": instruction,
        "constraints": ["Generate comprehensive unit tests"]
    })

    # Write code to file
    with open("generated_code.py", "w") as f:
        f.write(code_response.code)

    # Write tests to file
    with open("test_generated_code.py", "w") as f:
        f.write(code_response.tests)

    # Execute tests
    test_result = await executor.execute({
        "action_type": "python",
        "command": "pytest",
        "args": ["test_generated_code.py", "-v"],
        "timeout_seconds": 30,
        "capability_token": "tok_abc123"
    })

    if test_result.exit_code == 0:
        print("✓ All tests passed!")
    else:
        print("✗ Tests failed, debugging...")
        # Resubmit for debugging
```

### Pattern 2: Iterative Refinement with Confidence Check

If confidence is low, refine and retry.

```typescript
import { CoderClient } from 'octollm-sdk';

const client = new CoderClient({ bearerToken: '...' });

async function generateWithRefinement(
  instruction: string,
  language: string,
  minConfidence: number = 0.85
): Promise<CodeResponse> {
  let attempt = 0;
  const maxAttempts = 3;

  while (attempt < maxAttempts) {
    const response = await client.processCode({
      requestType: 'generate',
      language,
      instruction: attempt === 0 ? instruction : `${instruction}\n\nPrevious attempt had low confidence. Please improve.`,
      constraints: attempt > 0 ? ['Focus on correctness and edge cases'] : []
    });

    if (response.confidence >= minConfidence) {
      console.log(`✓ Generated with confidence ${(response.confidence * 100).toFixed(1)}%`);
      return response;
    }

    console.log(`Attempt ${attempt + 1}: Confidence ${(response.confidence * 100).toFixed(1)}% (below threshold)`);
    attempt++;
  }

  throw new Error('Could not generate high-confidence code after 3 attempts');
}
```

### Pattern 3: Multi-Stage Code Review (Generate + Analyze + Refactor)

Generate code, analyze it, then refactor based on analysis.

```python
from octollm_sdk import CoderClient

client = CoderClient(bearer_token="service_token_abc123")

async def generate_with_review(instruction: str, language: str):
    # Stage 1: Generate initial code
    gen_response = await client.process_code({
        "request_type": "generate",
        "language": language,
        "instruction": instruction
    })

    # Stage 2: Analyze generated code
    analyze_response = await client.process_code({
        "request_type": "analyze",
        "language": language,
        "instruction": "Analyze code quality, complexity, and suggest improvements",
        "existing_code": gen_response.code
    })

    print("=== ANALYSIS ===")
    print(analyze_response.explanation)

    # Stage 3: Refactor based on analysis
    refactor_response = await client.process_code({
        "request_type": "refactor",
        "language": language,
        "instruction": f"Refactor based on this analysis: {analyze_response.explanation}",
        "existing_code": gen_response.code
    })

    return refactor_response.code
```

---

## Performance Characteristics

| Request Type | P50 | P95 | P99 | Max | Notes |
|--------------|-----|-----|-----|-----|-------|
| Generate (simple) | 2.5s | 4.5s | 6.0s | 10s | ~500 tokens |
| Generate (complex) | 4.0s | 7.0s | 10s | 20s | ~1500 tokens |
| Debug | 2.0s | 3.5s | 5.0s | 8s | Smaller context |
| Refactor | 2.5s | 4.0s | 6.0s | 12s | Depends on code size |
| Analyze | 3.0s | 5.0s | 7.0s | 15s | Detailed analysis |
| Test Generation | 3.5s | 6.0s | 8.0s | 15s | Multiple test cases |

### Token Usage by Request Type

| Request Type | Avg Input Tokens | Avg Output Tokens | Total | Cost (GPT-4) |
|--------------|------------------|-------------------|-------|--------------|
| Generate | ~300 | ~200 | ~500 | $0.015 |
| Debug | ~400 | ~300 | ~700 | $0.021 |
| Refactor | ~500 | ~400 | ~900 | $0.027 |
| Analyze | ~600 | ~500 | ~1100 | $0.033 |
| Test | ~400 | ~600 | ~1000 | $0.030 |

**Note**: GPT-4 pricing: $0.03 / 1K input tokens, $0.06 / 1K output tokens

---

## Troubleshooting

### Issue 1: Low Confidence Code (<0.75)

**Symptoms**: Generated code has confidence <0.75, may have bugs

**Possible Causes**:
- Instruction too vague
- Conflicting constraints
- Unsupported language feature

**Solutions**:
```python
# Make instruction more specific
# Bad: "Create a function"
# Good: "Create a function that validates email addresses using RFC 5322 regex, with type hints and comprehensive docstring"

# Add more context
response = await client.process_code({
    "request_type": "generate",
    "language": "python",
    "instruction": "...",
    "context": {
        "framework": "Flask",
        "python_version": "3.11",
        "style_guide": "PEP 8"
    }
})
```

### Issue 2: Generated Code Doesn't Run

**Symptoms**: Code has syntax errors or runtime failures

**Possible Causes**:
- Missing imports
- Incorrect API usage
- Language version mismatch

**Solutions**:
```python
# Always test generated code
response = await coder.process_code({...})

# Execute with Executor arm
test_result = await executor.execute({
    "action_type": "python",
    "command": "python3",
    "args": ["-c", response.code],
    "timeout_seconds": 10
})

if test_result.exit_code != 0:
    # Debug the generated code
    debug_response = await coder.process_code({
        "request_type": "debug",
        "language": "python",
        "instruction": f"Fix this error: {test_result.stderr}",
        "existing_code": response.code
    })
```

### Issue 3: High Latency (>10s)

**Symptoms**: Code generation taking >10 seconds consistently

**Possible Causes**:
- Very long instruction or existing_code
- GPT-4 API throttling
- Complex refactoring task

**Solutions**:
```bash
# Check token usage
curl http://coder:8005/metrics | grep coder_tokens_used

# Reduce instruction/code length
# Keep instruction <500 chars, existing_code <2000 chars

# Split complex tasks into smaller steps
# Instead of "refactor entire module", do "refactor function X, then Y, then Z"

# Scale horizontally
kubectl scale deployment coder --replicas=5
```

### Issue 4: Episodic Memory Not Working

**Symptoms**: metadata.memory_hits always 0, similar tasks not improving

**Possible Causes**:
- Memory backend not configured
- Embeddings not indexed
- Task similarity too low

**Solutions**:
```bash
# Check memory configuration
kubectl get deployment coder -o yaml | grep MEMORY_ENABLED

# Verify memory backend health
kubectl logs -l app=coder | grep "episodic_memory"

# Check memory hits metric
curl http://coder:8005/metrics | grep memory_hits_total
```

### Issue 5: Code Quality Issues

**Symptoms**: Generated code works but has poor quality (no error handling, magic numbers, etc.)

**Possible Causes**:
- Missing constraints
- Low confidence threshold
- No code review step

**Solutions**:
```python
# Add comprehensive constraints
response = await client.process_code({
    "request_type": "generate",
    "language": "python",
    "instruction": "...",
    "constraints": [
        "Add comprehensive error handling",
        "Use type hints",
        "Add docstrings",
        "No magic numbers (use constants)",
        "Follow PEP 8 style guide",
        "Handle edge cases"
    ]
})

# Use multi-stage review (see Integration Patterns)
```

---

## Related Documentation

- [API Overview](../API-OVERVIEW.md)
- [Orchestrator API](./orchestrator.md)
- [Executor Arm API](./executor.md)
- [Judge Arm API](./judge.md)
- [OpenAPI Specification](../openapi/coder.yaml)

---

## Support

For issues with the Coder Arm:
1. Check [Troubleshooting](#troubleshooting) section above
2. Review logs: `kubectl logs -l app=coder`
3. Check metrics: `curl http://coder:8005/metrics`
4. File issue: https://github.com/octollm/octollm/issues
