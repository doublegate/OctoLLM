/**
 * Client for Executor Arm service (port 8006)
 *
 * The executor arm runs commands in sandboxed environments.
 */

import { BaseClient, ClientConfig } from '../client';
import { ExecuteRequest, ExecuteResponse, SandboxStatusResponse } from '../models';

export interface ExecutorConfig extends Partial<ClientConfig> {
  baseUrl?: string;
}

/**
 * Client for interacting with the Executor Arm service
 */
export class ExecutorClient extends BaseClient {
  constructor(config: ExecutorConfig = {}) {
    super({
      baseUrl: config.baseUrl || 'http://localhost:18006',
      ...config
    });
  }

  /**
   * Execute a command in a sandboxed environment
   *
   * @param request - Execution request with command and args
   * @param requestId - Optional request ID for tracing
   * @returns Execution response with stdout/stderr and status
   *
   * @example
   * ```typescript
   * const result = await client.execute({
   *   command: 'nmap',
   *   args: ['-sV', '192.168.1.1'],
   *   timeout: 60
   * });
   * console.log(result.stdout);
   * ```
   */
  async execute(
    request: ExecuteRequest,
    requestId?: string
  ): Promise<ExecuteResponse> {
    return this.post<ExecuteResponse>('/execute', request, {
      requestId
    });
  }

  /**
   * Get sandbox status by ID
   *
   * @param sandboxId - Sandbox identifier
   * @param requestId - Optional request ID for tracing
   * @returns Sandbox status and resource usage
   */
  async getSandboxStatus(
    sandboxId: string,
    requestId?: string
  ): Promise<SandboxStatusResponse> {
    return this.get<SandboxStatusResponse>(`/sandbox/${sandboxId}/status`, {
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
