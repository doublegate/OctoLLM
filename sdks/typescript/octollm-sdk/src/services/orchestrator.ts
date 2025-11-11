/**
 * Client for Orchestrator service (port 8000)
 *
 * The orchestrator is the central brain that coordinates task execution
 * across specialized arms.
 */

import { BaseClient, ClientConfig } from '../client';
import {
  TaskRequest,
  TaskResponse,
  TaskStatusResponse,
  ListArmsResponse,
  RegisterArmRequest,
  RegisterArmResponse
} from '../models';

export interface OrchestratorConfig extends Partial<ClientConfig> {
  baseUrl?: string;
}

/**
 * Client for interacting with the Orchestrator service
 */
export class OrchestratorClient extends BaseClient {
  constructor(config: OrchestratorConfig = {}) {
    super({
      baseUrl: config.baseUrl || 'http://localhost:8000',
      ...config
    });
  }

  /**
   * Submit a new task to the orchestrator
   *
   * @param task - Task request with goal, budget, and constraints
   * @param requestId - Optional request ID for tracing
   * @returns TaskResponse with task_id and status
   *
   * @example
   * ```typescript
   * const client = new OrchestratorClient({ apiKey: 'your-key' });
   * const response = await client.submitTask({
   *   goal: 'Analyze code security',
   *   budget: { max_tokens: 10000 }
   * });
   * console.log(response.task_id);
   * ```
   */
  async submitTask(
    task: TaskRequest,
    requestId?: string
  ): Promise<TaskResponse> {
    return this.post<TaskResponse>('/tasks', task, {
      requestId
    });
  }

  /**
   * Get task status and results by ID
   *
   * @param taskId - Task identifier
   * @param requestId - Optional request ID for tracing
   * @returns TaskStatusResponse with current status and results
   *
   * @example
   * ```typescript
   * const status = await client.getTask('task_abc123');
   * console.log(status.status, status.progress);
   * ```
   */
  async getTask(
    taskId: string,
    requestId?: string
  ): Promise<TaskStatusResponse> {
    return this.get<TaskStatusResponse>(`/tasks/${taskId}`, {
      requestId
    });
  }

  /**
   * Cancel a running task
   *
   * @param taskId - Task identifier
   * @param requestId - Optional request ID for tracing
   * @returns Updated TaskStatusResponse with cancelled status
   *
   * @example
   * ```typescript
   * const result = await client.cancelTask('task_abc123');
   * console.log(result.status); // 'cancelled'
   * ```
   */
  async cancelTask(
    taskId: string,
    requestId?: string
  ): Promise<TaskStatusResponse> {
    return this.delete<TaskStatusResponse>(`/tasks/${taskId}`, {
      requestId
    });
  }

  /**
   * List all registered arms and their capabilities
   *
   * @param requestId - Optional request ID for tracing
   * @returns List of ArmCapability objects
   *
   * @example
   * ```typescript
   * const { arms } = await client.listArms();
   * arms.forEach(arm => {
   *   console.log(`${arm.name}: ${arm.description}`);
   * });
   * ```
   */
  async listArms(requestId?: string): Promise<ListArmsResponse> {
    return this.get<ListArmsResponse>('/arms', {
      requestId
    });
  }

  /**
   * Register a new arm with the orchestrator
   *
   * @param request - Arm registration request
   * @param requestId - Optional request ID for tracing
   * @returns RegisterArmResponse with registration status
   *
   * @example
   * ```typescript
   * const response = await client.registerArm({
   *   arm_id: 'custom_arm_1',
   *   capability: {
   *     name: 'Custom Arm',
   *     description: 'Custom processing',
   *     // ... other fields
   *   }
   * });
   * ```
   */
  async registerArm(
    request: RegisterArmRequest,
    requestId?: string
  ): Promise<RegisterArmResponse> {
    return this.post<RegisterArmResponse>('/arms/register', request, {
      requestId
    });
  }
}
