/**
 * Client for Judge Arm service (port 8004)
 *
 * The judge arm validates outputs against acceptance criteria.
 */

import { BaseClient, ClientConfig } from '../client';
import { ValidateRequest, ValidateResponse } from '../models';

export interface JudgeConfig extends Partial<ClientConfig> {
  baseUrl?: string;
}

/**
 * Client for interacting with the Judge Arm service
 */
export class JudgeClient extends BaseClient {
  constructor(config: JudgeConfig = {}) {
    super({
      baseUrl: config.baseUrl || 'http://localhost:8004',
      ...config
    });
  }

  /**
   * Validate output against acceptance criteria
   *
   * @param request - Validation request with output and criteria
   * @param requestId - Optional request ID for tracing
   * @returns Validation result with per-criterion feedback
   *
   * @example
   * ```typescript
   * const result = await client.validate({
   *   output: 'Generated security report...',
   *   criteria: [
   *     'Must identify all high-severity vulnerabilities',
   *     'Must include remediation steps'
   *   ]
   * });
   * console.log(result.passed);
   * result.criteria_results.forEach(cr => {
   *   console.log(`${cr.criterion}: ${cr.passed ? 'PASS' : 'FAIL'}`);
   * });
   * ```
   */
  async validate(
    request: ValidateRequest,
    requestId?: string
  ): Promise<ValidateResponse> {
    return this.post<ValidateResponse>('/validate', request, {
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
