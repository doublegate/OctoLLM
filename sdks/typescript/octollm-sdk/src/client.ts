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

export interface ClientConfig {
  baseUrl: string;
  apiKey?: string;
  bearerToken?: string;
  timeout?: number;
  maxRetries?: number;
  verifySsl?: boolean;
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
  protected async request<T = any>(
    method: string,
    path: string,
    options: {
      data?: any;
      params?: Record<string, any>;
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
    } catch (error: any) {
      throw this.handleError(error);
    }
  }

  /**
   * Handle HTTP errors and convert to appropriate exception
   */
  private handleError(error: any): OctoLLMError {
    if (error.response) {
      const statusCode = error.response.status;
      const errorData: ErrorResponse = error.response.data || {
        error: { code: 'unknown', message: error.message }
      };

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
        case 429:
          const retryAfter = error.response.headers['retry-after'];
          return new RateLimitError(
            errorData,
            retryAfter ? parseInt(retryAfter) : undefined
          );
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

  protected async get<T = any>(
    path: string,
    options?: Omit<Parameters<typeof this.request>[2], 'data'>
  ): Promise<T> {
    return this.request<T>('GET', path, options);
  }

  protected async post<T = any>(
    path: string,
    data?: any,
    options?: Parameters<typeof this.request>[2]
  ): Promise<T> {
    return this.request<T>('POST', path, { ...options, data });
  }

  protected async put<T = any>(
    path: string,
    data?: any,
    options?: Parameters<typeof this.request>[2]
  ): Promise<T> {
    return this.request<T>('PUT', path, { ...options, data });
  }

  protected async patch<T = any>(
    path: string,
    data?: any,
    options?: Parameters<typeof this.request>[2]
  ): Promise<T> {
    return this.request<T>('PATCH', path, { ...options, data });
  }

  protected async delete<T = any>(
    path: string,
    options?: Parameters<typeof this.request>[2]
  ): Promise<T> {
    return this.request<T>('DELETE', path, options);
  }
}
