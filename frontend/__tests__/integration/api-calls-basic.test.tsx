import { render, screen, waitFor } from '@testing-library/react';
import { setupServer } from 'msw/node';
import { http, HttpResponse } from 'msw';
import { apiClient } from '@/services/apiClient';
import { getApiUrl } from '@/services/api';
import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';
ion for all customer segments
 * - Value Impact: Prevents API-related bugs that could cause 20% customer churn
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

const createBasicHandlers = () => [
  // GET endpoints
  http.get(`${mockApiUrl}/api/threads`, () => {
    return HttpResponse.json({
      threads: [
        { id: 'thread-1', title: 'Test Thread 1', created_at: '2025-01-19T10:00:00Z' },
        { id: 'thread-2', title: 'Test Thread 2', created_at: '2025-01-19T11:00:00Z' }
      ]
    });
  }),

  http.get(`${mockApiUrl}/api/threads/:threadId`, ({ params }) => {
    const { threadId } = params;
    return HttpResponse.json({
      id: threadId,
      title: `Thread ${threadId}`,
      messages: []
    });
  }),

  // POST endpoints  
  http.post(`${mockApiUrl}/api/threads`, async ({ request }) => {
    const body = await request.json();
    return HttpResponse.json({
      id: 'new-thread-id',
      title: (body as any).title,
      created_at: new Date().toISOString()
    }, { status: 201 });
  }),

  http.post(`${mockApiUrl}/api/messages`, async ({ request }) => {
    const body = await request.json();
    return HttpResponse.json({
      id: 'new-message-id',
      content: (body as any).content,
      thread_id: (body as any).thread_id,
      created_at: new Date().toISOString()
    }, { status: 201 });
  }),

  // PUT endpoints
  http.put(`${mockApiUrl}/api/threads/:threadId`, async ({ params, request }) => {
    const { threadId } = params;
    const body = await request.json();
    return HttpResponse.json({
      id: threadId,
      title: (body as any).title,
      updated_at: new Date().toISOString()
    });
  }),

  // DELETE endpoints
  http.delete(`${mockApiUrl}/api/threads/:threadId`, ({ params }) => {
    const { threadId } = params;
    return HttpResponse.json({
      success: true,
      deleted_id: threadId
    });
  }),

  // OpenAPI spec endpoint
  http.get(`${mockApiUrl}/openapi.json`, () => {
    return HttpResponse.json({
      paths: {
        '/api/threads': {
          get: { summary: 'get_threads' },
          post: { summary: 'create_thread' }
        },
        '/api/threads/{thread_id}': {
          get: { summary: 'get_thread' },
          put: { summary: 'update_thread' },
          delete: { summary: 'delete_thread' }
        },
        '/api/messages': {
          post: { summary: 'create_message' }
        }
      }
    });
  })
];

const server = setupServer(...createBasicHandlers());

// ============================================================================
// TEST SETUP
// ============================================================================

beforeAll(() => {
  server.listen();
  process.env.NEXT_PUBLIC_API_URL = mockApiUrl;
});

afterEach(() => {
  server.resetHandlers();
  jest.clearAllMocks();
    // Clean up timers to prevent hanging
    jest.clearAllTimers();
    jest.useFakeTimers();
    jest.runOnlyPendingTimers();
    jest.useRealTimers();
});

afterAll(() => {
  server.close();
});

// ============================================================================
// GET REQUEST TESTS
// ============================================================================

describe('API Calls - GET Requests', () => {
    jest.setTimeout(10000);
  it('fetches thread list successfully', async () => {
    const response = await apiClient.get('get_threads', 'test-token');
    
    expect(response.threads).toHaveLength(2);
    expect(response.threads[0]).toEqual({
      id: 'thread-1',
      title: 'Test Thread 1',
      created_at: '2025-01-19T10:00:00Z'
    });
  });

  it('fetches single thread with auth token', async () => {
    const response = await apiClient.get('get_thread', 'test-token');
    
    expect(response).toMatchObject({
      id: expect.any(String),
      title: expect.stringContaining('Thread'),
      messages: []
    });
  });

  it('handles GET request without auth token', async () => {
    const response = await apiClient.get('get_threads', null);
    
    expect(response.threads).toHaveLength(2);
  });

  it('constructs correct API URL for GET requests', () => {
    const url = getApiUrl('/api/test');
    expect(url).toBe(`${mockApiUrl}/api/test`);
  });
});

// ============================================================================
// POST REQUEST TESTS  
// ============================================================================

describe('API Calls - POST Requests', () => {
    jest.setTimeout(10000);
  it('creates new thread with POST request', async () => {
    const threadData = { title: 'New Test Thread' };
    const response = await apiClient.post('create_thread', threadData, 'test-token');
    
    expect(response).toMatchObject({
      id: 'new-thread-id',
      title: 'New Test Thread',
      created_at: expect.any(String)
    });
  });

  it('creates message with POST and validates payload', async () => {
    const messageData = {
      content: 'Test message content',
      thread_id: 'thread-1'
    };
    
    const response = await apiClient.post('create_message', messageData, 'test-token');
    
    expect(response).toMatchObject({
      id: 'new-message-id',
      content: 'Test message content',
      thread_id: 'thread-1',
      created_at: expect.any(String)
    });
  });

  it('includes correct headers in POST requests', async () => {
    let capturedHeaders: Record<string, string> = {};
    
    server.use(
      http.post(`${mockApiUrl}/api/threads`, ({ request }) => {
        capturedHeaders = Object.fromEntries(request.headers.entries());
        return HttpResponse.json({ id: 'test' });
      })
    );

    await apiClient.post('create_thread', { title: 'Test' }, 'test-token');
    
    expect(capturedHeaders['authorization']).toBe('Bearer test-token');
    expect(capturedHeaders['content-type']).toBe('application/json');
  });

  it('serializes request body correctly', async () => {
    let capturedBody: any = null;
    
    server.use(
      http.post(`${mockApiUrl}/api/threads`, async ({ request }) => {
        capturedBody = await request.json();
        return HttpResponse.json({ id: 'test' });
      })
    );

    const data = { title: 'Test Thread', metadata: { priority: 'high' } };
    await apiClient.post('create_thread', data, 'test-token');
    
    expect(capturedBody).toEqual(data);
  });
});

// ============================================================================
// PUT REQUEST TESTS
// ============================================================================

describe('API Calls - PUT Requests', () => {
    jest.setTimeout(10000);
  it('updates thread with PUT request', async () => {
    // Mock PUT endpoint specifically
    server.use(
      http.put(`${mockApiUrl}/api/threads/thread-1`, async ({ request }) => {
        const body = await request.json();
        return HttpResponse.json({
          id: 'thread-1',
          title: (body as any).title,
          updated_at: new Date().toISOString()
        });
      })
    );

    const updateData = { title: 'Updated Thread Title' };
    const response = await apiClient.request('update_thread', 'put', {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer test-token'
      },
      body: JSON.stringify(updateData)
    });
    
    expect(response.title).toBe('Updated Thread Title');
    expect(response.updated_at).toBeDefined();
  });

  it('handles PUT request with complex data', async () => {
    const complexData = {
      title: 'Complex Update',
      metadata: {
        tags: ['test', 'integration'],
        priority: 1,
        settings: { auto_save: true }
      }
    };

    let capturedBody: any = null;
    server.use(
      http.put(`${mockApiUrl}/api/threads/thread-1`, async ({ request }) => {
        capturedBody = await request.json();
        return HttpResponse.json({ success: true });
      })
    );

    await apiClient.request('update_thread', 'put', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(complexData)
    });
    
    expect(capturedBody).toEqual(complexData);
  });
});

// ============================================================================
// DELETE REQUEST TESTS
// ============================================================================

describe('API Calls - DELETE Requests', () => {
    jest.setTimeout(10000);
  it('deletes thread with DELETE request', async () => {
    const response = await apiClient.request('delete_thread', 'delete', {
      method: 'DELETE',
      headers: { 'Authorization': 'Bearer test-token' }
    });
    
    expect(response.success).toBe(true);
    expect(response.deleted_id).toBeDefined();
  });

  it('includes auth header in DELETE requests', async () => {
    let capturedHeaders: Record<string, string> = {};
    
    server.use(
      http.delete(`${mockApiUrl}/api/threads/thread-1`, ({ request }) => {
        capturedHeaders = Object.fromEntries(request.headers.entries());
        return HttpResponse.json({ success: true });
      })
    );

    await apiClient.request('delete_thread', 'delete', {
      method: 'DELETE',
      headers: { 'Authorization': 'Bearer delete-token' }
    });
    
    expect(capturedHeaders['authorization']).toBe('Bearer delete-token');
  });
});