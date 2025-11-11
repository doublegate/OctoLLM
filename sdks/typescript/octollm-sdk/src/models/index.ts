/**
 * TypeScript interfaces for OctoLLM SDK
 *
 * All models match the OpenAPI 3.0 specifications and Python SDK models.
 */

// ============================================================================
// Core Task Models (Orchestrator)
// ============================================================================

/**
 * Resource budget constraints for task execution
 */
export interface ResourceBudget {
  /** Maximum LLM tokens to use (100-100000) */
  max_tokens?: number;
  /** Maximum execution time in seconds (5-300) */
  max_time_seconds?: number;
  /** Maximum cost in USD (0.01-10.0) */
  max_cost_dollars?: number;
}

/**
 * Request to submit a new task to the orchestrator
 */
export interface TaskRequest {
  /** Natural language description of the task objective (10-2000 chars) */
  goal: string;
  /** Hard constraints that must be satisfied */
  constraints?: string[];
  /** Success conditions for validation */
  acceptance_criteria?: string[];
  /** Additional context and metadata */
  context?: Record<string, any>;
  /** Resource budget constraints */
  budget?: ResourceBudget;
}

/**
 * Task status enumeration
 */
export type TaskStatus =
  | 'queued'
  | 'processing'
  | 'completed'
  | 'failed'
  | 'cancelled';

/**
 * Response after submitting a task
 */
export interface TaskResponse {
  /** Unique task identifier (format: task_[a-zA-Z0-9]{16}) */
  task_id: string;
  /** Current task status */
  status: TaskStatus;
  /** Task creation timestamp */
  created_at: string;
  /** Estimated completion time */
  estimated_completion?: string;
}

/**
 * Current processing step
 */
export type ProcessingStep =
  | 'preprocessing'
  | 'planning'
  | 'execution'
  | 'validation'
  | 'synthesis';

/**
 * Task progress information
 */
export interface TaskProgress {
  /** Current processing step */
  current_step: ProcessingStep;
  /** Number of completed steps */
  completed_steps: number;
  /** Total number of steps */
  total_steps: number;
  /** Progress percentage (0-100) */
  percentage: number;
}

/**
 * Task execution result
 */
export interface TaskResult {
  /** Primary output */
  output: string;
  /** Confidence score (0.0-1.0) */
  confidence: number;
  /** Whether output passed validation */
  validation_passed: boolean;
}

/**
 * Task error information
 */
export interface TaskError {
  /** Error type */
  type: string;
  /** Human-readable error message */
  message: string;
  /** Additional error details */
  details?: string;
}

/**
 * Complete task status with results
 */
export interface TaskStatusResponse {
  /** Unique task identifier */
  task_id: string;
  /** Current task status */
  status: TaskStatus;
  /** Task creation timestamp */
  created_at: string;
  /** Last update timestamp */
  updated_at?: string;
  /** Task progress information */
  progress?: TaskProgress;
  /** Task result (if completed) */
  result?: TaskResult;
  /** Error information (if failed) */
  error?: TaskError;
}

// ============================================================================
// Arm Models
// ============================================================================

/**
 * JSON schema definition
 */
export interface JSONSchema {
  type: string;
  properties?: Record<string, any>;
  required?: string[];
  [key: string]: any;
}

/**
 * Arm capability information
 */
export interface ArmCapability {
  /** Unique arm identifier */
  arm_id: string;
  /** Human-readable arm name */
  name: string;
  /** Description of arm capabilities */
  description: string;
  /** Input JSON schema */
  input_schema: JSONSchema;
  /** Output JSON schema */
  output_schema: JSONSchema;
  /** Capability tags for routing */
  capabilities: string[];
  /** Cost tier (1=cheap, 5=expensive) */
  cost_tier: number;
  /** Kubernetes service endpoint */
  endpoint: string;
}

/**
 * List arms response
 */
export interface ListArmsResponse {
  /** List of registered arms */
  arms: ArmCapability[];
}

/**
 * Register arm request
 */
export interface RegisterArmRequest {
  /** Unique arm identifier */
  arm_id: string;
  /** Arm capability information */
  capability: Omit<ArmCapability, 'arm_id'>;
}

/**
 * Register arm response
 */
export interface RegisterArmResponse {
  /** Registration status */
  status: 'registered' | 'updated';
  /** Registered arm capability */
  arm: ArmCapability;
}

// ============================================================================
// Reflex Layer Models
// ============================================================================

/**
 * Reflex layer preprocessing request
 */
export interface PreprocessRequest {
  /** Input text to preprocess */
  input: string;
  /** Optional request context */
  context?: Record<string, any>;
}

/**
 * Reflex layer preprocessing response
 */
export interface PreprocessResponse {
  /** Whether cached response was found */
  cached: boolean;
  /** Preprocessed output (if not cached) */
  output?: string;
  /** Cached response (if cached) */
  response?: any;
  /** PII detection results */
  pii_detected: boolean;
  /** Injection attack detection results */
  injection_detected: boolean;
}

/**
 * Cache statistics
 */
export interface CacheStats {
  /** Total cache entries */
  total_entries: number;
  /** Cache hit rate (0.0-1.0) */
  hit_rate: number;
  /** Average response time (ms) */
  avg_response_time_ms: number;
}

// ============================================================================
// Planner Arm Models
// ============================================================================

/**
 * Planner decomposition request
 */
export interface PlanRequest {
  /** Task goal to decompose */
  goal: string;
  /** Task constraints */
  constraints?: string[];
  /** Resource budget */
  budget?: ResourceBudget;
}

/**
 * Subtask in execution plan
 */
export interface Subtask {
  /** Subtask identifier */
  subtask_id: string;
  /** Subtask description */
  description: string;
  /** Target arm for execution */
  assigned_arm: string;
  /** Dependencies on other subtasks */
  dependencies: string[];
  /** Estimated cost tier */
  cost_tier: number;
}

/**
 * Planner decomposition response
 */
export interface PlanResponse {
  /** List of subtasks */
  subtasks: Subtask[];
  /** Estimated total cost */
  estimated_cost_usd: number;
  /** Estimated execution time (seconds) */
  estimated_time_seconds: number;
}

// ============================================================================
// Executor Arm Models
// ============================================================================

/**
 * Executor command execution request
 */
export interface ExecuteRequest {
  /** Command to execute */
  command: string;
  /** Command arguments */
  args?: string[];
  /** Working directory */
  cwd?: string;
  /** Environment variables */
  env?: Record<string, string>;
  /** Execution timeout (seconds) */
  timeout?: number;
}

/**
 * Executor command execution response
 */
export interface ExecuteResponse {
  /** Sandbox identifier */
  sandbox_id: string;
  /** Execution status */
  status: 'running' | 'completed' | 'failed' | 'timeout';
  /** Standard output */
  stdout?: string;
  /** Standard error */
  stderr?: string;
  /** Exit code */
  exit_code?: number;
  /** Execution time (seconds) */
  execution_time_seconds?: number;
}

/**
 * Sandbox status response
 */
export interface SandboxStatusResponse {
  /** Sandbox identifier */
  sandbox_id: string;
  /** Sandbox status */
  status: 'running' | 'completed' | 'terminated';
  /** Creation timestamp */
  created_at: string;
  /** Resource usage */
  resources?: {
    cpu_percent: number;
    memory_mb: number;
  };
}

// ============================================================================
// Retriever Arm Models
// ============================================================================

/**
 * Retriever search request
 */
export interface SearchRequest {
  /** Search query */
  query: string;
  /** Number of results to return */
  top_k?: number;
  /** Minimum relevance score (0.0-1.0) */
  min_score?: number;
  /** Filter by metadata */
  filters?: Record<string, any>;
}

/**
 * Search result item
 */
export interface SearchResult {
  /** Document ID */
  doc_id: string;
  /** Document content */
  content: string;
  /** Relevance score (0.0-1.0) */
  score: number;
  /** Document metadata */
  metadata?: Record<string, any>;
}

/**
 * Retriever search response
 */
export interface SearchResponse {
  /** List of search results */
  results: SearchResult[];
  /** Total number of matches */
  total_matches: number;
  /** Search execution time (ms) */
  search_time_ms: number;
}

// ============================================================================
// Coder Arm Models
// ============================================================================

/**
 * Code operation type
 */
export type CodeOperation = 'generate' | 'debug' | 'refactor' | 'explain';

/**
 * Coder request
 */
export interface CodeRequest {
  /** Operation type */
  operation: CodeOperation;
  /** Natural language prompt */
  prompt: string;
  /** Existing code (for debug/refactor) */
  code?: string;
  /** Programming language */
  language?: string;
  /** Additional context */
  context?: Record<string, any>;
}

/**
 * Coder response
 */
export interface CodeResponse {
  /** Generated/modified code */
  code: string;
  /** Explanation of changes */
  explanation: string;
  /** Language detected/used */
  language: string;
  /** Confidence score (0.0-1.0) */
  confidence: number;
}

// ============================================================================
// Judge Arm Models
// ============================================================================

/**
 * Judge validation request
 */
export interface ValidateRequest {
  /** Output to validate */
  output: string;
  /** Acceptance criteria */
  criteria: string[];
  /** Expected format/schema */
  expected_format?: JSONSchema;
}

/**
 * Validation criterion result
 */
export interface CriterionResult {
  /** Criterion description */
  criterion: string;
  /** Whether criterion passed */
  passed: boolean;
  /** Explanation */
  explanation: string;
}

/**
 * Judge validation response
 */
export interface ValidateResponse {
  /** Overall validation result */
  passed: boolean;
  /** Overall confidence score (0.0-1.0) */
  confidence: number;
  /** Individual criterion results */
  criteria_results: CriterionResult[];
  /** Issues found */
  issues?: string[];
}

// ============================================================================
// Safety Guardian Arm Models
// ============================================================================

/**
 * PII entity type
 */
export type PIIType =
  | 'email'
  | 'phone'
  | 'ssn'
  | 'credit_card'
  | 'ip_address'
  | 'name'
  | 'address';

/**
 * Detected PII entity
 */
export interface PIIEntity {
  /** Entity type */
  type: PIIType;
  /** Detected value */
  value: string;
  /** Position in text */
  start: number;
  end: number;
  /** Detection confidence (0.0-1.0) */
  confidence: number;
}

/**
 * Safety check request
 */
export interface SafetyCheckRequest {
  /** Content to check */
  content: string;
  /** Check for PII */
  check_pii?: boolean;
  /** Check for harmful content */
  check_harmful?: boolean;
}

/**
 * Safety check response
 */
export interface SafetyCheckResponse {
  /** Whether content is safe */
  safe: boolean;
  /** PII detected */
  pii_detected: boolean;
  /** PII entities found */
  pii_entities?: PIIEntity[];
  /** Harmful content detected */
  harmful_detected: boolean;
  /** Harm categories detected */
  harm_categories?: string[];
  /** Redacted content (PII removed) */
  redacted_content?: string;
}

// ============================================================================
// Health Check Models
// ============================================================================

/**
 * Health check response
 */
export interface HealthResponse {
  /** Service status */
  status: 'healthy' | 'degraded' | 'unhealthy';
  /** Service version */
  version: string;
  /** Uptime in seconds */
  uptime_seconds?: number;
}
