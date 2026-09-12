/**
 * Client for Reflex Layer service (port 8080)
 *
 * The reflex layer provides fast preprocessing with caching and PII detection.
 */

import { BaseClient, ClientConfig } from '../client';
import { PreprocessRequest, PreprocessResponse, CacheStats } from '../models';

export interface ReflexConfig extends Partial<ClientConfig> {
  baseUrl?: string;
}

/**
 * Client for interacting with the Reflex Layer service
 */
export class ReflexClient extends BaseClient {
  constructor(config: ReflexConfig = {}) {
    super({
      baseUrl: config.baseUrl || 'http://localhost:8080',
      ...config
    });
  }

  /**
   * Preprocess input with caching and security checks
   *
   * @param request - Preprocessing request
   * @param requestId - Optional request ID for tracing
   * @returns PreprocessResponse with cached/processed result
   */
  async preprocess(
    request: PreprocessRequest,
    requestId?: string
  ): Promise<PreprocessResponse> {
    // `/process`, not `/preprocess`. The reflex layer has only ever served
    // `/process`; this SDK asked for a path that has never existed, and no test
    // noticed because every one of them mocked the transport.
    return this.post<PreprocessResponse>('/process', request, {
      requestId
    });
  }

  /**
   * Get cache statistics
   *
   * @param requestId - Optional request ID for tracing
   * @returns Cache statistics
   */
  async getCacheStats(requestId?: string): Promise<CacheStats> {
    return this.get<CacheStats>('/cache/stats', {
      requestId
    });
  }

  /**
   * Empty the reflex cache.
   *
   * Not served yet: the reflex layer's response cache arrives in Stage 7, along with
   * the two exits from the reflex arc that give it something worth caching. See
   * `scripts/ci/check_sdk_parity.py`, which lists every such call with its stage and
   * fails once the route exists and the entry is not removed.
   *
   * @param requestId - Optional request ID for tracing
   */
  async clearCache(requestId?: string): Promise<Record<string, unknown>> {
    return this.post<Record<string, unknown>>('/cache/clear', undefined, {
      requestId
    });
  }
}
