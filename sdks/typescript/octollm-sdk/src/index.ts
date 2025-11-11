/**
 * OctoLLM SDK for TypeScript
 *
 * Official SDK for interacting with the OctoLLM distributed AI architecture.
 *
 * @example Basic usage
 * ```typescript
 * import { OrchestratorClient } from 'octollm-sdk';
 *
 * const client = new OrchestratorClient({
 *   apiKey: process.env.OCTOLLM_API_KEY
 * });
 *
 * const response = await client.submitTask({
 *   goal: 'Analyze code security',
 *   budget: { max_tokens: 10000 }
 * });
 * ```
 */

// Service clients
export { OrchestratorClient } from './services/orchestrator';
export { ReflexClient } from './services/reflex';
export { PlannerClient } from './services/planner';
export { ExecutorClient } from './services/executor';
export { RetrieverClient } from './services/retriever';
export { CoderClient } from './services/coder';
export { JudgeClient } from './services/judge';
export { SafetyClient } from './services/safety';

// Base client and config
export { BaseClient, ClientConfig } from './client';

// Models and types
export * from './models';

// Exceptions
export * from './exceptions';

// Auth helpers
export { getAuthHeaders, getAuthFromEnv } from './auth';
