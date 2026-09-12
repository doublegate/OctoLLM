/**
 * Client for the Memory / Curator Arm (port 8007)
 *
 * Memory owns storage for the whole system: episodic vectors in Qdrant, semantic
 * provenance in PostgreSQL. It is the Retriever's corpus, which is why it lands first.
 *
 * Both calls require a capability token signed by the orchestrator, with `aud` of
 * `memory` and a matching `X-Task-Id` header.
 */

import { BaseClient, ClientConfig } from "../client";

/** How far an artifact may travel. Ordered; the diode never flows downward. */
export type Sensitivity = "public" | "internal" | "confidential" | "restricted";

/** One recalled artifact, with enough provenance to judge whether to trust it. */
export interface MemoryHit {
  artifact_id: string;
  artifact_type: string;
  content: string;
  score: number;
  created_by: string;
  task_id: string;
  sensitivity: Sensitivity;
  created_at: string;
}

export interface RecallResponse {
  arm_id: string;
  request_id: string;
  confidence: number;
  hits: MemoryHit[];
  scope: "episodic" | "semantic";
  /**
   * Matches suppressed because they exceed the caller's clearance. Reported as a
   * count so the diode is visible: silently returning fewer results makes a
   * clearance boundary look like an empty index.
   */
  withheld: number;
}

export interface RememberResponse {
  arm_id: string;
  request_id: string;
  confidence: number;
  artifact_id: string;
  episodic_written: boolean;
  semantic_written: boolean;
  /** Already stored. Expected: ring delivery is at-least-once. */
  duplicate: boolean;
}

export interface MemoryConfig extends Partial<ClientConfig> {
  baseUrl?: string;
}

export interface RecallOptions {
  /** Sent as `X-Task-Id`; must match the token's `task_id`. */
  taskId: string;
  topK?: number;
  /** Whose memory to search. Defaults to the token's subject. */
  armId?: string;
}

export interface RememberOptions {
  taskId: string;
  /** Embed and index it. False records provenance only. */
  indexEpisodic?: boolean;
}

/**
 * Client for interacting with the Memory / Curator Arm
 */
export class MemoryClient extends BaseClient {
  constructor(config: MemoryConfig = {}) {
    super({
      baseUrl: config.baseUrl || "http://localhost:8007",
      ...config,
    });
  }

  /**
   * Search episodic memory.
   *
   * There is deliberately no clearance argument. Sensitivity is read from the
   * capability token, never from the request — a caller that states its own clearance
   * is an escalation with extra steps. The response's `withheld` count tells you how
   * many matches your clearance excluded.
   *
   * @example
   * ```typescript
   * const result = await client.recall('how did we parse that header', {
   *   taskId: 'task-1',
   *   topK: 5
   * });
   * console.log(`${result.hits.length} hits, ${result.withheld} withheld`);
   * ```
   */
  async recall(query: string, options: RecallOptions): Promise<RecallResponse> {
    const body: Record<string, unknown> = {
      query,
      top_k: options.topK ?? 10,
      task_id: options.taskId,
    };
    if (options.armId !== undefined) {
      body.arm_id = options.armId;
    }
    return this.post<RecallResponse>("/recall", body, {
      headers: { "X-Task-Id": options.taskId },
    });
  }

  /**
   * Commit one artifact to memory.
   *
   * Idempotent: a second write of the same `artifact_id` returns 200 with
   * `duplicate: true`, not a conflict. Ring delivery is at-least-once, so a
   * redelivery is expected rather than exceptional.
   */
  async remember(
    artifact: Record<string, unknown>,
    options: RememberOptions,
  ): Promise<RememberResponse> {
    return this.post<RememberResponse>(
      "/remember",
      {
        artifact,
        index_episodic: options.indexEpisodic ?? true,
        task_id: options.taskId,
      },
      { headers: { "X-Task-Id": options.taskId } },
    );
  }

  // `health()` is inherited from BaseClient: GET /health is the one route all nine
  // services have in common, and overriding it here would narrow its return type for
  // no benefit.

  /** This arm's declaration, including its ring topology. Needs no token. */
  async getCapabilities(): Promise<Record<string, unknown>> {
    return this.get<Record<string, unknown>>("/capabilities");
  }
}
