/**
 * Client for Reflex Layer service (port 8001)
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
      baseUrl: config.baseUrl || 'http://localhost:8001',
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
    return this.post<PreprocessResponse>('/preprocess', request, {
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
}
