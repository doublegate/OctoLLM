/**
 * Client for Safety Guardian Arm service (port 8005)
 *
 * The safety guardian detects PII and filters harmful content.
 */

import { BaseClient, ClientConfig } from '../client';
import { SafetyCheckRequest, SafetyCheckResponse } from '../models';

export interface SafetyConfig extends Partial<ClientConfig> {
  baseUrl?: string;
}

/**
 * Client for interacting with the Safety Guardian Arm service
 */
export class SafetyClient extends BaseClient {
  constructor(config: SafetyConfig = {}) {
    super({
      baseUrl: config.baseUrl || 'http://localhost:8005',
      ...config
    });
  }

  /**
   * Check content for PII and harmful content
   *
   * @param request - Safety check request
   * @param requestId - Optional request ID for tracing
   * @returns Safety check results with PII entities and redacted content
   *
   * @example
   * ```typescript
   * const result = await client.check({
   *   content: 'Contact me at john@example.com or 555-1234',
   *   check_pii: true,
   *   check_harmful: true
   * });
   * if (result.pii_detected) {
   *   console.log('PII found:', result.pii_entities);
   *   console.log('Redacted:', result.redacted_content);
   * }
   * ```
   */
  async check(
    request: SafetyCheckRequest,
    requestId?: string
  ): Promise<SafetyCheckResponse> {
    return this.post<SafetyCheckResponse>('/check', request, {
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
