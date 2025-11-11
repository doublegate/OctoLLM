/**
 * Client for Planner Arm service (port 8002)
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
      baseUrl: config.baseUrl || 'http://localhost:8002',
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
}
