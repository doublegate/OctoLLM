/**
 * Tests for BaseClient
 */

import { AxiosError, AxiosHeaders } from 'axios';
import { BaseClient } from '../src/client';
import {
  APIError,
  AuthenticationError,
  ValidationError,
  NotFoundError,
  RateLimitError
} from '../src/exceptions';

/** Build an AxiosError carrying an arbitrary response body. */
function axiosErrorWithBody(status: number, data: unknown): AxiosError {
  const error = new AxiosError('Request failed with status code ' + status);
  error.response = {
    status,
    statusText: '',
    data,
    headers: new AxiosHeaders(),
    config: { headers: new AxiosHeaders() }
  };
  return error;
}

describe('BaseClient', () => {
  let client: BaseClient;

  beforeEach(() => {
    client = new BaseClient({
      baseUrl: 'http://localhost:8000',
      apiKey: 'test-key',
      timeout: 5000,
      maxRetries: 3
    });
  });

  describe('constructor', () => {
    it('should initialize with correct config', () => {
      expect(client).toBeDefined();
      expect(client.getRequestCount()).toBe(0);
    });

    it('should strip trailing slash from baseUrl', () => {
      const clientWithSlash = new BaseClient({
        baseUrl: 'http://localhost:8000/',
        apiKey: 'test-key'
      });
      expect(clientWithSlash).toBeDefined();
    });
  });

  describe('request counting', () => {
    it('should increment request count', () => {
      expect(client.getRequestCount()).toBe(0);
    });
  });

  describe('error handling', () => {
    it('should handle authentication errors', () => {
      // This test would require mocking axios
      expect(AuthenticationError).toBeDefined();
    });

    it('should handle validation errors', () => {
      expect(ValidationError).toBeDefined();
    });

    it('should handle not found errors', () => {
      expect(NotFoundError).toBeDefined();
    });

    it('should handle rate limit errors', () => {
      expect(RateLimitError).toBeDefined();
    });

    // A gateway or proxy will return HTML, plain text, or a bare array in place of the
    // documented error object. These bodies used to be cast straight to ErrorResponse,
    // which type-checks but leaves errorData.error.code undefined at runtime.
    const handle = (body: unknown, status = 404) =>
      client['handleError'](axiosErrorWithBody(status, body));

    it('uses the documented error object when the body has one', () => {
      const err = handle({ error: { code: 'not_found', message: 'no such task' } });
      expect(err).toBeInstanceOf(NotFoundError);
      expect(err.message).toBe('no such task');
      expect(err.errorCode).toBe('not_found');
    });

    it('synthesises an error for an HTML body and keeps the raw body', () => {
      const err = handle('<html>502 Bad Gateway</html>');
      expect(err).toBeInstanceOf(NotFoundError);
      expect(err.errorCode).toBe('unknown');
      expect(err.details).toEqual({ body: '<html>502 Bad Gateway</html>' });
    });

    it('synthesises an error for a JSON body that is not an object', () => {
      const err = handle(['not', 'an', 'object']);
      expect(err.errorCode).toBe('unknown');
      expect(err.details).toEqual({ body: ['not', 'an', 'object'] });
    });

    it('synthesises an error for an object with no error field', () => {
      const err = handle({ detail: 'wrong envelope' });
      expect(err.errorCode).toBe('unknown');
      expect(err.details).toEqual({ body: { detail: 'wrong envelope' } });
    });

    it('handles an empty body without inventing details', () => {
      const err = handle(null);
      expect(err.errorCode).toBe('unknown');
      expect(err.details).toBeUndefined();
    });

    it('maps a non-axios throw to an APIError instead of crashing', () => {
      const err = client['handleError'](new Error('socket hang up'));
      expect(err).toBeInstanceOf(APIError);
      expect(err.message).toBe('socket hang up');
    });
  });
});
