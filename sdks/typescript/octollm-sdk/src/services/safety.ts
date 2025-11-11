/**
 * Client for Safety Guardian Arm service (port 8007)
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
      baseUrl: config.baseUrl || 'http://localhost:8007',
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
}
