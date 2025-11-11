# ValidationResult Schema Reference

## Overview

The **ValidationResult** schema represents the output from the Judge arm after validating outputs against schemas, acceptance criteria, facts, and quality standards. This multi-layer validation ensures outputs are structurally correct, factually accurate, and meet quality thresholds.

**Used By**: Judge Arm (output), Orchestrator (for decision-making)
**Primary Endpoint**: `POST /validate`
**Format**: JSON

---

## Structure

### ValidationResult

Complete validation output with issues, confidence, and quality metrics.

```typescript
interface ValidationResult {
  valid: boolean;                   // Required: No errors (warnings/info OK)
  confidence: number;               // Required: 0.0-1.0 confidence score
  issues: ValidationIssue[];        // Required: List of issues found
  passed_criteria: string[];        // Optional: Criteria that passed
  failed_criteria: string[];        // Optional: Criteria that failed
  quality_score: number;            // Required: 0.0-1.0 overall quality
  metadata: ValidationMetadata;     // Optional: Additional info
}

interface ValidationIssue {
  severity: 'error' | 'warning' | 'info';  // Required: Issue severity
  type: string;                            // Required: Issue type
  message: string;                         // Required: Human-readable description
  location: string;                        // Optional: Where the issue was found
  suggestion: string;                      // Optional: How to fix it
}

interface ValidationMetadata {
  validation_types_run: string[];   // Types executed (schema, facts, etc.)
  total_issues: number;             // Total issue count
  error_count: number;              // Number of errors
  warning_count: number;            // Number of warnings
  info_count: number;               // Number of info messages
  duration_ms: number;              // Validation execution time
  model?: string;                   // LLM model used (if applicable)
}
```

---

## Field Definitions

### `valid` (required)

**Type**: boolean
**Description**: Whether the output is considered valid (no errors)

**Validation Logic**:
- `true`: No issues with `severity: 'error'` (warnings and info are acceptable)
- `false`: At least one issue with `severity: 'error'`

**Examples**:
```json
// Valid output (warnings OK)
{
  "valid": true,
  "issues": [
    {"severity": "warning", "message": "Consider adding docstring"},
    {"severity": "info", "message": "Code style follows PEP 8"}
  ]
}

// Invalid output (errors present)
{
  "valid": false,
  "issues": [
    {"severity": "error", "message": "Missing required field 'tests'"},
    {"severity": "warning", "message": "Function name could be more descriptive"}
  ]
}
```

---

### `confidence` (required)

**Type**: number
**Constraints**: 0.0-1.0
**Description**: Confidence in the validation result (higher = more certain)

**Confidence Levels**:
| Range | Interpretation | Meaning |
|-------|----------------|---------|
| 0.9-1.0 | Very High | Extremely confident in validation |
| 0.7-0.89 | High | Confident, minor ambiguities |
| 0.5-0.69 | Medium | Moderate confidence, some uncertainty |
| 0.3-0.49 | Low | Significant uncertainty |
| 0.0-0.29 | Very Low | Highly uncertain, review manually |

**Factors Affecting Confidence**:
- Clear vs ambiguous acceptance criteria
- Availability of trusted sources for fact-checking
- Complexity of schema validation
- Presence of hallucination indicators
- Quality of LLM reasoning (if used)

**Examples**:
```typescript
// High confidence - clear violations
{
  valid: false,
  confidence: 0.95,
  issues: [
    {severity: "error", message: "Missing required field 'email'"}
  ]
}

// Low confidence - ambiguous criteria
{
  valid: true,
  confidence: 0.45,
  issues: [
    {severity: "warning", message: "Criterion 'code is good' is subjective"}
  ]
}
```

---

### `issues` (required)

**Type**: array of ValidationIssue objects
**Description**: List of all issues found during validation

#### ValidationIssue Structure

##### `severity` (required)

**Type**: enum - `'error'` | `'warning'` | `'info'`
**Description**: Severity level of the issue

**Severity Definitions**:

**error** - Blocking issue, prevents output acceptance
- Missing required fields
- Schema violations
- Failed acceptance criteria
- Factual hallucinations
- Critical quality issues

**warning** - Non-blocking issue, should be addressed but not critical
- Suboptimal implementations
- Style inconsistencies
- Minor quality concerns
- Deprecated patterns

**info** - Informational, no action required
- Best practice suggestions
- Optimization opportunities
- Context notes

**Example**:
```json
{
  "issues": [
    {
      "severity": "error",
      "type": "schema_violation",
      "message": "Missing required field 'tests'"
    },
    {
      "severity": "warning",
      "type": "style_issue",
      "message": "Function name uses camelCase instead of snake_case"
    },
    {
      "severity": "info",
      "type": "optimization",
      "message": "Consider using list comprehension for better performance"
    }
  ]
}
```

##### `type` (required)

**Type**: string
**Description**: Categorizes the issue for filtering and tracking

**Common Issue Types**:

**Schema Validation**:
- `schema_violation` - Output doesn't match expected schema
- `missing_field` - Required field is absent
- `invalid_type` - Field has wrong data type
- `constraint_violation` - Field violates constraints (min/max, regex, etc.)

**Criteria Validation**:
- `criteria_not_met` - Acceptance criterion failed
- `criteria_ambiguous` - Criterion is unclear or subjective

**Fact Checking**:
- `fact_mismatch` - Stated fact contradicts trusted sources
- `unsupported_claim` - Claim not found in sources
- `source_missing` - Citation lacks source

**Hallucination Detection**:
- `hallucination` - LLM fabricated information
- `confidence_mismatch` - High confidence on uncertain facts
- `detail_inconsistency` - Details contradict each other

**Quality Assessment**:
- `readability_issue` - Code/text is hard to understand
- `complexity_issue` - Unnecessarily complex solution
- `performance_issue` - Inefficient implementation
- `security_issue` - Potential security vulnerability
- `style_issue` - Code style inconsistencies

**Example**:
```json
{
  "issues": [
    {"type": "schema_violation", "message": "..."},
    {"type": "hallucination", "message": "..."},
    {"type": "security_issue", "message": "..."}
  ]
}
```

##### `message` (required)

**Type**: string
**Constraints**: 10-500 characters
**Description**: Human-readable description of the issue

**Best Practices**:
- Be specific and actionable
- Include relevant details (field names, expected vs actual values)
- Use clear, non-technical language when possible
- Avoid jargon unless necessary

**Examples**:
```json
// Good messages
"Missing required field 'email' in user object"
"CVSS score stated as 9.8 but actual score is 7.5 according to NVD"
"Function 'calc_avg' has cyclomatic complexity of 15 (max recommended: 10)"

// Bad messages
"Schema error"  // Too vague
"The code doesn't follow best practices"  // Not specific
```

##### `location` (optional)

**Type**: string
**Description**: Where the issue was found (field path, line number, function name)

**Format Examples**:
```json
// Field paths (dot notation)
"user.profile.email"
"tasks[2].status"

// Code locations
"function:calculate_average"
"line:42"
"file:auth.py:line:87"

// General locations
"root"
"N/A"
```

##### `suggestion` (optional)

**Type**: string
**Constraints**: 10-500 characters
**Description**: Actionable advice on how to fix the issue

**Examples**:
```json
{
  "issue": "Missing required field 'tests'",
  "suggestion": "Add a 'tests' field containing unit tests for the code"
},
{
  "issue": "Function has no docstring",
  "suggestion": "Add a docstring explaining parameters, return value, and example usage"
},
{
  "issue": "CVSS score mismatch",
  "suggestion": "Update CVSS score to 7.5 based on https://nvd.nist.gov/vuln/detail/CVE-2024-12345"
}
```

---

### `passed_criteria` (optional)

**Type**: array of strings
**Description**: Acceptance criteria that were successfully met

**Example**:
```json
{
  "passed_criteria": [
    "Code implements sorting functionality",
    "Function has proper naming",
    "Edge cases are handled"
  ]
}
```

---

### `failed_criteria` (optional)

**Type**: array of strings
**Description**: Acceptance criteria that were not met

**Example**:
```json
{
  "failed_criteria": [
    "Tests are included",
    "Performance is O(n log n) or better"
  ]
}
```

---

### `quality_score` (required)

**Type**: number
**Constraints**: 0.0-1.0
**Description**: Overall quality assessment of the output

**Quality Scoring Rubric**:

| Score Range | Grade | Interpretation |
|-------------|-------|----------------|
| 0.9-1.0 | Excellent | Production-ready, minimal issues |
| 0.7-0.89 | Good | Minor improvements needed |
| 0.5-0.69 | Fair | Moderate issues, rework suggested |
| 0.3-0.49 | Poor | Significant issues, major rework required |
| 0.0-0.29 | Very Poor | Unacceptable quality, restart recommended |

**Factors Considered**:
- Correctness (does it work?)
- Completeness (meets all requirements?)
- Readability (easy to understand?)
- Maintainability (easy to modify?)
- Performance (efficient?)
- Security (safe from vulnerabilities?)
- Style (consistent formatting?)

**Example**:
```json
{
  "quality_score": 0.85,
  "issues": [
    {"severity": "warning", "type": "style_issue", "message": "Minor style inconsistency"},
    {"severity": "info", "type": "optimization", "message": "Could use list comprehension"}
  ]
}
```

---

### `metadata` (optional)

**Type**: object
**Description**: Additional information about the validation process

**Common Metadata Fields**:
- `validation_types_run`: Types of validation performed
- `total_issues`: Total number of issues found
- `error_count`: Number of errors
- `warning_count`: Number of warnings
- `info_count`: Number of info messages
- `duration_ms`: Validation execution time
- `model`: LLM model used (if applicable)

**Example**:
```json
{
  "metadata": {
    "validation_types_run": ["schema", "criteria", "quality"],
    "total_issues": 3,
    "error_count": 1,
    "warning_count": 1,
    "info_count": 1,
    "duration_ms": 1250,
    "model": "gpt-3.5-turbo"
  }
}
```

---

## Complete Examples

### Example 1: Valid Output with Warnings

```json
{
  "valid": true,
  "confidence": 0.88,
  "issues": [
    {
      "severity": "warning",
      "type": "style_issue",
      "message": "Function name uses camelCase instead of snake_case",
      "location": "function:sortList",
      "suggestion": "Rename to 'sort_list' to follow Python naming conventions"
    },
    {
      "severity": "info",
      "type": "optimization",
      "message": "Consider adding type hints for better code clarity",
      "location": "function:sortList",
      "suggestion": "Add type hints like 'def sort_list(lst: List[int]) -> List[int]:'"
    }
  ],
  "passed_criteria": [
    "Code implements sorting functionality",
    "Tests are included",
    "Edge cases are handled"
  ],
  "failed_criteria": [],
  "quality_score": 0.82,
  "metadata": {
    "validation_types_run": ["schema", "criteria", "quality"],
    "total_issues": 2,
    "error_count": 0,
    "warning_count": 1,
    "info_count": 1,
    "duration_ms": 950,
    "model": "gpt-3.5-turbo"
  }
}
```

---

### Example 2: Invalid Output (Schema Violation)

```json
{
  "valid": false,
  "confidence": 0.95,
  "issues": [
    {
      "severity": "error",
      "type": "missing_field",
      "message": "Missing required field 'tests'",
      "location": "root",
      "suggestion": "Add a 'tests' field containing unit tests for the code"
    },
    {
      "severity": "error",
      "type": "criteria_not_met",
      "message": "Acceptance criterion not met: Tests are included",
      "location": "N/A",
      "suggestion": "Review output and ensure tests are included"
    },
    {
      "severity": "warning",
      "type": "style_issue",
      "message": "Function lacks docstring",
      "location": "function:sort_list",
      "suggestion": "Add docstring explaining parameters and return value"
    }
  ],
  "passed_criteria": [
    "Code implements sorting functionality"
  ],
  "failed_criteria": [
    "Tests are included"
  ],
  "quality_score": 0.55,
  "metadata": {
    "validation_types_run": ["schema", "criteria", "quality"],
    "total_issues": 3,
    "error_count": 2,
    "warning_count": 1,
    "info_count": 0,
    "duration_ms": 1150
  }
}
```

---

### Example 3: Hallucination Detection

```json
{
  "valid": false,
  "confidence": 0.72,
  "issues": [
    {
      "severity": "error",
      "type": "hallucination",
      "message": "CVSS score stated as 9.8 but actual score is 7.5 according to NVD",
      "location": "summary:cvss_score",
      "suggestion": "Update CVSS score to 7.5 based on https://nvd.nist.gov/vuln/detail/CVE-2024-12345"
    },
    {
      "severity": "error",
      "type": "hallucination",
      "message": "Affected versions claim 'prior to 1.24.0' but actually 'prior to 1.24.1'",
      "location": "summary:affected_versions",
      "suggestion": "Correct affected versions to 'prior to 1.24.1'"
    },
    {
      "severity": "error",
      "type": "unsupported_claim",
      "message": "Discoverer 'Alice Smith' not found in sources",
      "location": "summary:discoverer",
      "suggestion": "Remove unsupported claim or provide valid source"
    },
    {
      "severity": "warning",
      "type": "fact_mismatch",
      "message": "Discovery date stated as March but actual date is February",
      "location": "summary:discovery_date",
      "suggestion": "Correct discovery date to February 2024"
    }
  ],
  "passed_criteria": [],
  "failed_criteria": [
    "All facts are supported by trusted sources",
    "No hallucinations present"
  ],
  "quality_score": 0.35,
  "metadata": {
    "validation_types_run": ["facts", "hallucination"],
    "total_issues": 4,
    "error_count": 3,
    "warning_count": 1,
    "info_count": 0,
    "duration_ms": 2800,
    "model": "gpt-3.5-turbo"
  }
}
```

---

### Example 4: Quality Assessment (Low Score)

```json
{
  "valid": true,
  "confidence": 0.68,
  "issues": [
    {
      "severity": "warning",
      "type": "complexity_issue",
      "message": "Function has cyclomatic complexity of 15 (recommended max: 10)",
      "location": "function:calculate_statistics",
      "suggestion": "Refactor into smaller helper functions"
    },
    {
      "severity": "warning",
      "type": "performance_issue",
      "message": "Nested loops result in O(n²) complexity",
      "location": "function:find_duplicates",
      "suggestion": "Use a set-based approach for O(n) complexity"
    },
    {
      "severity": "warning",
      "type": "security_issue",
      "message": "User input not sanitized before use in shell command",
      "location": "line:87",
      "suggestion": "Use subprocess with parameterized commands instead of shell=True"
    },
    {
      "severity": "warning",
      "type": "readability_issue",
      "message": "Variable name 'x' is not descriptive",
      "location": "function:process_data",
      "suggestion": "Rename to descriptive name like 'user_count' or 'total_items'"
    },
    {
      "severity": "info",
      "type": "style_issue",
      "message": "Line length exceeds 88 characters (PEP 8 recommendation)",
      "location": "line:42",
      "suggestion": "Break line into multiple lines"
    }
  ],
  "passed_criteria": [
    "Code is functional",
    "Tests pass"
  ],
  "failed_criteria": [],
  "quality_score": 0.52,
  "metadata": {
    "validation_types_run": ["quality"],
    "total_issues": 5,
    "error_count": 0,
    "warning_count": 4,
    "info_count": 1,
    "duration_ms": 3500,
    "model": "gpt-4"
  }
}
```

---

## Usage Patterns

### Pattern 1: Interpreting Validation Results

```typescript
function interpretValidationResult(result: ValidationResult): string {
  if (result.valid && result.quality_score >= 0.8) {
    return '✅ Output is excellent and ready to use';
  }

  if (result.valid && result.quality_score >= 0.6) {
    return '⚠️ Output is acceptable but could be improved';
  }

  if (result.valid && result.quality_score < 0.6) {
    return '⚠️ Output is valid but quality is below threshold';
  }

  if (!result.valid && result.confidence > 0.8) {
    return '❌ Output is invalid (high confidence)';
  }

  if (!result.valid && result.confidence < 0.5) {
    return '❓ Output may be invalid (low confidence, manual review needed)';
  }

  return '❌ Output is invalid';
}
```

---

### Pattern 2: Filtering Issues by Severity

```python
def get_blocking_issues(result: ValidationResult) -> List[ValidationIssue]:
    """Get only error-level issues that block acceptance."""
    return [issue for issue in result.issues if issue.severity == "error"]

def has_security_issues(result: ValidationResult) -> bool:
    """Check if any security issues were found."""
    return any(issue.type == "security_issue" for issue in result.issues)

# Example usage
result = await judge_client.validate(output)

blocking = get_blocking_issues(result)
if blocking:
    print(f"❌ {len(blocking)} blocking issues found:")
    for issue in blocking:
        print(f"  - {issue.message}")

if has_security_issues(result):
    print("🔒 Security issues detected, review required")
```

---

### Pattern 3: Automatic Retry with Lower Quality Threshold

```typescript
async function validateWithRetry(
  output: any,
  minQualityScore: number = 0.8,
  maxRetries: number = 3
): Promise<ValidationResult> {
  let currentQuality = minQualityScore;

  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    const result = await judgeClient.validate({
      output,
      validationTypes: ['schema', 'criteria', 'quality']
    });

    // If valid and meets quality threshold, return
    if (result.valid && result.quality_score >= currentQuality) {
      console.log(`✅ Validation passed (attempt ${attempt})`);
      return result;
    }

    // Lower quality threshold for subsequent attempts
    currentQuality = Math.max(0.5, currentQuality - 0.1);

    console.log(`❌ Attempt ${attempt} failed (quality: ${result.quality_score.toFixed(2)})`);

    if (attempt < maxRetries) {
      console.log(`Retrying with lower threshold: ${currentQuality.toFixed(2)}...`);
    }
  }

  throw new Error('Validation failed after maximum retries');
}
```

---

### Pattern 4: Issue Aggregation and Reporting

```python
from collections import defaultdict

def generate_validation_report(result: ValidationResult) -> str:
    """Generate human-readable validation report."""

    report = []
    report.append(f"Validation Result: {'✅ PASS' if result.valid else '❌ FAIL'}")
    report.append(f"Confidence: {result.confidence:.2f}")
    report.append(f"Quality Score: {result.quality_score:.2f}")
    report.append("")

    # Group issues by severity
    issues_by_severity = defaultdict(list)
    for issue in result.issues:
        issues_by_severity[issue.severity].append(issue)

    # Report errors
    if "error" in issues_by_severity:
        report.append(f"🔴 ERRORS ({len(issues_by_severity['error'])})")
        for issue in issues_by_severity["error"]:
            report.append(f"  • [{issue.type}] {issue.message}")
            if issue.suggestion:
                report.append(f"    → {issue.suggestion}")
        report.append("")

    # Report warnings
    if "warning" in issues_by_severity:
        report.append(f"🟡 WARNINGS ({len(issues_by_severity['warning'])})")
        for issue in issues_by_severity["warning"]:
            report.append(f"  • [{issue.type}] {issue.message}")
        report.append("")

    # Report criteria results
    if result.passed_criteria:
        report.append(f"✅ PASSED CRITERIA ({len(result.passed_criteria)})")
        for criterion in result.passed_criteria:
            report.append(f"  • {criterion}")
        report.append("")

    if result.failed_criteria:
        report.append(f"❌ FAILED CRITERIA ({len(result.failed_criteria)})")
        for criterion in result.failed_criteria:
            report.append(f"  • {criterion}")
        report.append("")

    return "\n".join(report)

# Example usage
result = await judge_client.validate(output)
print(generate_validation_report(result))
```

---

## Best Practices

### 1. Always Check Both `valid` and `quality_score`

**Why**: An output can be valid but still low quality
**How**: Set minimum thresholds for both

```python
if result.valid and result.quality_score >= 0.7:
    accept_output(output)
else:
    reject_output(output)
```

---

### 2. Filter Issues by Severity for Decision-Making

**Why**: Not all issues are blocking
**How**: Only treat errors as blocking, warnings as advisory

```typescript
const errors = result.issues.filter(i => i.severity === 'error');
if (errors.length === 0) {
  // Accept with warnings
  acceptWithWarnings(output, result);
} else {
  // Reject due to errors
  reject(output, errors);
}
```

---

### 3. Use Confidence Scores for Manual Review Triggers

**Why**: Low confidence indicates uncertainty
**How**: Trigger manual review for low confidence

```python
if result.confidence < 0.6:
    send_for_manual_review(output, result)
elif result.valid:
    accept_automatically(output)
else:
    reject_automatically(output)
```

---

### 4. Track Issue Types Over Time

**Why**: Identify patterns and improve prompts
**How**: Log issue types for analysis

```typescript
// Track issue types in metrics
for (const issue of result.issues) {
  metrics.recordIssue(issue.type, issue.severity);
}

// Analyze trends
const commonIssues = metrics.getTopIssues(limit: 10);
console.log('Most common issues:', commonIssues);
```

---

## Related Documentation

- [Judge Arm API Reference](../services/judge.md)
- [TaskContract Schema](./TaskContract.md)
- [Validation Types Guide](../../guides/validation-types.md) (coming soon)
- [Quality Metrics Guide](../../guides/quality-metrics.md) (coming soon)

---

## JSON Schema

Complete JSON Schema for validation:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "ValidationResult",
  "type": "object",
  "required": ["valid", "confidence", "issues", "quality_score"],
  "properties": {
    "valid": {
      "type": "boolean",
      "description": "Whether output is valid (no errors)"
    },
    "confidence": {
      "type": "number",
      "minimum": 0.0,
      "maximum": 1.0,
      "description": "Confidence in validation result"
    },
    "issues": {
      "type": "array",
      "items": {
        "$ref": "#/definitions/ValidationIssue"
      },
      "description": "List of issues found"
    },
    "passed_criteria": {
      "type": "array",
      "items": {"type": "string"},
      "description": "Acceptance criteria that passed"
    },
    "failed_criteria": {
      "type": "array",
      "items": {"type": "string"},
      "description": "Acceptance criteria that failed"
    },
    "quality_score": {
      "type": "number",
      "minimum": 0.0,
      "maximum": 1.0,
      "description": "Overall quality score"
    },
    "metadata": {
      "type": "object",
      "properties": {
        "validation_types_run": {
          "type": "array",
          "items": {"type": "string"}
        },
        "total_issues": {"type": "integer"},
        "error_count": {"type": "integer"},
        "warning_count": {"type": "integer"},
        "info_count": {"type": "integer"},
        "duration_ms": {"type": "number"},
        "model": {"type": "string"}
      }
    }
  },
  "definitions": {
    "ValidationIssue": {
      "type": "object",
      "required": ["severity", "type", "message"],
      "properties": {
        "severity": {
          "type": "string",
          "enum": ["error", "warning", "info"],
          "description": "Issue severity level"
        },
        "type": {
          "type": "string",
          "description": "Issue type (e.g., schema_violation, hallucination)"
        },
        "message": {
          "type": "string",
          "minLength": 10,
          "maxLength": 500,
          "description": "Human-readable issue description"
        },
        "location": {
          "type": "string",
          "description": "Where the issue was found"
        },
        "suggestion": {
          "type": "string",
          "minLength": 10,
          "maxLength": 500,
          "description": "How to fix the issue"
        }
      }
    }
  }
}
```
