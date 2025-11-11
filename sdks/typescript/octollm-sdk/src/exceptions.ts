/**
 * Custom exception classes for OctoLLM SDK
 */

export interface ErrorResponse {
  error: {
    code: string;
    message: string;
    details?: Record<string, any>;
  };
  request_id?: string;
}

/**
 * Base exception for all OctoLLM errors
 */
export class OctoLLMError extends Error {
  public readonly statusCode?: number;
  public readonly errorCode?: string;
  public readonly details?: Record<string, any>;
  public readonly requestId?: string;

  constructor(message: string, errorData?: ErrorResponse, statusCode?: number) {
    super(message);
    this.name = this.constructor.name;
    this.statusCode = statusCode;

    if (errorData) {
      this.errorCode = errorData.error.code;
      this.details = errorData.error.details;
      this.requestId = errorData.request_id;
    }

    Error.captureStackTrace(this, this.constructor);
  }
}

/**
 * Authentication failed (401)
 */
export class AuthenticationError extends OctoLLMError {
  constructor(errorData: ErrorResponse) {
    super(errorData.error.message || 'Authentication failed', errorData, 401);
  }
}

/**
 * Authorization failed (403)
 */
export class AuthorizationError extends OctoLLMError {
  constructor(errorData: ErrorResponse) {
    super(errorData.error.message || 'Authorization failed', errorData, 403);
  }
}

/**
 * Validation failed (400, 422)
 */
export class ValidationError extends OctoLLMError {
  constructor(errorData: ErrorResponse) {
    super(errorData.error.message || 'Validation failed', errorData, 400);
  }
}

/**
 * Resource not found (404)
 */
export class NotFoundError extends OctoLLMError {
  constructor(errorData: ErrorResponse) {
    super(errorData.error.message || 'Resource not found', errorData, 404);
  }
}

/**
 * Rate limit exceeded (429)
 */
export class RateLimitError extends OctoLLMError {
  public readonly retryAfter?: number;

  constructor(errorData: ErrorResponse, retryAfter?: number) {
    super(errorData.error.message || 'Rate limit exceeded', errorData, 429);
    this.retryAfter = retryAfter;
  }
}

/**
 * Service unavailable (503)
 */
export class ServiceUnavailableError extends OctoLLMError {
  constructor(errorData: ErrorResponse) {
    super(errorData.error.message || 'Service unavailable', errorData, 503);
  }
}

/**
 * Request timeout
 */
export class TimeoutError extends OctoLLMError {
  constructor(message: string) {
    super(message, undefined, 408);
  }
}

/**
 * Generic API error
 */
export class APIError extends OctoLLMError {
  constructor(errorData: ErrorResponse, statusCode?: number) {
    super(errorData.error.message || 'API error occurred', errorData, statusCode);
  }
}
