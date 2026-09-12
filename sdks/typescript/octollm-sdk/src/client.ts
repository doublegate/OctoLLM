/**
 * Base HTTP client with automatic retry and error handling
 */

import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios';
import axiosRetry from 'axios-retry';
import { getAuthHeaders } from './auth';
import {
  OctoLLMError,
  AuthenticationError,
  AuthorizationError,
  ValidationError,
  NotFoundError,
  RateLimitError,
  ServiceUnavailableError,
  TimeoutError,
  APIError,
  ErrorResponse
} from './exceptions';
import { HealthResponse } from './models';

export interface ClientConfig {
  baseUrl: string;
  apiKey?: string;
  bearerToken?: string;
  timeout?: number;
  maxRetries?: number;
  verifySsl?: boolean;
}

/**
 * Coerce an arbitrary error body into an ErrorResponse.
 *
 * A gateway or proxy will happily return HTML, plain text, or a bare JSON array in
 * place of the documented error object. Casting that straight to ErrorResponse type-checks
 * but leaves `errorData.error.code` undefined at runtime, so the shape is verified here
 * instead. Anything unrecognised is preserved under `details.body` rather than discarded,
 * which is what you actually want when debugging a 502 from an intermediary.
 */
function toErrorResponse(data: unknown, fallbackMessage: string): ErrorResponse {
  const hasErrorObject =
    typeof data === 'object' &&
    data !== null &&
    'error' in data &&
    typeof (data as { error: unknown }).error === 'object' &&
    (data as { error: unknown }).error !== null;

  if (hasErrorObject) {
    return data as ErrorResponse;
  }

  return {
    error: {
      code: 'unknown',
      message: fallbackMessage,
      ...(data === undefined || data === null ? {} : { details: { body: data } })
    }
  };
}

/**
 * Base client for all OctoLLM service clients
 */
export class BaseClient {
  protected baseUrl: string;
  protected apiKey?: string;
  protected bearerToken?: string;
  protected timeout: number;
  protected maxRetries: number;
  protected verifySsl: boolean;
  protected axiosInstance: AxiosInstance;
  private requestCount: number = 0;

  constructor(config: ClientConfig) {
    this.baseUrl = config.baseUrl.replace(/\/$/, '');
    this.apiKey = config.apiKey;
    this.bearerToken = config.bearerToken;
    this.timeout = config.timeout || 30000;
    this.maxRetries = config.maxRetries || 3;
    this.verifySsl = config.verifySsl !== false;

    // Create axios instance
    this.axiosInstance = axios.create({
      baseURL: this.baseUrl,
      timeout: this.timeout,
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeaders(this.apiKey, this.bearerToken)
      }
    });

    // Configure retry logic
    axiosRetry(this.axiosInstance, {
      retries: this.maxRetries,
      retryDelay: (retryCount) => {
        return Math.pow(2, retryCount) * 1000; // Exponential backoff
      },
      retryCondition: (error) => {
        // Retry on network errors and 5xx errors
        return (
          axiosRetry.isNetworkOrIdempotentRequestError(error) ||
          (error.response?.status ?? 0) >= 500
        );
      }
    });

    // Add request interceptor for tracking
    this.axiosInstance.interceptors.request.use((config) => {
      this.requestCount++;
      return config;
    });

    // Add response interceptor for error handling
    this.axiosInstance.interceptors.response.use(
      (response) => response,
      (error) => {
        throw this.handleError(error);
      }
    );
  }

  /**
   * Get request count
   */
  getRequestCount(): number {
    return this.requestCount;
  }

  /**
   * Make HTTP request
   */
  protected async request<T = unknown>(
    method: string,
    path: string,
    options: {
      data?: unknown;
      params?: Record<string, unknown>;
      headers?: Record<string, string>;
      requestId?: string;
      timeout?: number;
    } = {}
  ): Promise<T> {
    const { data, params, headers, requestId, timeout } = options;

    const config: AxiosRequestConfig = {
      method,
      url: path,
      data,
      params,
      headers: {
        ...headers,
        ...(requestId ? { 'X-Request-ID': requestId } : {})
      },
      timeout: timeout || this.timeout
    };

    try {
      const response: AxiosResponse<T> = await this.axiosInstance.request(config);
      return response.data;
    } catch (error: unknown) {
      throw this.handleError(error);
    }
  }

  /**
   * Handle HTTP errors and convert to appropriate exception
   */
  private handleError(error: unknown): OctoLLMError {
    if (!axios.isAxiosError(error)) {
      return new APIError({
        error: {
          code: 'unknown_error',
          message: error instanceof Error ? error.message : String(error)
        }
      });
    }

    if (error.response) {
      const statusCode = error.response.status;
      const errorData = toErrorResponse(error.response.data, error.message);

      switch (statusCode) {
        case 401:
          return new AuthenticationError(errorData);
        case 403:
          return new AuthorizationError(errorData);
        case 404:
          return new NotFoundError(errorData);
        case 400:
        case 422:
          return new ValidationError(errorData);
        case 429: {
          const retryAfter = error.response.headers['retry-after'];
          return new RateLimitError(
            errorData,
            retryAfter ? parseInt(retryAfter, 10) : undefined
          );
        }
        case 503:
          return new ServiceUnavailableError(errorData);
        default:
          return new APIError(errorData, statusCode);
      }
    } else if (error.code === 'ECONNABORTED') {
      return new TimeoutError(`Request timed out after ${this.timeout}ms`);
    } else if (error.request) {
      return new APIError({
        error: { code: 'network_error', message: 'Network error occurred' }
      });
    } else {
      return new APIError({
        error: { code: 'unknown', message: error.message }
      });
    }
  }

  /**
   * Convenience methods for HTTP verbs
   */

  protected async get<T = unknown>(
    path: string,
    options?: Omit<Parameters<typeof this.request>[2], 'data'>
  ): Promise<T> {
    return this.request<T>('GET', path, options);
  }

  protected async post<T = unknown>(
    path: string,
    data?: unknown,
    options?: Parameters<typeof this.request>[2]
  ): Promise<T> {
    return this.request<T>('POST', path, { ...options, data });
  }

  protected async put<T = unknown>(
    path: string,
    data?: unknown,
    options?: Parameters<typeof this.request>[2]
  ): Promise<T> {
    return this.request<T>('PUT', path, { ...options, data });
  }

  protected async patch<T = unknown>(
    path: string,
    data?: unknown,
    options?: Parameters<typeof this.request>[2]
  ): Promise<T> {
    return this.request<T>('PATCH', path, { ...options, data });
  }

  protected async delete<T = unknown>(
    path: string,
    options?: Parameters<typeof this.request>[2]
  ): Promise<T> {
    return this.request<T>('DELETE', path, options);
  }

  /**
   * Check the service's health.
   *
   * On the base client because all eight services serve `GET /health` -- it is the
   * one route the whole stack has in common. The Python SDK has had this on every
   * client since Phase 0; this SDK had it on none, which `check_sdk_parity.py` found
   * the moment it compared the two.
   *
   * @param requestId - Optional request ID for tracing
   */
  async health(requestId?: string): Promise<HealthResponse> {
    return this.get<HealthResponse>('/health', { requestId });
  }
}
