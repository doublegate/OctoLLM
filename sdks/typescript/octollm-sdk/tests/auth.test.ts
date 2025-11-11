/**
 * Tests for authentication helpers
 */

import { getAuthHeaders, getAuthFromEnv } from '../src/auth';

describe('Auth helpers', () => {
  describe('getAuthHeaders', () => {
    it('should return empty object when no credentials provided', () => {
      const headers = getAuthHeaders();
      expect(headers).toEqual({});
    });

    it('should return API key header when provided', () => {
      const headers = getAuthHeaders('test-key');
      expect(headers).toEqual({
        'X-API-Key': 'test-key'
      });
    });

    it('should return bearer token header when provided', () => {
      const headers = getAuthHeaders(undefined, 'test-token');
      expect(headers).toEqual({
        'Authorization': 'Bearer test-token'
      });
    });

    it('should return both headers when both provided', () => {
      const headers = getAuthHeaders('test-key', 'test-token');
      expect(headers).toEqual({
        'X-API-Key': 'test-key',
        'Authorization': 'Bearer test-token'
      });
    });
  });

  describe('getAuthFromEnv', () => {
    const originalEnv = process.env;

    beforeEach(() => {
      jest.resetModules();
      process.env = { ...originalEnv };
    });

    afterAll(() => {
      process.env = originalEnv;
    });

    it('should return empty object when env vars not set', () => {
      delete process.env.OCTOLLM_API_KEY;
      delete process.env.OCTOLLM_BEARER_TOKEN;

      const auth = getAuthFromEnv();
      expect(auth).toEqual({
        apiKey: undefined,
        bearerToken: undefined
      });
    });

    it('should return API key from env', () => {
      process.env.OCTOLLM_API_KEY = 'env-key';
      const auth = getAuthFromEnv();
      expect(auth.apiKey).toBe('env-key');
    });

    it('should return bearer token from env', () => {
      process.env.OCTOLLM_BEARER_TOKEN = 'env-token';
      const auth = getAuthFromEnv();
      expect(auth.bearerToken).toBe('env-token');
    });
  });
});
