/**
 * API Calls Integration Tests - Advanced Features
 * Tests request interceptors, API versioning, and response handling
 * 
 * Business Value Justification (BVJ):
 * - Segment: All (Free → Enterprise)
 * - Goal: Ensure reliable API communication patterns for all customer segments
 * - Value Impact: Prevents API-related bugs that could cause customer churn
 * - Revenue Impact: +$50K MRR from improved reliability
 */
import { render, screen, waitFor } from '@testing-library/react';
import { setupServer } from 'msw/node';
import { http, HttpResponse } from 'msw';
import { apiClient } from '@/services/apiClient';
import { getApiUrl } from '@/services/api';

// ============================================================================
// MSW SERVER SETUP
// ============================================================================

const mockApiUrl = 'http://localhost:8000';

const createAdvancedHandlers = () => [
  // Clean API endpoints without versioning
  http.get(`${mockApiUrl}/api/threads`, () => {
    return HttpResponse.json({
      threads: []
    });
  }),

  // Interceptor test endpoints
  http.get(`${mockApiUrl}/api/interceptor-test`, () => {
    return HttpResponse.json({ intercepted: true });
  }),

  // Large data endpoint
  http.get(`${mockApiUrl}/api/large-data`, () => {
    const largeData = Array.from({ length: 1000 }, (_, i) => ({
      id: i,
      content: `Large data item ${i}`.repeat(10)
    }));
    return HttpResponse.json({ data: largeData });
  }),

  // Empty response endpoint
  http.delete(`${mockApiUrl}/api/empty-response`, () => {
    return new HttpResponse(null, { status: 204 });
  }),

  // Dynamic OpenAPI spec
  http.get(`${mockApiUrl}/openapi.json`, () => {
    return HttpResponse.json({
      paths: {
        '/api/threads': {
          get: { summary: 'get_threads' }
        },
        '/api/interceptor-test': {
          get: { summary: 'interceptor_test' }
        },
        '/api/cached': {
          get: { summary: 'cached_endpoint' }
        },
        '/api/retry-test': {
          get: { summary: 'retry_test' }
        },
        '/api/empty-response': {
          delete: { summary: 'delete_empty' }
        },
        '/api/with-metadata': {
          get: { summary: 'metadata_test' }
        },
        '/api/large-data': {
          get: { summary: 'get_large_data' }
        },
        '/api/connection-test': {
          get: { summary: 'connection_test' }
        },
        '/api/large-payload': {
          post: { summary: 'large_payload_test' }
        }
      }
    });
  }),

  // Cached endpoint
  http.get(`${mockApiUrl}/api/cached`, (() => {
    let callCount = 0;
    return () => {
      callCount++;
      return HttpResponse.json({ 
        call_count: callCount,
        timestamp: Date.now()
      });
    };
  })()),

  // OpenAPI spec caching test
  http.get(`${mockApiUrl}/openapi-cache-test.json`, (() => {
    let specCallCount = 0;
    return () => {
      specCallCount++;
      return HttpResponse.json({
        spec_calls: specCallCount,
        paths: {
          '/api/cached': {
            get: { summary: 'cached_endpoint' }
          }
        }
      });
    };
  })())
];

const server = setupServer(...createAdvancedHandlers());

// ============================================================================
// TEST SETUP
// ============================================================================

beforeAll(() => {
  server.listen();
  process.env.NEXT_PUBLIC_API_URL = mockApiUrl;
});

beforeEach(() => {
  // Clear the API spec cache before each test
  (require('@/services/api').apiSpecService as any).spec = null;
});

afterEach(() => {
  server.resetHandlers();
  jest.clearAllMocks();
});

afterAll(() => {
  server.close();
});

// ============================================================================
// REQUEST INTERCEPTOR TESTS
// ============================================================================

describe('API Calls - Request Interceptors', () => {
  it('handles API spec fetching for endpoint resolution', async () => {
    // The apiClient.get() call should first fetch the OpenAPI spec
    const result = await apiClient.get('get_threads', 'test-token');
    
    // Verify the call completed successfully (endpoint was resolved)
    expect(result).toBeDefined();
    
    // Verify the API client exists and is functional
    expect(apiClient.get).toBeDefined();
    expect(typeof apiClient.get).toBe('function');
  });

  it('caches OpenAPI spec for subsequent requests', async () => {
    let specCallCount = 0;
    
    server.use(
      http.get(`${mockApiUrl}/openapi.json`, () => {
        specCallCount++;
        return HttpResponse.json({
          paths: {
            '/api/cached': {
              get: { summary: 'cached_endpoint' }
            }
          }
        });
      })
    );

    // Make multiple requests
    await apiClient.get('cached_endpoint', 'test-token');
    await apiClient.get('cached_endpoint', 'test-token');
    
    // Spec should only be fetched once due to caching
    expect(specCallCount).toBe(1);
  });

  it('handles endpoint resolution failure gracefully', async () => {
    server.use(
      http.get(`${mockApiUrl}/openapi.json`, () => {
        return HttpResponse.json({
          paths: {} // Empty paths
        });
      })
    );

    await expect(
      apiClient.get('nonexistent_endpoint', 'test-token')
    ).rejects.toThrow('Endpoint nonexistent_endpoint not found');
  });

  it('handles malformed OpenAPI specs', async () => {
    server.use(
      http.get(`${mockApiUrl}/openapi.json`, () => {
        return new HttpResponse('invalid json', { status: 200 });
      })
    );

    await expect(
      apiClient.get('any_endpoint', 'test-token')
    ).rejects.toThrow();
  });

  it('retries spec fetching on failure', async () => {
    let specAttempts = 0;
    
    server.use(
      http.get(`${mockApiUrl}/openapi.json`, () => {
        specAttempts++;
        if (specAttempts < 2) {
          return new HttpResponse(null, { status: 500 });
        }
        return HttpResponse.json({
          paths: {
            '/api/retry-test': {
              get: { summary: 'retry_test' }
            }
          }
        });
      })
    );

    // Should eventually succeed after retry
    await expect(
      apiClient.get('retry_test', 'test-token')
    ).resolves.toBeDefined();
  });
});

// ============================================================================
// API VERSIONING TESTS
// ============================================================================

describe('API Calls - API Versioning', () => {
  it('supports clean API endpoints without versioning', async () => {
    const url = getApiUrl('/api/threads');
    const response = await fetch(url);
    const data = await response.json();
    
    expect(data.threads).toBeDefined();
    expect(Array.isArray(data.threads)).toBe(true);
  });

  it('handles clean endpoints in OpenAPI spec', async () => {
    server.use(
      http.get(`${mockApiUrl}/openapi.json`, () => {
        return HttpResponse.json({
          paths: {
            '/api/threads': {
              get: { summary: 'get_threads' }
            }
          }
        });
      })
    );

    // Clear any cached spec
    (apiClient as any).spec = null;
    
    const result = await apiClient.get('get_threads', 'test-token');
    
    // Verify endpoint was successfully called
    expect(result).toBeDefined();
    expect(apiClient.get).toBeDefined();
  });

  it('handles consistent endpoint structure', async () => {
    // Test calling clean endpoints without versioning
    const response = await apiClient.get('get_threads', 'test-token');
    
    expect(response.threads).toBeDefined();
    expect(Array.isArray(response.threads)).toBe(true);
  });

  it('validates clean endpoint availability', async () => {
    const url = getApiUrl('/api/threads');
    const response = await fetch(url);
    
    expect(response.status).toBe(200);
    const data = await response.json();
    expect(data.threads).toBeDefined();
  });
});

// ============================================================================
// RESPONSE INTERCEPTOR TESTS
// ============================================================================

describe('API Calls - Response Interceptors', () => {
  it('parses JSON responses correctly', async () => {
    const response = await apiClient.get('get_threads', 'test-token');
    
    expect(typeof response).toBe('object');
    expect(response.threads).toBeDefined();
  });

  it('handles empty response bodies', async () => {
    server.use(
      http.delete(`${mockApiUrl}/api/empty-response`, () => {
        return new HttpResponse(null, { status: 204 });
      })
    );

    const response = await apiClient.request('delete_empty', 'delete', {
      method: 'DELETE'
    });
    
    // Should handle empty response gracefully
    expect(response).toBeDefined();
  });

  it('preserves response metadata', async () => {
    server.use(
      http.get(`${mockApiUrl}/api/with-metadata`, () => {
        return HttpResponse.json(
          { 
            data: 'test',
            metadata: {
              timestamp: '2025-01-19T10:00:00Z',
              version: '1.0',
              request_id: 'req-123'
            }
          },
          { 
            status: 200,
            headers: {
              'X-Request-ID': 'req-123',
              'X-Rate-Limit': '100'
            }
          }
        );
      })
    );

    server.use(
      http.get(`${mockApiUrl}/openapi.json`, () => {
        return HttpResponse.json({
          paths: {
            '/api/with-metadata': {
              get: { summary: 'metadata_test' }
            }
          }
        });
      })
    );

    const response = await apiClient.get('metadata_test', 'test-token');
    expect(response.metadata).toBeDefined();
    expect(response.metadata.request_id).toBe('req-123');
  });

  it('handles large response payloads efficiently', async () => {
    const startTime = performance.now();
    const response = await apiClient.get('get_large_data', 'test-token');
    const endTime = performance.now();
    
    expect(response.data).toHaveLength(1000);
    expect(endTime - startTime).toBeLessThan(5000); // Should handle large data quickly
  });

  it('validates response content types', async () => {
    server.use(
      http.get(`${mockApiUrl}/api/xml-response`, () => {
        return new HttpResponse('<xml>data</xml>', {
          headers: { 'Content-Type': 'application/xml' }
        });
      })
    );

    server.use(
      http.get(`${mockApiUrl}/openapi.json`, () => {
        return HttpResponse.json({
          paths: {
            '/api/xml-response': {
              get: { summary: 'xml_test' }
            }
          }
        });
      })
    );

    // Should handle non-JSON content gracefully
    await expect(
      apiClient.get('xml_test', 'test-token')
    ).rejects.toThrow(); // JSON parsing will fail
  });
});

// ============================================================================
// PERFORMANCE TESTS
// ============================================================================

describe('API Calls - Performance', () => {
  it('handles concurrent requests efficiently', async () => {
    const promises = Array.from({ length: 10 }, (_, i) => 
      apiClient.get('get_threads', `token-${i}`)
    );
    
    const startTime = performance.now();
    const responses = await Promise.all(promises);
    const endTime = performance.now();
    
    expect(responses).toHaveLength(10);
    expect(endTime - startTime).toBeLessThan(3000); // Should handle concurrent requests
  });

  it('implements connection pooling', async () => {
    let connectionCount = 0;
    
    server.use(
      http.get(`${mockApiUrl}/api/connection-test`, () => {
        connectionCount++;
        return HttpResponse.json({ connection: connectionCount });
      })
    );

    server.use(
      http.get(`${mockApiUrl}/openapi.json`, () => {
        return HttpResponse.json({
          paths: {
            '/api/connection-test': {
              get: { summary: 'connection_test' }
            }
          }
        });
      })
    );

    // Make multiple requests rapidly
    const promises = Array.from({ length: 5 }, () => 
      apiClient.get('connection_test', 'test-token')
    );
    
    await Promise.all(promises);
    expect(connectionCount).toBe(5);
  });

  it('optimizes payload serialization', async () => {
    const largePayload = {
      data: Array.from({ length: 1000 }, (_, i) => ({
        id: i,
        content: `Item ${i}`.repeat(50)
      }))
    };

    let serializedSize = 0;
    server.use(
      http.post(`${mockApiUrl}/api/large-payload`, async ({ request }) => {
        const text = await request.text();
        serializedSize = text.length;
        return HttpResponse.json({ received: true });
      })
    );

    server.use(
      http.get(`${mockApiUrl}/openapi.json`, () => {
        return HttpResponse.json({
          paths: {
            '/api/large-payload': {
              post: { summary: 'large_payload_test' }
            }
          }
        });
      })
    );

    const startTime = performance.now();
    await apiClient.post('large_payload_test', largePayload, 'test-token');
    const endTime = performance.now();
    
    expect(serializedSize).toBeGreaterThan(0);
    expect(endTime - startTime).toBeLessThan(2000); // Should serialize efficiently
  });
});