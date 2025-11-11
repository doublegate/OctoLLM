# Executor Arm API Reference

**Service**: Executor Arm (Sandboxed Command Execution)
**Port**: 8003
**Base URL**: `http://localhost:8003` (development), `http://executor:8003` (internal)
**Technology**: Rust 1.75+ / Axum
**Cost Tier**: 3 (Medium-High - sandboxing overhead)
**Average Latency**: 0.5-5 seconds

## Overview

The Executor Arm is the hands of OctoLLM - it safely executes shell commands, HTTP requests, and scripts in isolated sandbox environments. Think of it as a skilled technician working in a cleanroom, following strict protocols to ensure no contamination or damage occurs.

### Capabilities

- **Shell Execution**: Run allowlisted shell commands (ls, cat, grep, etc.)
- **HTTP Requests**: Make external API calls via curl/wget
- **Python Execution**: Run Python scripts in isolated environments
- **Capability-Based Access**: Fine-grained permissions per execution
- **Resource Limits**: CPU, memory, time, and network constraints
- **Provenance Tracking**: Audit trail for every command executed

### Key Features

- **Sandboxed Isolation**: Docker containers with gVisor for kernel-level isolation
- **Allowlist Security**: Only pre-approved commands permitted
- **Non-Root Execution**: All commands run as unprivileged users
- **Timeout Enforcement**: Hard limits prevent runaway processes
- **Command Hashing**: SHA-256 hashes for audit and replay detection
- **Zero-Trust Model**: Every execution requires explicit capability token

---

## Authentication

All Executor endpoints require Bearer token authentication with **capability tokens**:

```bash
curl http://executor:8003/execute \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json" \
  -d '{
    "action_type": "shell",
    "command": "ls",
    "args": ["-la", "/tmp"],
    "timeout_seconds": 10,
    "capability_token": "tok_abc123xyz"
  }'
```

**Capability Tokens**: Short-lived tokens encoding specific permissions (e.g., "ShellRead", "FilesystemRead"). Issued by Orchestrator for each execution.

**Note**: The Executor is typically called by the Orchestrator with time-limited capability tokens, not directly by external clients. External clients should use the [Orchestrator API](./orchestrator.md).

See [Authentication Guide](../API-OVERVIEW.md#authentication--authorization) for details on capability-based access control.

---

## Endpoints

### POST /execute

Execute a command in an isolated sandbox with capability-based access control.

#### Request

**Headers**:
- `Content-Type: application/json` (required)
- `Authorization: Bearer <token>` (required)
- `X-Request-ID: <uuid>` (optional, recommended for tracing)

**Body**:

```json
{
  "action_type": "shell",
  "command": "ls",
  "args": ["-la", "/tmp"],
  "timeout_seconds": 10,
  "capability_token": "tok_abc123xyz",
  "metadata": {
    "task_id": "task_123",
    "step_number": 3
  }
}
```

**Field Descriptions**:

| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| `action_type` | string | ✅ | One of: `shell`, `http`, `python` | Type of execution |
| `command` | string | ✅ | Must be in allowlist | Command to execute (e.g., `ls`, `curl`, `python3`) |
| `args` | array | ❌ | - | Command arguments (e.g., `["-la", "/tmp"]`) |
| `timeout_seconds` | integer | ❌ | 1-300, default: 30 | Maximum execution time |
| `capability_token` | string | ✅ | Pattern: `^tok_[a-zA-Z0-9]+$` | Authorization token with required capabilities |
| `metadata` | object | ❌ | - | Additional context (task_id, step_number, etc.) |

#### Response

**Status**: 200 OK (execution completed, check `success` field for actual result)

```json
{
  "success": true,
  "stdout": "total 32\ndrwxrwxrwt 10 root root 4096 Nov 11 10:30 .\ndrwxr-xr-x 20 root root 4096 Nov 10 08:00 ..",
  "stderr": "",
  "exit_code": 0,
  "duration_ms": 45,
  "provenance": {
    "arm_id": "executor",
    "timestamp": "2025-11-11T10:30:00Z",
    "action_type": "shell",
    "command_hash": "sha256:1a2b3c4d5e6f...",
    "capabilities_used": [
      "ShellRead",
      "FilesystemRead"
    ]
  }
}
```

**Field Descriptions**:

| Field | Type | Description |
|-------|------|-------------|
| `success` | boolean | Whether execution succeeded (exit_code == 0) |
| `stdout` | string | Standard output from command |
| `stderr` | string | Standard error from command |
| `exit_code` | integer | Process exit code (0 = success, >0 = error) |
| `duration_ms` | integer | Execution duration in milliseconds |
| `provenance` | object | Audit metadata (arm_id, timestamp, command hash, capabilities) |

#### Examples

**Example 1: Shell Command - List Directory (Bash)**

```bash
curl -X POST http://executor:8003/execute \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $SERVICE_TOKEN" \
  -d '{
    "action_type": "shell",
    "command": "ls",
    "args": ["-la", "/tmp"],
    "timeout_seconds": 10,
    "capability_token": "tok_abc123xyz"
  }'

# Response:
{
  "success": true,
  "stdout": "total 32\ndrwxrwxrwt 10 root root 4096 Nov 11 10:30 .",
  "stderr": "",
  "exit_code": 0,
  "duration_ms": 45,
  "provenance": {
    "arm_id": "executor",
    "timestamp": "2025-11-11T10:30:00Z",
    "action_type": "shell",
    "command_hash": "sha256:1a2b3c4d5e6f...",
    "capabilities_used": ["ShellRead", "FilesystemRead"]
  }
}
```

**Example 2: HTTP Request - API Call (Python SDK)**

```python
from octollm_sdk import ExecutorClient

client = ExecutorClient(bearer_token="service_token_abc123")

result = await client.execute({
    "action_type": "http",
    "command": "curl",
    "args": [
        "-X", "GET",
        "https://api.github.com/repos/octollm/octollm"
    ],
    "timeout_seconds": 30,
    "capability_token": "tok_abc123xyz"
})

if result.success:
    print("Response:", result.stdout)
    print(f"Duration: {result.duration_ms}ms")
else:
    print("Error:", result.stderr)
    print(f"Exit code: {result.exit_code}")

# Output:
# Response: {"name":"octollm","full_name":"octollm/octollm",...}
# Duration: 1250ms
```

**Example 3: Python Script Execution (TypeScript SDK)**

```typescript
import { ExecutorClient } from 'octollm-sdk';

const client = new ExecutorClient({
  bearerToken: process.env.SERVICE_TOKEN
});

const script = `
import sys
print("Python version:", sys.version)
print("2 + 2 =", 2 + 2)
`;

const result = await client.execute({
  actionType: 'python',
  command: 'python3',
  args: ['-c', script],
  timeoutSeconds: 10,
  capabilityToken: 'tok_abc123xyz'
});

console.log('=== STDOUT ===');
console.log(result.stdout);
console.log('\n=== STDERR ===');
console.log(result.stderr);
console.log(`\nExit Code: ${result.exitCode}`);
console.log(`Duration: ${result.durationMs}ms`);

// Output:
// === STDOUT ===
// Python version: 3.11.5 (main, Sep 11 2023, 14:09:26)
// 2 + 2 = 4
//
// === STDERR ===
//
// Exit Code: 0
// Duration: 320ms
```

**Example 4: Command Failure Handling (Python SDK)**

```python
from octollm_sdk import ExecutorClient, ExecutionError

client = ExecutorClient(bearer_token="service_token_abc123")

try:
    result = await client.execute({
        "action_type": "shell",
        "command": "cat",
        "args": ["/nonexistent/file.txt"],
        "timeout_seconds": 5,
        "capability_token": "tok_abc123xyz"
    })

    if not result.success:
        print(f"Command failed with exit code {result.exit_code}")
        print(f"Error: {result.stderr}")

except ExecutionError as e:
    print(f"Execution error: {e}")
```

**Example 5: Network Scanning with Timeout (Bash)**

```bash
curl -X POST http://executor:8003/execute \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $SERVICE_TOKEN" \
  -d '{
    "action_type": "shell",
    "command": "nmap",
    "args": ["-p", "80,443", "192.168.1.1"],
    "timeout_seconds": 60,
    "capability_token": "tok_network_scan_xyz"
  }'

# Response:
{
  "success": true,
  "stdout": "Starting Nmap 7.94...\nPORT    STATE SERVICE\n80/tcp  open  http\n443/tcp open  https",
  "stderr": "",
  "exit_code": 0,
  "duration_ms": 8432,
  "provenance": {
    "arm_id": "executor",
    "timestamp": "2025-11-11T10:35:00Z",
    "action_type": "shell",
    "command_hash": "sha256:7f8e9a0b1c2d...",
    "capabilities_used": ["ShellExecute", "NetworkAccess"]
  }
}
```

#### Error Responses

**403 Forbidden** (command not in allowlist):

```json
{
  "success": false,
  "error": "Command 'rm' not in allowlist",
  "error_type": "CapabilityViolation",
  "allowed_commands": [
    "echo",
    "cat",
    "ls",
    "grep",
    "curl",
    "python3"
  ]
}
```

**408 Request Timeout** (execution timeout):

```json
{
  "success": false,
  "error": "Command execution exceeded timeout of 30 seconds",
  "error_type": "ExecutionTimeout",
  "duration_ms": 30000
}
```

**401 Unauthorized** (missing or invalid capability token):

```json
{
  "success": false,
  "error": "Invalid or expired capability token",
  "error_type": "Unauthorized"
}
```

---

### GET /capabilities

Retrieve executor capabilities and allowlisted commands.

#### Request

**No authentication required**

#### Response

**Status**: 200 OK

```json
{
  "capabilities": [
    "shell_execution",
    "http_requests",
    "python_execution"
  ],
  "allowed_commands": [
    "echo",
    "ls",
    "cat",
    "grep",
    "curl",
    "wget",
    "python3",
    "nmap"
  ]
}
```

#### Examples

**Example 1: Check Allowed Commands (Bash)**

```bash
curl -X GET http://executor:8003/capabilities

# Response:
{
  "capabilities": [
    "shell_execution",
    "http_requests",
    "python_execution"
  ],
  "allowed_commands": [
    "echo",
    "ls",
    "cat",
    "grep",
    "curl",
    "wget",
    "python3",
    "nmap"
  ]
}
```

**Example 2: Validate Command Before Execution (Python SDK)**

```python
from octollm_sdk import ExecutorClient

client = ExecutorClient(bearer_token="service_token_abc123")

# Check if command is allowed
capabilities = await client.get_capabilities()

command = "rm"  # Dangerous command
if command in capabilities.allowed_commands:
    print(f"✓ Command '{command}' is allowed")
else:
    print(f"✗ Command '{command}' not allowed. Use one of: {capabilities.allowed_commands}")
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
  "version": "0.3.0"
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
# HELP executor_executions_total Total number of executions
# TYPE executor_executions_total counter
executor_executions_total{action_type="shell",success="true"} 15234
executor_executions_total{action_type="shell",success="false"} 892
executor_executions_total{action_type="http",success="true"} 8901
executor_executions_total{action_type="python",success="true"} 3421

# HELP executor_execution_duration_seconds Execution duration
# TYPE executor_execution_duration_seconds histogram
executor_execution_duration_seconds_bucket{le="0.5"} 8234
executor_execution_duration_seconds_bucket{le="1.0"} 12523
executor_execution_duration_seconds_bucket{le="5.0"} 19836

# HELP executor_capability_violations_total Capability violations
# TYPE executor_capability_violations_total counter
executor_capability_violations_total 45

# HELP executor_timeouts_total Execution timeouts
# TYPE executor_timeouts_total counter
executor_timeouts_total 23
```

---

## Data Models

### ExecutionRequest

```typescript
type ActionType = 'shell' | 'http' | 'python';

interface ExecutionRequest {
  action_type: ActionType;
  command: string;              // Must be in allowlist
  args?: string[];
  timeout_seconds?: number;     // 1-300, default: 30
  capability_token: string;     // Format: tok_<alphanumeric>
  metadata?: {
    [key: string]: any;
  };
}
```

### ExecutionResult

```typescript
interface ExecutionResult {
  success: boolean;
  stdout: string;
  stderr: string;
  exit_code: number;
  duration_ms: number;
  provenance: ProvenanceMetadata;
}
```

### ProvenanceMetadata

```typescript
interface ProvenanceMetadata {
  arm_id: string;              // Always "executor"
  timestamp: string;           // ISO 8601 format
  action_type: string;         // shell, http, python
  command_hash: string;        // SHA-256 hash of command + args
  capabilities_used: string[]; // e.g., ["ShellRead", "FilesystemRead"]
}
```

---

## Integration Patterns

### Pattern 1: Orchestrator-Driven Execution

The Orchestrator issues capability tokens and delegates execution to the Executor.

```python
from octollm_sdk import ExecutorClient

executor = ExecutorClient(bearer_token="service_token_abc123")

async def execute_with_capabilities(command: str, args: list, capabilities: list):
    # Orchestrator generates capability token (not shown)
    capability_token = generate_capability_token(capabilities, duration_seconds=60)

    result = await executor.execute({
        "action_type": "shell",
        "command": command,
        "args": args,
        "timeout_seconds": 30,
        "capability_token": capability_token
    })

    # Log provenance for audit
    print(f"Executed: {command} {' '.join(args)}")
    print(f"Hash: {result.provenance.command_hash}")
    print(f"Capabilities used: {result.provenance.capabilities_used}")

    return result
```

### Pattern 2: Retry Logic for Network Commands

Network commands may fail transiently; implement retry logic.

```typescript
import { ExecutorClient } from 'octollm-sdk';

const client = new ExecutorClient({ bearerToken: '...' });

async function executeWithRetry(
  request: ExecutionRequest,
  maxAttempts: number = 3
): Promise<ExecutionResult> {
  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    try {
      const result = await client.execute(request);

      if (result.success) {
        return result;
      }

      // Check if error is retryable
      if (result.stderr.includes('Connection refused') ||
          result.stderr.includes('Temporary failure')) {
        console.log(`Attempt ${attempt} failed, retrying...`);
        await new Promise(resolve => setTimeout(resolve, 1000 * attempt));
        continue;
      }

      // Non-retryable error
      return result;
    } catch (error) {
      if (attempt === maxAttempts) throw error;
      await new Promise(resolve => setTimeout(resolve, 1000 * attempt));
    }
  }

  throw new Error('Max retry attempts exceeded');
}
```

### Pattern 3: Command Hashing for Replay Detection

Use command hashes to detect and prevent replay attacks.

```python
from octollm_sdk import ExecutorClient
import hashlib

client = ExecutorClient(bearer_token="service_token_abc123")

executed_hashes = set()

async def execute_once(request: dict):
    # Pre-compute hash (should match provenance.command_hash)
    command_str = f"{request['command']} {' '.join(request.get('args', []))}"
    expected_hash = hashlib.sha256(command_str.encode()).hexdigest()

    # Check if already executed
    if expected_hash in executed_hashes:
        print(f"⚠️ Replay detected: {command_str}")
        return None

    result = await client.execute(request)

    # Verify hash matches
    if result.provenance.command_hash.split(':')[1] == expected_hash:
        executed_hashes.add(expected_hash)
    else:
        print("⚠️ Hash mismatch! Possible tampering.")

    return result
```

### Pattern 4: Parallel Command Execution

Execute multiple independent commands concurrently.

```typescript
import { ExecutorClient } from 'octollm-sdk';

const client = new ExecutorClient({ bearerToken: '...' });

async function parallelExecution(commands: ExecutionRequest[]): Promise<ExecutionResult[]> {
  const promises = commands.map(cmd => client.execute(cmd));
  const results = await Promise.all(promises);

  // Check for failures
  const failures = results.filter(r => !r.success);
  if (failures.length > 0) {
    console.log(`${failures.length} commands failed`);
    failures.forEach(f => console.log(`  - Exit code ${f.exitCode}: ${f.stderr}`));
  }

  return results;
}

// Example: Scan multiple ports in parallel
const scanCommands = [22, 80, 443, 3306].map(port => ({
  actionType: 'shell',
  command: 'nmap',
  args: ['-p', String(port), '192.168.1.1'],
  timeoutSeconds: 30,
  capabilityToken: 'tok_network_scan_xyz'
}));

const results = await parallelExecution(scanCommands);
```

---

## Performance Characteristics

| Scenario | P50 | P95 | P99 | Max | Notes |
|----------|-----|-----|-----|-----|-------|
| Simple Shell (ls, echo) | 50ms | 120ms | 200ms | 500ms | Docker overhead |
| File Operations (cat, grep) | 100ms | 300ms | 500ms | 1s | I/O dependent |
| HTTP Requests (curl) | 800ms | 2s | 4s | 10s | Network latency |
| Python Scripts | 300ms | 1s | 2s | 5s | Interpreter startup |
| Network Scans (nmap) | 3s | 8s | 15s | 60s | Target dependent |

### Resource Limits (Per Execution)

| Resource | Limit | Notes |
|----------|-------|-------|
| CPU | 1 core | Shared across sandboxes |
| Memory | 512 MB | Hard limit, OOM kills |
| Disk | 100 MB | Ephemeral storage |
| Timeout | 300s max | Configurable per request |
| Network | 10 Mbps | Rate limited |

---

## Troubleshooting

### Issue 1: Command Not in Allowlist (403 Forbidden)

**Symptoms**: Executor returns 403 with "Command 'X' not in allowlist"

**Possible Causes**:
- Attempting to run dangerous command (rm, dd, etc.)
- Typo in command name
- Command not installed in sandbox

**Solutions**:
```bash
# Check allowed commands
curl http://executor:8003/capabilities | jq '.allowed_commands'

# Add command to allowlist (config change in Executor)
# ALLOWED_COMMANDS="echo,ls,cat,grep,curl,python3,YOUR_COMMAND"

# Restart Executor after config change
kubectl rollout restart deployment executor
```

### Issue 2: Execution Timeout (408)

**Symptoms**: Commands timing out after configured timeout

**Possible Causes**:
- Command taking longer than expected
- Network latency for HTTP requests
- Infinite loop in script

**Solutions**:
```python
# Increase timeout for long-running commands
result = await executor.execute({
    "action_type": "shell",
    "command": "nmap",
    "args": ["-p", "1-65535", "192.168.1.1"],
    "timeout_seconds": 300,  # 5 minutes
    "capability_token": "tok_abc123"
})

# Or split into smaller chunks
ports = ["1-1000", "1001-2000", "2001-3000", ...]
for port_range in ports:
    result = await executor.execute({
        "command": "nmap",
        "args": ["-p", port_range, "192.168.1.1"],
        "timeout_seconds": 60
    })
```

### Issue 3: Capability Token Errors

**Symptoms**: "Invalid or expired capability token" errors

**Possible Causes**:
- Token expired (default TTL: 60 seconds)
- Token missing required capabilities
- Clock skew between services

**Solutions**:
```python
# Ensure tokens are fresh
capability_token = generate_capability_token(
    capabilities=["ShellExecute", "NetworkAccess"],
    duration_seconds=120  # Longer TTL if needed
)

# Verify token before use
decoded = jwt.decode(capability_token, verify=False)
print(f"Token expires at: {decoded['exp']}")
print(f"Token capabilities: {decoded['capabilities']}")
```

### Issue 4: High Latency (>1s for simple commands)

**Symptoms**: Simple commands (ls, echo) taking >1 second

**Possible Causes**:
- Docker container startup overhead
- High system load
- Disk I/O saturation

**Solutions**:
```bash
# Check Docker performance
docker stats

# Increase Executor replicas
kubectl scale deployment executor --replicas=10

# Pre-warm containers (keep pool of ready sandboxes)
# Implementation in Executor service

# Monitor latency
curl http://executor:8003/metrics | grep executor_execution_duration
```

### Issue 5: Sandbox Escapes / Security Concerns

**Symptoms**: Suspicious activity, unauthorized file access

**Possible Causes**:
- Vulnerability in sandbox implementation
- Misconfigured capabilities
- Allowlist too permissive

**Solutions**:
```bash
# Audit provenance logs
kubectl logs -l app=executor | grep provenance | jq .

# Review allowed commands
# Remove any unnecessary commands from allowlist

# Enable gVisor for stronger isolation
# SANDBOX_RUNTIME=gvisor  # In Executor config

# Monitor capability violations
curl http://executor:8003/metrics | grep capability_violations
```

---

## Related Documentation

- [API Overview](../API-OVERVIEW.md)
- [Orchestrator API](./orchestrator.md)
- [Planner Arm API](./planner.md)
- [OpenAPI Specification](../openapi/executor.yaml)

---

## Support

For issues with the Executor Arm:
1. Check [Troubleshooting](#troubleshooting) section above
2. Review logs: `kubectl logs -l app=executor`
3. Check metrics: `curl http://executor:8003/metrics`
4. File issue: https://github.com/octollm/octollm/issues
