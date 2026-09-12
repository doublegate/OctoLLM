/**
 * Client for Coder Arm service (port 8003)
 *
 * The coder arm generates, debugs, and refactors code.
 */

import { BaseClient, ClientConfig } from '../client';
import { CodeRequest, CodeResponse } from '../models';

export interface CoderConfig extends Partial<ClientConfig> {
  baseUrl?: string;
}

/**
 * Client for interacting with the Coder Arm service
 */
export class CoderClient extends BaseClient {
  constructor(config: CoderConfig = {}) {
    super({
      baseUrl: config.baseUrl || 'http://localhost:8003',
      ...config
    });
  }

  /**
   * Generate, debug, or refactor code
   *
   * @param request - Code operation request
   * @param requestId - Optional request ID for tracing
   * @returns Code response with generated/modified code
   *
   * @example
   * ```typescript
   * const result = await client.code({
   *   operation: 'generate',
   *   prompt: 'Write a Python function to validate email addresses',
   *   language: 'python'
   * });
   * console.log(result.code);
   * console.log(result.explanation);
   * ```
   */
  async code(request: CodeRequest, requestId?: string): Promise<CodeResponse> {
    return this.post<CodeResponse>('/code', request, {
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
