/**
 * Client for Retriever Arm service (port 8002)
 *
 * The retriever arm performs semantic search over knowledge bases.
 */

import { BaseClient, ClientConfig } from '../client';
import { SearchRequest, SearchResponse } from '../models';

export interface RetrieverConfig extends Partial<ClientConfig> {
  baseUrl?: string;
}

/**
 * Client for interacting with the Retriever Arm service
 */
export class RetrieverClient extends BaseClient {
  constructor(config: RetrieverConfig = {}) {
    super({
      baseUrl: config.baseUrl || 'http://localhost:8002',
      ...config
    });
  }

  /**
   * Search knowledge base with semantic + full-text hybrid search
   *
   * @param request - Search request with query and filters
   * @param requestId - Optional request ID for tracing
   * @returns Search results with relevance scores
   *
   * @example
   * ```typescript
   * const results = await client.search({
   *   query: 'SQL injection vulnerabilities',
   *   top_k: 10,
   *   min_score: 0.7
   * });
   * results.results.forEach(result => {
   *   console.log(`${result.score}: ${result.content}`);
   * });
   * ```
   */
  async search(
    request: SearchRequest,
    requestId?: string
  ): Promise<SearchResponse> {
    return this.post<SearchResponse>('/search', request, {
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
