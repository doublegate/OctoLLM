/**
 * Tests for exception classes
 */

import {
  OctoLLMError,
  AuthenticationError,
  ValidationError,
  NotFoundError,
  RateLimitError,
  ErrorResponse
} from '../src/exceptions';

describe('Exception classes', () => {
  const mockErrorResponse: ErrorResponse = {
    error: {
      code: 'test_error',
      message: 'Test error message',
      details: { field: 'value' }
    },
    request_id: 'req_123'
  };

  describe('OctoLLMError', () => {
    it('should create error with message', () => {
      const error = new OctoLLMError('Test error');
      expect(error.message).toBe('Test error');
      expect(error.name).toBe('OctoLLMError');
    });

    it('should capture error data', () => {
      const error = new OctoLLMError('Test', mockErrorResponse, 400);
      expect(error.errorCode).toBe('test_error');
      expect(error.requestId).toBe('req_123');
      expect(error.statusCode).toBe(400);
      expect(error.details).toEqual({ field: 'value' });
    });
  });

  describe('AuthenticationError', () => {
    it('should create with 401 status code', () => {
      const error = new AuthenticationError(mockErrorResponse);
      expect(error.statusCode).toBe(401);
      expect(error.message).toBe('Test error message');
    });

    it('should use default message when not provided', () => {
      const response: ErrorResponse = {
        error: { code: 'auth_failed', message: '' }
      };
      const error = new AuthenticationError(response);
      expect(error.message).toBe('Authentication failed');
    });
  });

  describe('ValidationError', () => {
    it('should create with 400 status code', () => {
      const error = new ValidationError(mockErrorResponse);
      expect(error.statusCode).toBe(400);
    });
  });

  describe('NotFoundError', () => {
    it('should create with 404 status code', () => {
      const error = new NotFoundError(mockErrorResponse);
      expect(error.statusCode).toBe(404);
    });
  });

  describe('RateLimitError', () => {
    it('should create with 429 status code', () => {
      const error = new RateLimitError(mockErrorResponse);
      expect(error.statusCode).toBe(429);
    });

    it('should capture retry after value', () => {
      const error = new RateLimitError(mockErrorResponse, 60);
      expect(error.retryAfter).toBe(60);
    });
  });
});
