# CodeGeneration Schema Reference

## Overview

The **CodeGeneration** (also called `CodeResponse`) schema represents the output from the Coder arm after processing code-related requests. This includes generated code, debugging fixes, refactorings, analysis, test generation, explanations, and optimizations.

**Used By**: Coder Arm (output), Orchestrator (for code tasks), Judge Arm (for validation)
**Primary Endpoint**: `POST /code`
**Format**: JSON

---

## Structure

### CodeGeneration (CodeResponse)

Complete code generation response with code, explanation, tests, and metadata.

```typescript
interface CodeGeneration {
  success: boolean;                 // Required: Whether operation succeeded
  code: string;                     // Required: Generated or modified code
  explanation: string;              // Required: Approach and design decisions
  language: string;                 // Required: Programming language
  tests?: string;                   // Optional: Unit tests
  confidence: number;               // Required: 0.0-1.0 quality confidence
  warnings: string[];               // Optional: Caveats and limitations
  metadata: CodeMetadata;           // Optional: Additional info
}

interface CodeMetadata {
  model: string;                    // LLM model used (e.g., "gpt-4")
  tokens_used: number;              // Total tokens consumed
  memory_hits: number;              // Episodic memory cache hits
  episodic_memory_used: boolean;    // Whether previous solutions were reused
  request_type: RequestType;        // Type of operation performed
  duration_ms: number;              // Execution time
  language_version?: string;        // Language version if specified
  framework?: string;               // Framework if specified (e.g., "React", "FastAPI")
}

type RequestType =
  | 'generate'      // Create new code
  | 'debug'         // Fix bugs
  | 'refactor'      // Improve structure
  | 'analyze'       // Understand code
  | 'test'          // Generate tests
  | 'explain'       // Document code
  | 'optimize';     // Improve performance
```

---

## Field Definitions

### `success` (required)

**Type**: boolean
**Description**: Whether the code operation succeeded

**Success Criteria**:
- `true`: Code generated/modified successfully
- `false`: Operation failed (error in processing, unable to complete task)

**Example**:
```json
// Successful generation
{
  "success": true,
  "code": "def validate_email(email: str) -> bool: ..."
}

// Failed generation
{
  "success": false,
  "code": "",
  "explanation": "Unable to generate code: instruction too vague"
}
```

**Note**: Even if `success: true`, always check `confidence` and `warnings` before using code in production.

---

### `code` (required)

**Type**: string
**Constraints**: 1-50,000 characters
**Description**: Generated, modified, or analyzed code

**Format**:
- Plain text source code
- No markdown code blocks (no ```python etc.)
- Properly indented according to language conventions
- Includes comments where helpful
- May include imports/dependencies at the top

**Examples by Request Type**:

**generate** - New code from scratch:
```python
from typing import Optional
import re

def validate_email(email: str) -> bool:
    """Validate email address using RFC 5322 regex.

    Args:
        email: Email address to validate

    Returns:
        True if valid, False otherwise

    Examples:
        >>> validate_email("user@example.com")
        True
        >>> validate_email("invalid.email")
        False
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))
```

**debug** - Fixed code:
```python
def get_item(items: List[T], index: int) -> Optional[T]:
    """Safely retrieve item from list by index."""
    if 0 <= index < len(items):
        return items[index]
    return None  # Fixed: added bounds check
```

**refactor** - Improved code:
```python
# Before (callback-based)
def fetchData(url, callback):
    fetch(url).then(data => callback(null, data))

# After (async/await)
async def fetch_data(url: str) -> Optional[dict]:
    """Fetch JSON data from URL with error handling."""
    try:
        response = await fetch(url)
        return await response.json()
    except Exception as error:
        logger.error(f"Fetch error: {error}")
        return None
```

**analyze** - Code with annotations:
```python
# Complexity: O(n²) - PERFORMANCE ISSUE
def find_duplicates(items):  # Missing type hints
    duplicates = []
    for i in range(len(items)):
        for j in range(i + 1, len(items)):  # Nested loop
            if items[i] == items[j]:
                duplicates.append(items[i])
    return duplicates
# Recommendation: Use set-based approach for O(n)
```

**test** - Test code:
```python
import pytest

def test_fibonacci_base_cases():
    assert fibonacci(0) == 0
    assert fibonacci(1) == 1

def test_fibonacci_recursive():
    assert fibonacci(5) == 5
    assert fibonacci(10) == 55
```

---

### `explanation` (required)

**Type**: string
**Constraints**: 50-5000 characters
**Description**: Human-readable explanation of the approach, design decisions, and trade-offs

**Should Include**:
- High-level approach and algorithm used
- Key design decisions and why they were made
- Trade-offs considered (performance vs readability, etc.)
- Assumptions made
- Important implementation details

**Examples by Request Type**:

**generate**:
```
Created an email validation function using regex pattern matching.
The pattern follows RFC 5322 standard with simplified rules for
common email formats. Includes docstring with examples and type hints
for better IDE support. Returns boolean for easy integration into
validation logic.
```

**debug**:
```
Fixed IndexError by adding bounds checking (0 <= index < len(items)).
Returns None for out-of-bounds indices instead of raising exception,
which is more graceful for the calling code. Added type hints with
generics (TypeVar) for type safety across different list types.
```

**refactor**:
```
Converted callback-based async code to modern async/await syntax for
better readability and error handling. Used try-catch instead of promise
chaining to simplify error flow. Returns None on error to avoid
exceptions propagating to callers. Added type hints for better IDE support.
```

**optimize**:
```
Replaced nested loops (O(n²)) with set-based approach (O(n)) for finding
duplicates. The new implementation creates a set to track seen items and
identifies duplicates in a single pass. This reduces time complexity from
quadratic to linear, significantly improving performance for large inputs.
```

---

### `language` (required)

**Type**: string
**Description**: Programming language of the code (echoed from request)

**Supported Languages**:
- **Python** (`python`)
- **JavaScript** (`javascript`)
- **TypeScript** (`typescript`)
- **Rust** (`rust`)
- **Go** (`go`)
- **Java** (`java`)
- **C++** (`cpp`)
- **C#** (`csharp`)
- **Ruby** (`ruby`)
- **PHP** (`php`)
- **Swift** (`swift`)
- **Kotlin** (`kotlin`)
- **Shell** (`bash`, `shell`)

**Example**:
```json
{
  "language": "python",
  "code": "def example(): ..."
}
```

---

### `tests` (optional)

**Type**: string
**Constraints**: 1-20,000 characters
**Description**: Unit tests for validating the generated code

**When Present**:
- `request_type: 'test'` - Always includes tests
- `request_type: 'generate'` - Includes tests if requested in constraints
- Other request types - Rarely includes tests

**Format**:
- Uses appropriate testing framework for language (pytest, jest, JUnit, etc.)
- Includes multiple test cases covering:
  - Happy path (normal inputs)
  - Edge cases (boundaries, empty inputs)
  - Error cases (invalid inputs)
- Well-named test functions (test_*, should_*, etc.)

**Example** (Python + pytest):
```python
import pytest
from email_validator import validate_email

def test_valid_emails():
    assert validate_email("user@example.com") == True
    assert validate_email("test.user+tag@sub.example.org") == True

def test_invalid_emails():
    assert validate_email("invalid.email") == False
    assert validate_email("@example.com") == False
    assert validate_email("user@") == False

def test_edge_cases():
    assert validate_email("") == False
    assert validate_email("a@b.c") == True  # Minimal valid email
```

---

### `confidence` (required)

**Type**: number
**Constraints**: 0.0-1.0
**Description**: Confidence in the quality and correctness of the generated code

**Confidence Levels**:
| Range | Interpretation | Recommendation |
|-------|----------------|----------------|
| 0.95-1.0 | Very High | Production-ready, thoroughly tested approach |
| 0.85-0.94 | High | Good quality, minor review recommended |
| 0.70-0.84 | Medium | Acceptable, moderate review needed |
| 0.50-0.69 | Low | Significant review required, may have issues |
| 0.0-0.49 | Very Low | Unreliable, major rework likely needed |

**Factors Affecting Confidence**:
- **Instruction Clarity**: Vague instructions → lower confidence
- **Language Familiarity**: Common languages (Python, JS) → higher confidence
- **Code Complexity**: Simple tasks → higher confidence
- **Edge Cases**: Well-defined edge cases → higher confidence
- **Testing**: Testable code → higher confidence

**Example**:
```json
{
  "confidence": 0.92,
  "warnings": [
    "Edge case handling for Unicode emails not fully tested"
  ]
}
```

**Best Practice**: Only use code with `confidence >= 0.80` in production without manual review.

---

### `warnings` (optional)

**Type**: array of strings
**Description**: Caveats, limitations, or potential issues with the generated code

**Common Warning Types**:

**Performance Warnings**:
- "O(n²) complexity may be slow for large inputs"
- "Recursive approach may hit stack limit for n > 1000"
- "Database query in loop may cause N+1 problem"

**Security Warnings**:
- "User input not sanitized, vulnerable to injection"
- "Hardcoded credentials should be moved to environment variables"
- "SQL query vulnerable to SQL injection, use parameterized queries"

**Compatibility Warnings**:
- "Requires Python 3.10+ for match statement"
- "Uses experimental async/await, may change in future Node versions"
- "Deprecated API usage, migrate to new API soon"

**Edge Case Warnings**:
- "Does not handle Unicode characters in input"
- "May fail for very large files (>1GB)"
- "Thread-safety not guaranteed for concurrent access"

**Example**:
```json
{
  "warnings": [
    "Regex pattern does not support international email addresses with Unicode characters",
    "Consider using a library like 'email-validator' for production use",
    "Performance may degrade for batch validation (>10k emails)"
  ]
}
```

---

### `metadata` (optional)

**Type**: object
**Description**: Additional information about the code generation process

**Common Metadata Fields**:

**`model`** - LLM model used:
```json
{"model": "gpt-4"}
{"model": "gpt-3.5-turbo"}
```

**`tokens_used`** - Total tokens consumed:
```json
{"tokens_used": 1450}  // Input + output tokens
```

**`memory_hits`** - Episodic memory cache hits:
```json
{"memory_hits": 2}  // Found 2 similar past solutions
```

**`episodic_memory_used`** - Whether previous solutions were reused:
```json
{"episodic_memory_used": true}
```

**`duration_ms`** - Execution time:
```json
{"duration_ms": 8500}
```

**Complete Metadata Example**:
```json
{
  "metadata": {
    "model": "gpt-4",
    "tokens_used": 2340,
    "memory_hits": 1,
    "episodic_memory_used": true,
    "request_type": "generate",
    "duration_ms": 7800,
    "language_version": "3.11",
    "framework": "FastAPI"
  }
}
```

---

## Complete Examples

### Example 1: Generate New Function (High Confidence)

```json
{
  "success": true,
  "code": "from typing import Optional\nimport re\n\ndef validate_email(email: str) -> bool:\n    \"\"\"Validate email address using RFC 5322 regex.\n\n    Args:\n        email: Email address to validate\n\n    Returns:\n        True if valid, False otherwise\n\n    Examples:\n        >>> validate_email(\"user@example.com\")\n        True\n        >>> validate_email(\"invalid.email\")\n        False\n    \"\"\"\n    if not email or not isinstance(email, str):\n        return False\n\n    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$'\n    return bool(re.match(pattern, email))",
  "explanation": "Created an email validation function using regex pattern matching. The pattern follows RFC 5322 standard with simplified rules for common email formats. Added input validation to handle edge cases (None, empty string, non-string types). Includes comprehensive docstring with examples and type hints for better IDE support. Returns boolean for easy integration into validation logic.",
  "language": "python",
  "tests": "import pytest\nfrom email_validator import validate_email\n\ndef test_valid_emails():\n    assert validate_email(\"user@example.com\") == True\n    assert validate_email(\"test.user+tag@sub.example.org\") == True\n\ndef test_invalid_emails():\n    assert validate_email(\"invalid.email\") == False\n    assert validate_email(\"@example.com\") == False\n    assert validate_email(\"user@\") == False\n\ndef test_edge_cases():\n    assert validate_email(\"\") == False\n    assert validate_email(None) == False\n    assert validate_email(123) == False\n    assert validate_email(\"a@b.c\") == True",
  "confidence": 0.92,
  "warnings": [
    "Regex pattern does not support international email addresses with Unicode characters",
    "Consider using a library like 'email-validator' for production use with full RFC 5322 compliance",
    "Performance may degrade for batch validation (>10k emails)"
  ],
  "metadata": {
    "model": "gpt-4",
    "tokens_used": 1450,
    "memory_hits": 0,
    "episodic_memory_used": false,
    "request_type": "generate",
    "duration_ms": 6200,
    "language_version": "3.11"
  }
}
```

---

### Example 2: Debug Existing Code

```json
{
  "success": true,
  "code": "from typing import Optional, List, TypeVar\n\nT = TypeVar('T')\n\ndef get_item(items: List[T], index: int) -> Optional[T]:\n    \"\"\"Safely retrieve item from list by index.\n\n    Args:\n        items: List to retrieve from\n        index: Index to retrieve\n\n    Returns:\n        Item at index, or None if index out of bounds\n    \"\"\"\n    if 0 <= index < len(items):\n        return items[index]\n    return None\n\n# Example usage\nresult = get_item([1, 2, 3], 5)  # Returns None instead of raising IndexError",
  "explanation": "Fixed IndexError by adding bounds checking (0 <= index < len(items)). Returns None for out-of-bounds indices instead of raising exception, which is more graceful for the calling code. Added type hints with generics (TypeVar) for type safety across different list types. Included comprehensive docstring explaining behavior and return values.",
  "language": "python",
  "confidence": 0.95,
  "warnings": [
    "Returning None may mask errors if caller doesn't check for None",
    "Consider raising a custom exception with clear error message for better debugging"
  ],
  "metadata": {
    "model": "gpt-4",
    "tokens_used": 980,
    "memory_hits": 1,
    "episodic_memory_used": true,
    "request_type": "debug",
    "duration_ms": 4500
  }
}
```

---

### Example 3: Refactor to Async/Await

```json
{
  "success": true,
  "code": "/**\n * Fetch JSON data from URL with error handling\n * @param {string} url - URL to fetch from\n * @returns {Promise<Object|null>} JSON data or null on error\n */\nasync function fetchData(url) {\n  try {\n    const response = await fetch(url);\n\n    if (!response.ok) {\n      throw new Error(`HTTP error! status: ${response.status}`);\n    }\n\n    const data = await response.json();\n    return data;\n  } catch (error) {\n    console.error('Fetch error:', error);\n    return null;\n  }\n}",
  "explanation": "Converted callback-based async code to modern async/await syntax for better readability and error handling. Used try-catch instead of promise chaining to simplify error flow. Added check for response.ok to handle HTTP errors properly. Returns null on error to avoid exceptions propagating to callers. Added JSDoc comment for documentation.",
  "language": "javascript",
  "confidence": 0.88,
  "warnings": [
    "Consider checking response.ok before parsing JSON",
    "Logging to console may not be appropriate for production (use proper logging framework)",
    "Returning null on error may hide issues; consider throwing custom error or using Result type"
  ],
  "metadata": {
    "model": "gpt-4",
    "tokens_used": 1120,
    "memory_hits": 2,
    "episodic_memory_used": true,
    "request_type": "refactor",
    "duration_ms": 5800
  }
}
```

---

### Example 4: Generate Unit Tests

```json
{
  "success": true,
  "code": "import pytest\n\ndef test_fibonacci_base_cases():\n    \"\"\"Test base cases n=0 and n=1\"\"\"\n    assert fibonacci(0) == 0\n    assert fibonacci(1) == 1\n\ndef test_fibonacci_recursive():\n    \"\"\"Test recursive cases\"\"\"\n    assert fibonacci(2) == 1\n    assert fibonacci(5) == 5\n    assert fibonacci(10) == 55\n\ndef test_fibonacci_negative():\n    \"\"\"Test negative inputs\"\"\"\n    with pytest.raises(ValueError):\n        fibonacci(-1)\n\ndef test_fibonacci_performance():\n    \"\"\"Test performance for n=10\"\"\"\n    import time\n    start = time.time()\n    result = fibonacci(10)\n    duration = time.time() - start\n    assert result == 55\n    assert duration < 0.1  # Should complete in <100ms",
  "explanation": "Generated comprehensive unit tests using pytest. Tests cover: (1) Base cases (n=0, n=1), (2) Recursive cases (n=2, 5, 10), (3) Edge case (negative input), (4) Performance check (n=10 completes in <100ms). Each test function is well-named and includes docstring. Uses pytest.raises for exception testing.",
  "language": "python",
  "confidence": 0.90,
  "warnings": [
    "Performance test may be flaky depending on system load",
    "Original fibonacci function should validate n >= 0 to make negative test pass",
    "Consider adding tests for large n values (e.g., n=30) to catch stack overflow"
  ],
  "metadata": {
    "model": "gpt-4",
    "tokens_used": 1680,
    "memory_hits": 0,
    "episodic_memory_used": false,
    "request_type": "test",
    "duration_ms": 7200
  }
}
```

---

### Example 5: Failed Generation (Low Confidence)

```json
{
  "success": false,
  "code": "",
  "explanation": "Unable to generate code due to ambiguous instruction. The request asked to 'make the code better' without specifying what aspects to improve (performance, readability, security, etc.). Additionally, no existing code was provided to refactor. Please clarify the specific improvements desired and provide the code to be modified.",
  "language": "python",
  "confidence": 0.15,
  "warnings": [
    "Instruction too vague: 'make the code better' is subjective",
    "No existing code provided for refactoring",
    "Recommend re-submitting with specific constraints (e.g., 'optimize for performance', 'add error handling')"
  ],
  "metadata": {
    "model": "gpt-4",
    "tokens_used": 320,
    "memory_hits": 0,
    "episodic_memory_used": false,
    "request_type": "refactor",
    "duration_ms": 2100
  }
}
```

---

## Usage Patterns

### Pattern 1: Iterative Refinement

Generate code, validate, and refine based on feedback.

```python
from octollm_sdk import CoderClient, JudgeClient

coder = CoderClient(bearer_token="service_token_abc123")
judge = JudgeClient(bearer_token="service_token_abc123")

MAX_ATTEMPTS = 3

async def generate_with_validation(instruction: str, language: str):
    for attempt in range(1, MAX_ATTEMPTS + 1):
        # Generate code
        code_result = await coder.process_code({
            "request_type": "generate",
            "language": language,
            "instruction": instruction
        })

        if not code_result.success:
            print(f"Attempt {attempt} failed: {code_result.explanation}")
            continue

        # Validate code
        validation = await judge.validate({
            "output": {"code": code_result.code},
            "validation_types": ["schema", "quality"]
        })

        if validation.valid and validation.quality_score >= 0.8:
            print(f"✅ Success on attempt {attempt}")
            return code_result

        # Refine instruction with validation feedback
        instruction += f"\n\nPrevious attempt issues: {', '.join([i.message for i in validation.issues])}"

    raise Exception("Failed to generate valid code after maximum attempts")
```

---

### Pattern 2: Confidence-Based Acceptance

Only accept code above confidence threshold.

```typescript
const MIN_CONFIDENCE = 0.85;

async function generateCode(instruction: string): Promise<CodeGeneration> {
  const result = await coderClient.processCode({
    requestType: 'generate',
    language: 'python',
    instruction
  });

  if (!result.success) {
    throw new Error(`Code generation failed: ${result.explanation}`);
  }

  if (result.confidence < MIN_CONFIDENCE) {
    console.warn(`⚠️ Low confidence (${result.confidence.toFixed(2)}), manual review required`);
    console.warn(`Warnings: ${result.warnings.join(', ')}`);
    // Send for manual review
    await sendForReview(result);
  } else {
    console.log(`✅ High confidence (${result.confidence.toFixed(2)}), auto-accepting`);
  }

  return result;
}
```

---

### Pattern 3: Multi-Language Code Generation

Generate equivalent code in multiple languages.

```python
async def generate_multilanguage(instruction: str, languages: List[str]):
    """Generate equivalent code in multiple languages."""
    results = {}

    for lang in languages:
        result = await coder.process_code({
            "request_type": "generate",
            "language": lang,
            "instruction": instruction
        })
        results[lang] = result

    # Compare confidence scores
    best_lang = max(results.items(), key=lambda x: x[1].confidence)
    print(f"Best implementation: {best_lang[0]} (confidence: {best_lang[1].confidence:.2f})")

    return results

# Example usage
results = await generate_multilanguage(
    "Implement binary search",
    ["python", "javascript", "rust", "go"]
)
```

---

## Best Practices

### 1. Always Check `success` and `confidence`

**Why**: Even successful generations may have low confidence
**How**: Validate both fields

```python
if result.success and result.confidence >= 0.85:
    use_code(result.code)
else:
    send_for_review(result)
```

---

### 2. Review Warnings Before Production Use

**Why**: Warnings highlight potential issues
**How**: Log and review all warnings

```typescript
if (result.warnings.length > 0) {
  console.warn('Code generation warnings:');
  result.warnings.forEach(w => console.warn(`  - ${w}`));
}
```

---

### 3. Use Tests to Validate Generated Code

**Why**: Tests catch bugs before production
**How**: Always request tests or generate separately

```python
code_result = await coder.process_code({
    "request_type": "generate",
    "language": "python",
    "instruction": "...",
    "constraints": ["Generate comprehensive unit tests"]
})

# Run tests
if code_result.tests:
    run_tests(code_result.tests)
```

---

### 4. Leverage Episodic Memory for Repeated Tasks

**Why**: Reusing past solutions improves quality and speed
**How**: Check `metadata.episodic_memory_used`

```typescript
if (result.metadata.episodic_memory_used) {
  console.log(`✨ Reused ${result.metadata.memory_hits} past solution(s)`);
}
```

---

## Related Documentation

- [Coder Arm API Reference](../services/coder.md)
- [ValidationResult Schema](./ValidationResult.md)
- [TaskContract Schema](./TaskContract.md)
- [Code Generation Best Practices](../../guides/code-generation.md) (coming soon)

---

## JSON Schema

Complete JSON Schema for validation:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "CodeGeneration",
  "type": "object",
  "required": ["success", "code", "explanation", "language", "confidence"],
  "properties": {
    "success": {
      "type": "boolean",
      "description": "Whether operation succeeded"
    },
    "code": {
      "type": "string",
      "minLength": 0,
      "maxLength": 50000,
      "description": "Generated or modified code"
    },
    "explanation": {
      "type": "string",
      "minLength": 50,
      "maxLength": 5000,
      "description": "Approach and design decisions"
    },
    "language": {
      "type": "string",
      "description": "Programming language"
    },
    "tests": {
      "type": "string",
      "minLength": 1,
      "maxLength": 20000,
      "description": "Unit tests"
    },
    "confidence": {
      "type": "number",
      "minimum": 0.0,
      "maximum": 1.0,
      "description": "Quality confidence score"
    },
    "warnings": {
      "type": "array",
      "items": {"type": "string"},
      "description": "Caveats and limitations"
    },
    "metadata": {
      "type": "object",
      "properties": {
        "model": {"type": "string"},
        "tokens_used": {"type": "integer"},
        "memory_hits": {"type": "integer"},
        "episodic_memory_used": {"type": "boolean"},
        "request_type": {
          "type": "string",
          "enum": ["generate", "debug", "refactor", "analyze", "test", "explain", "optimize"]
        },
        "duration_ms": {"type": "number"},
        "language_version": {"type": "string"},
        "framework": {"type": "string"}
      }
    }
  }
}
```
