/**
 * Authentication helpers for OctoLLM SDK
 */

export interface AuthHeaders {
  'X-API-Key'?: string;
  'Authorization'?: string;
  [key: string]: string | undefined;
}

/**
 * Get authentication headers based on provided credentials
 *
 * @param apiKey - API key for external authentication
 * @param bearerToken - Bearer token for inter-service authentication
 * @returns Headers object with appropriate authentication
 */
export function getAuthHeaders(
  apiKey?: string,
  bearerToken?: string
): AuthHeaders {
  const headers: AuthHeaders = {};

  if (apiKey) {
    headers['X-API-Key'] = apiKey;
  }

  if (bearerToken) {
    headers['Authorization'] = `Bearer ${bearerToken}`;
  }

  return headers;
}

/**
 * Get authentication from environment variables
 *
 * @returns Object with apiKey and bearerToken from environment
 */
export function getAuthFromEnv(): { apiKey?: string; bearerToken?: string } {
  return {
    apiKey: process.env.OCTOLLM_API_KEY,
    bearerToken: process.env.OCTOLLM_BEARER_TOKEN
  };
}
