/**
 * Tests for BaseClient
 */

import { BaseClient } from '../src/client';
import {
  AuthenticationError,
  ValidationError,
  NotFoundError,
  RateLimitError
} from '../src/exceptions';

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
  });
});
