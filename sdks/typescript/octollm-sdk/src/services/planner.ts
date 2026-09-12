/**
 * Client for Planner Arm service (port 8001)
 *
 * The planner arm decomposes complex tasks into executable subtasks.
 */

import { BaseClient, ClientConfig } from '../client';
import { PlanRequest, PlanResponse } from '../models';

export interface PlannerConfig extends Partial<ClientConfig> {
  baseUrl?: string;
}

/**
 * Client for interacting with the Planner Arm service
 */
export class PlannerClient extends BaseClient {
  constructor(config: PlannerConfig = {}) {
    super({
      baseUrl: config.baseUrl || 'http://localhost:8001',
      ...config
    });
  }

  /**
   * Decompose a task into subtasks
   *
   * @param request - Planning request with goal and constraints
   * @param requestId - Optional request ID for tracing
   * @returns Plan with subtasks and cost estimates
   *
   * @example
   * ```typescript
   * const plan = await client.plan({
   *   goal: 'Scan network for vulnerabilities',
   *   budget: { max_tokens: 5000 }
   * });
   * plan.subtasks.forEach(subtask => {
   *   console.log(`${subtask.description} -> ${subtask.assigned_arm}`);
   * });
   * ```
   */
  async plan(request: PlanRequest, requestId?: string): Promise<PlanResponse> {
    return this.post<PlanResponse>('/plan', request, {
      requestId
    });
  }

  /**
   * Fetch this arm's own declaration: its id, routing tags, cost tier, the schemas
   * it accepts and returns, and the Neural Ring edges it declares.
   *
   * The orchestrator's registry reads the same endpoint, which is how the ring
   * topology reaches it over a protocol that already exists.
   *
   * @param requestId - Optional request ID for tracing
   */
  async capabilities(requestId?: string): Promise<Record<string, unknown>> {
    return this.get<Record<string, unknown>>('/capabilities', {
      requestId
    });
  }
}
